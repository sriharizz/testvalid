import re
from typing import List, Dict, Any, Optional
from schemas import ProtocolStep, ProtocolSession, CoverageGateReport, PlannedStep

def check_protocol_to_plan(session: ProtocolSession) -> CoverageGateReport:
    """
    Upgraded Coverage Gate 1:
    1. Step Sequence Parity: Every step_id in session.steps exists in session.planned_steps in exact same order.
    2. 100% Field-Level Parity: Every extracted_field in session.steps exists in planned_steps with a non-empty target_value.
    """
    step_ids_proto = [s.step_id for s in session.steps]
    step_ids_plan = [p.step_id for p in session.planned_steps]

    missing_steps = [sid for sid in step_ids_proto if sid not in step_ids_plan]
    order_mismatches = []
    if not missing_steps and step_ids_proto != step_ids_plan:
        order_mismatches.append(f"Step sequence order mismatch: Expected {step_ids_proto} but got {step_ids_plan}")

    missing_fields = []
    plan_dict = {p.step_id: p for p in session.planned_steps}

    total_fields_expected = 0
    total_fields_mapped = 0

    for step in session.steps:
        total_fields_expected += len(step.extracted_fields)
        plan_step = plan_dict.get(step.step_id)
        if not plan_step:
            for ef in step.extracted_fields:
                missing_fields.append(f"{step.step_id}:{ef.label}")
            continue

        planned_field_ids = {fa.field_id: fa for fa in plan_step.field_actions}
        for ef in step.extracted_fields:
            if ef.field_id not in planned_field_ids:
                missing_fields.append(f"{step.step_id}:{ef.label}")
            else:
                fa = planned_field_ids[ef.field_id]
                if not fa.target_value or fa.target_value.strip() == "":
                    missing_fields.append(f"{step.step_id}:{ef.label} (Empty Value)")
                else:
                    total_fields_mapped += 1

    passed = (len(missing_steps) == 0 and len(order_mismatches) == 0 and len(missing_fields) == 0)

    report = CoverageGateReport(
        gate_name="GATE_1_PROTOCOL_TO_PLAN",
        passed=passed,
        total_steps_expected=len(step_ids_proto),
        total_steps_mapped=len(step_ids_plan),
        total_fields_expected=total_fields_expected,
        total_fields_mapped=total_fields_mapped,
        missing_steps=missing_steps,
        missing_fields=missing_fields,
        order_mismatch_errors=order_mismatches,
        assertion_errors=[],
        screenshot_errors=[],
        skip_violations=[],
        details=[f"Verified {total_fields_mapped}/{total_fields_expected} fields across {len(step_ids_plan)}/{len(step_ids_proto)} steps."]
    )
    return report

def check_plan_to_spec(session: ProtocolSession) -> CoverageGateReport:
    """
    Upgraded Coverage Gate 2:
    Audits session.generated_spec_code to verify:
    1. All planned step_id blocks exist in exact sequential order.
    2. Every planned fa.field_id is present as a traceable tag [FIELD:TS1-...] in the generated code.
    3. Zero .skip(), .fixme(), or commented-out assertions exist.
    4. Every step requiring screenshot captures form state and modal evidence before dismissal.
    """
    spec_code = session.generated_spec_code or ""
    
    plan_step_ids = [p.step_id for p in session.planned_steps]
    total_fields_expected = sum(len(p.field_actions) for p in session.planned_steps)
    
    missing_steps = []
    missing_fields = []
    order_mismatch_errors = []
    assertion_errors = []
    screenshot_errors = []
    skip_violations = []

    # 1. Audit Forbidden Skip Patterns
    forbidden_patterns = [
        (r'test\.skip\s*\(', "Forbidden test.skip() detected"),
        (r'\.skip\s*\(', "Forbidden .skip() detected"),
        (r'test\.fixme\s*\(', "Forbidden test.fixme() detected"),
        (r'\.fixme\s*\(', "Forbidden .fixme() detected"),
        (r'test\.todo\s*\(', "Forbidden test.todo() detected"),
        (r'//\s*await\s+expect\(', "Commented-out expect() assertion detected")
    ]
    for pattern, msg in forbidden_patterns:
        if re.search(pattern, spec_code):
            skip_violations.append(msg)

    # 2. Extract step blocks from spec_code
    step_pattern = re.compile(
        r"await\s+test\.step\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*async\s*\(\s*\)\s*=>\s*\{([\s\S]*?)\n\s*\}\s*\);",
        re.MULTILINE
    )

    extracted_steps = []
    for match in step_pattern.finditer(spec_code):
        raw_header = match.group(1).strip()
        id_match = re.match(r'(TS\d+-S\d+)', raw_header)
        step_id = id_match.group(1) if id_match else raw_header
        body = match.group(2)
        extracted_steps.append((step_id, body))

    extracted_step_ids = [s[0] for s in extracted_steps]

    # Verify all planned step IDs exist
    for pid in plan_step_ids:
        if pid not in extracted_step_ids:
            missing_steps.append(pid)

    # Verify sequential order
    if not missing_steps and extracted_step_ids != plan_step_ids:
        order_mismatch_errors.append(f"Spec test.step order mismatch: Expected {plan_step_ids} but got {extracted_step_ids}")

    step_body_map = {s[0]: s[1] for s in extracted_steps}
    total_fields_mapped = 0

    # 3. Field-Level Parity & Screenshot Audits
    for p_step in session.planned_steps:
        sid = p_step.step_id
        body = step_body_map.get(sid, "")

        # Audit 100% of field tags
        for fa in p_step.field_actions:
            field_tag = f"[FIELD:{fa.field_id}]"
            if field_tag in body or f"'{fa.field_id}'" in body:
                total_fields_mapped += 1
            else:
                missing_fields.append(f"{sid}:{fa.field_id}:{fa.label}")

        # Audit Screenshots
        if p_step.requires_form_screenshot or p_step.requires_modal_screenshot:
            has_form_cap = f"{sid}_form" in body or f"captureFormState" in body or f"captureEvidence(page, '{sid}')" in body
            has_modal_cap = f"{sid}_modal" in body or f"captureModalEvidence" in body or f"captureEvidence" in body
            if not has_form_cap and not has_modal_cap:
                screenshot_errors.append(f"Step {sid}: Screenshot checkpoint required but capture call is missing")

        # Audit Assertions count
        actual_expects = len(re.findall(r'await\s+expect\s*\(', body))
        req_expects = len(p_step.expected_assertions)
        if actual_expects < req_expects:
            assertion_errors.append(f"Step {sid}: Expected {req_expects} assertions, found {actual_expects}")

    passed = (
        len(missing_steps) == 0 and
        len(missing_fields) == 0 and
        len(order_mismatch_errors) == 0 and
        len(skip_violations) == 0 and
        len(screenshot_errors) == 0 and
        len(assertion_errors) == 0
    )

    return CoverageGateReport(
        gate_name="GATE_2_PLAN_TO_SPEC",
        passed=passed,
        total_steps_expected=len(plan_step_ids),
        total_steps_mapped=len(extracted_step_ids),
        total_fields_expected=total_fields_expected,
        total_fields_mapped=total_fields_mapped,
        missing_steps=missing_steps,
        missing_fields=missing_fields,
        order_mismatch_errors=order_mismatch_errors,
        assertion_errors=assertion_errors,
        screenshot_errors=screenshot_errors,
        skip_violations=skip_violations,
        details=[f"Verified {total_fields_mapped}/{total_fields_expected} fields and {len(extracted_step_ids)}/{len(plan_step_ids)} steps in Playwright .spec.ts code."]
    )

class CoverageChecker:
    @staticmethod
    def verify_protocol_to_plan(protocol_steps: List[ProtocolStep], plan_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        protocol_ids = [step.step_id for step in protocol_steps]
        plan_ids = [p["step_id"] for p in plan_steps]

        missing_ids = [sid for sid in protocol_ids if sid not in plan_ids]
        extra_ids = [sid for sid in plan_ids if sid not in protocol_ids]
        order_verified = (protocol_ids == plan_ids)

        violations = []
        if missing_ids:
            violations.append(f"Missing step IDs in plan: {missing_ids}")
        if extra_ids:
            violations.append(f"Extra step IDs in plan: {extra_ids}")
        if not order_verified and not missing_ids and not extra_ids:
            violations.append(f"Sequence order mismatch between protocol and plan")

        passed = len(violations) == 0

        return {
            "gate": "GATE_1_PROTOCOL_TO_PLAN",
            "passed": passed,
            "total_protocol_steps": len(protocol_ids),
            "mapped_plan_steps": len(plan_ids),
            "order_verified": order_verified,
            "missing_step_ids": missing_ids,
            "extra_step_ids": extra_ids,
            "violations": violations
        }

    @staticmethod
    def verify_plan_to_playwright_code(plan_steps: List[Dict[str, Any]], spec_ts_code: str) -> Dict[str, Any]:
        violations = []
        missing_step_blocks = []
        skipped_steps = []
        assertion_violations = []
        screenshot_violations = []

        forbidden_patterns = [
            (r'test\.skip\s*\(', "Forbidden test.skip() detected"),
            (r'\.skip\s*\(', "Forbidden .skip() detected"),
            (r'test\.fixme\s*\(', "Forbidden test.fixme() detected"),
            (r'test\.todo\s*\(', "Forbidden test.todo() detected"),
            (r'//\s*await\s+expect\(', "Commented-out expect() assertion detected")
        ]
        for pattern, msg in forbidden_patterns:
            if re.search(pattern, spec_code := spec_ts_code):
                violations.append(msg)

        step_pattern = re.compile(
            r"await\s+test\.step\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*async\s*\(\s*\)\s*=>\s*\{([\s\S]*?)\n\s*\}\s*\);",
            re.MULTILINE
        )

        extracted_steps = []
        for match in step_pattern.finditer(spec_ts_code):
            raw_id = match.group(1).strip()
            id_match = re.match(r'(TS\d+-S\d+)', raw_id)
            step_id = id_match.group(1) if id_match else raw_id
            body = match.group(2)
            extracted_steps.append((step_id, body))

        extracted_step_ids = [s[0] for s in extracted_steps]
        plan_step_ids = [p["step_id"] for p in plan_steps]

        for pid in plan_step_ids:
            if pid not in extracted_step_ids:
                missing_step_blocks.append(pid)
                violations.append(f"Missing test.step block for step ID: {pid}")

        order_verified = (extracted_step_ids == plan_step_ids)
        if not order_verified and not missing_step_blocks:
            violations.append(f"Step blocks in .spec.ts out of sequence order: {extracted_step_ids} vs {plan_step_ids}")

        step_bodies = {s[0]: s[1] for s in extracted_steps}

        for step in plan_steps:
            sid = step["step_id"]
            if sid not in step_bodies:
                continue

            body = step_bodies[sid]
            actual_expects = len(re.findall(r'await\s+expect\s*\(', body))
            req_expects = step.get("required_assertions_count", 1)

            if actual_expects < req_expects:
                v_msg = f"Step {sid}: Required assertions = {req_expects}, found = {actual_expects}"
                assertion_violations.append(v_msg)
                violations.append(v_msg)

            if step.get("screenshot_required", False):
                evidence_call = f"captureEvidence(page, '{sid}')"
                if evidence_call not in body and f'captureEvidence(page, "{sid}")' not in body:
                    v_msg = f"Step {sid}: Screenshot required (µ) but {evidence_call} is missing"
                    screenshot_violations.append(v_msg)
                    violations.append(v_msg)

        passed = len(violations) == 0

        return {
            "gate": "GATE_2_PLAN_TO_PLAYWRIGHT_CODE",
            "passed": passed,
            "total_plan_steps": len(plan_step_ids),
            "verified_code_steps": len(extracted_step_ids),
            "order_verified": order_verified,
            "missing_step_blocks": missing_step_blocks,
            "skipped_steps": skipped_steps,
            "assertion_violations": assertion_violations,
            "screenshot_violations": screenshot_violations,
            "violations": violations
        }
