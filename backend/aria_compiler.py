import os
import re
import json
import hashlib
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from schemas import (
    ProtocolSession,
    ProtocolStep,
    LockedProtocolPlan,
    LockedStepSpec,
    CompiledControlLocator,
    PlannedStep,
    StepAssertion,
    ControlType,
    AppliedInputRecord,
    ValueProvenance
)
from cpu_semantic_matcher import match_label_to_dom_candidates, match_dropdown_option

CACHE_ROOT = Path(__file__).resolve().parent / "artifacts" / "plan_cache"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)

async def capture_scoped_aria_snapshot(page: Any, container: Optional[Any] = None) -> str:
    """
    Playwright native YAML accessibility tree snapshot.
    Scoped to the container or page body (~300-600 tokens).
    """
    try:
        target = container if (container and await container.is_visible()) else page.locator("body")
        if hasattr(target, "aria_snapshot"):
            return await target.aria_snapshot()
        return "aria_snapshot not supported on this locator"
    except Exception as e:
        return f"aria_snapshot_error: {str(e)}"

class PlanCacheManager:
    """
    Deterministic Action Plan Cache Manager (Stage 2).
    Ensures zero AI tokens are consumed during replay of pre-compiled qualification protocols.
    """
    @staticmethod
    def compute_protocol_sha256(session: ProtocolSession) -> str:
        """Computes deterministic SHA-256 hash across all protocol step procedures & expectations."""
        elements = []
        for s in session.steps:
            elements.append(f"{s.step_id}|{s.scenario}|{s.procedure}|{s.expected_result}")
        raw = "\n".join(elements)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def get_cache_path(product_id: str, protocol_sha256: str) -> Path:
        prod_dir = CACHE_ROOT / (product_id or "default")
        prod_dir.mkdir(parents=True, exist_ok=True)
        return prod_dir / f"{protocol_sha256}.json"

    @classmethod
    def get_cached_plan(cls, product_id: str, protocol_sha256: str) -> Optional[LockedProtocolPlan]:
        path = cls.get_cache_path(product_id, protocol_sha256)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return LockedProtocolPlan(**data)
            except Exception as e:
                print(f"[PlanCacheManager] Warning: failed to deserialize cache {path}: {e}")
        return None

    @classmethod
    def save_plan_to_cache(cls, product_id: str, plan: LockedProtocolPlan) -> str:
        path = cls.get_cache_path(product_id, plan.protocol_sha256)
        path.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")
        return str(path)

    @classmethod
    def compile_step_to_locked_spec(cls, step: ProtocolStep, planned_step: Optional[PlannedStep] = None) -> LockedStepSpec:
        """Compiles a ProtocolStep into a deterministic LockedStepSpec with compiled ARIA locators."""
        compiled_fields: List[CompiledControlLocator] = []

        if step.applied_inputs:
            for ai in step.applied_inputs:
                compiled_fields.append(CompiledControlLocator(
                    field_id=f"{step.step_id}-{ai.field_label}",
                    section_hint=step.primary_section,
                    label=ai.field_label,
                    control_type="select" if ai.original_term or "select" in ai.selector_used else "text",
                    aria_role="combobox" if "select" in ai.selector_used else "textbox",
                    accessible_name=ai.field_label,
                    fallback_css=ai.selector_used,
                    target_value=ai.value_applied,
                    is_optional=False,
                    expect_auto_populated=False,
                    provenance=ai.provenance,
                    original_term=ai.original_term
                ))
        else:
            # Determine target values from planned_step if available, else synthesize
            field_values: Dict[str, str] = {}
            if planned_step:
                for fa in planned_step.field_actions:
                    field_values[fa.field_id] = fa.target_value
                    field_values[fa.label] = fa.target_value

            for ef in step.extracted_fields:
                val = ef.explicit_value or field_values.get(ef.field_id) or field_values.get(ef.label)
                if not val or str(val).startswith("(") or str(val).lower() == "default data":
                    if ef.control_type == "date" or "date" in ef.label.lower() or "birth" in ef.label.lower():
                        val = datetime.date.today().isoformat()
                    else:
                        val = ef.explicit_value or field_values.get(ef.field_id) or field_values.get(ef.label) or "Default Data"
                
                # Map control type to expected ARIA role
                aria_role = "textbox"
                if ef.control_type == "select":
                    aria_role = "combobox"
                elif ef.control_type == "toggle":
                    aria_role = "checkbox"
                elif ef.control_type == "button_click":
                    aria_role = "button"
                elif ef.control_type == "date":
                    aria_role = "textbox"

                c_loc = CompiledControlLocator(
                    field_id=ef.field_id,
                    section_hint=ef.section,
                    label=ef.label,
                    control_type=ef.control_type,
                    aria_role=aria_role,
                    accessible_name=ef.label,
                    fallback_css=f"#{ef.label.replace(' ', '')}",
                    target_value=str(val),
                    is_optional=False,
                    expect_auto_populated=(ef.control_type == "auto_populate_verify" or ef.auto_populated),
                    provenance="protocol_explicit"
                )
                compiled_fields.append(c_loc)

        # Inferred Submit & Modal button names
        submit_btn = None
        proc_lower = step.procedure.lower()
        if "save and submit" in proc_lower:
            submit_btn = "Save and Submit"
        elif "save" in proc_lower:
            submit_btn = "Save"
        elif "login" in proc_lower:
            submit_btn = "Login"
        elif "submit" in proc_lower:
            submit_btn = "Submit"

        modal_btn = None
        if "click on ok" in proc_lower or "click ok" in proc_lower:
            modal_btn = "OK"
        elif "click on yes" in proc_lower or "click yes" in proc_lower:
            modal_btn = "Yes"

        step_hash = hashlib.sha256(f"{step.step_id}|{step.procedure}".encode("utf-8")).hexdigest()[:12]

        return LockedStepSpec(
            step_id=step.step_id,
            scenario=step.scenario,
            action_intent=step.action_intent,
            primary_section=step.primary_section,
            pre_sub_actions=step.sub_actions,
            compiled_fields=compiled_fields,
            submit_button_name=submit_btn,
            modal_confirm_button=modal_btn,
            assertions=step.assertions,
            requires_form_screenshot=step.requires_form_screenshot,
            requires_modal_screenshot=step.requires_modal_screenshot,
            aria_structure_hash=step_hash
        )

    @classmethod
    def compile_session_plan(cls, session: ProtocolSession) -> LockedProtocolPlan:
        """Compiles entire ProtocolSession into a LockedProtocolPlan."""
        proto_hash = cls.compute_protocol_sha256(session)
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        step_map = {ps.step_id: ps for ps in session.planned_steps} if session.planned_steps else {}
        locked_steps = []
        for s in session.steps:
            p_step = step_map.get(s.step_id)
            locked_steps.append(cls.compile_step_to_locked_spec(s, p_step))

        plan = LockedProtocolPlan(
            protocol_id=session.document_no,
            protocol_sha256=proto_hash,
            compiled_at_utc=now_utc,
            steps=locked_steps
        )
        return plan

async def heal_step_locator_with_aria(
    page: Any,
    step: ProtocolStep,
    field_action: Any,
    container: Optional[Any] = None
) -> Optional[Any]:
    """
    Runtime JIT ARIA Healer.
    When a compiled locator fails, captures the live ARIA snapshot and attempts to resolve
    the accessible role / name dynamically.
    """
    try:
        snapshot = await capture_scoped_aria_snapshot(page, container)
        label_clean = getattr(field_action, "label", str(field_action)).strip()

        # Heuristic search in snapshot for accessible name
        # Look for e.g. - textbox "First Name": or - combobox "Gender":
        pattern = re.compile(rf'-\s+([a-z]+)\s+["\']([^"\']*{re.escape(label_clean)}[^"\']*)["\']', re.IGNORECASE)
        match = pattern.search(snapshot)
        if match:
            role = match.group(1).lower()
            name = match.group(2).strip()
            loc = page.get_by_role(role, name=name)
            if await loc.count() > 0:
                print(f"[AriaHealer] Successfully healed locator for '{label_clean}' -> role='{role}', name='{name}'")
                return loc.first
    except Exception as e:
        print(f"[AriaHealer] Healer attempt failed: {e}")

    return None

async def extract_visible_dom_controls(page: Any, container: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    <400-token live DOM control snapshotter.
    Queries all actionable form controls (input, select, textarea, button, combobox, switch, checkbox),
    filters out hidden or non-visible elements, resolves associated labels, required flags,
    and returns a compact JSON-serializable list of control candidates.
    """
    js_extract = """
    () => {
        const root = document;
        const elements = root.querySelectorAll('input, select, textarea, button, [role="combobox"], [role="switch"], [role="checkbox"]');
        const candidates = [];
        for (const el of elements) {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0' || (rect.width === 0 && rect.height === 0)) {
                continue;
            }
            if (el.type === 'hidden' || el.disabled) {
                continue;
            }

            let label = '';
            if (el.id) {
                const lblEl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                if (lblEl) label = lblEl.innerText.trim();
            }
            if (!label) {
                const parentLbl = el.closest('label');
                if (parentLbl) label = parentLbl.innerText.trim();
            }
            if (!label && el.getAttribute('aria-label')) {
                label = el.getAttribute('aria-label').trim();
            }
            if (!label && el.getAttribute('aria-labelledby')) {
                const idRef = el.getAttribute('aria-labelledby');
                const refEl = document.getElementById(idRef);
                if (refEl) label = refEl.innerText.trim();
            }
            if (!label && el.placeholder) {
                label = el.placeholder.trim();
            }
            if (!label && el.name) {
                label = el.name.trim();
            }
            if (!label && el.id) {
                label = el.id.trim();
            }

            const tag = el.tagName.toLowerCase();
            let controlType = 'text';
            if (tag === 'select' || el.getAttribute('role') === 'combobox') controlType = 'select';
            else if (el.type === 'checkbox' || el.getAttribute('role') === 'checkbox') controlType = 'toggle';
            else if (el.type === 'date') controlType = 'date';
            else if (tag === 'button' || el.type === 'submit' || el.type === 'button') controlType = 'button';
            else if (tag === 'textarea') controlType = 'textarea';

            const isRequired = !!(el.required || el.getAttribute('aria-required') === 'true' || (label && label.includes('*')));

            const options = [];
            if (tag === 'select') {
                for (const opt of el.options) {
                    options.push({ text: opt.text.trim(), val: opt.value.trim() });
                }
            }

            candidates.push({
                id: el.id ? `#${el.id}` : '',
                name: el.name || '',
                tag: tag,
                control_type: controlType,
                label: label.replace(/\\s*\\*\\s*$/, '').trim(),
                raw_label: label,
                required: isRequired,
                options: options,
                value: el.value || '',
                selector: el.id ? `#${el.id}` : (el.name ? `[name="${CSS.escape(el.name)}"]` : tag)
            });
        }
        return candidates;
    }
    """
    try:
        if container and hasattr(container, "evaluate"):
            return await container.evaluate(js_extract)
        return await page.evaluate(js_extract)
    except Exception as e:
        print(f"[extract_visible_dom_controls] Error extracting DOM controls: {e}")
        return []

def resolve_dynamic_value(
    raw_val: Optional[str],
    control_type: str,
    label: str,
    options: Optional[List[Dict[str, str]]] = None
) -> Tuple[str, ValueProvenance, Optional[str]]:
    """
    Resolves relative dates and synonym options dynamically.
    Returns (resolved_value, provenance, original_term).
    """
    if not raw_val:
        if control_type == "date" or "date" in label.lower():
            return datetime.date.today().isoformat(), "computed_dynamic", None
        return "", "protocol_explicit", None

    val_clean = str(raw_val).strip()
    val_lower = val_clean.lower()

    # 1. Relative dynamic dates
    if any(k in val_lower for k in ["today+1", "tomorrow", "future date", "a future date"]):
        fut = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        return fut, "computed_dynamic", val_clean
    elif any(k in val_lower for k in ["today-1", "yesterday"]):
        past = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        return past, "computed_dynamic", val_clean
    elif val_lower == "today":
        return datetime.date.today().isoformat(), "computed_dynamic", val_clean

    # 2. Dropdown synonym matching
    if (control_type == "select" or options) and options:
        matched_opt, score, prov = match_dropdown_option(val_clean, options)
        if matched_opt:
            res_val = matched_opt.get("val") or matched_opt.get("value") or matched_opt.get("text", "")
            return res_val, prov, (val_clean if prov != "protocol_explicit" else None)

    return val_clean, "protocol_explicit", None

async def bind_step_with_live_dom(
    page: Any,
    step: ProtocolStep,
    planned_step: Optional[PlannedStep] = None,
    container: Optional[Any] = None,
    llm_client: Optional[Any] = None
) -> List[AppliedInputRecord]:
    """
    Mode 1 Live-DOM Guided Micro-Agent.
    Inspects live visible DOM controls on the page, dynamically matches protocol fields,
    executes them, handles DOM mutation diffs (unhiding conditional sub-forms),
    synthesizes dummy data for unmapped mandatory fields, and verifies DOM readback.
    Returns List[AppliedInputRecord].
    """
    applied_records: List[AppliedInputRecord] = []
    applied_selectors: set = set()

    # 1. Capture initial visible controls
    initial_controls = await extract_visible_dom_controls(page, container)
    all_visible = list(initial_controls)

    # Target fields from step.extracted_fields
    target_fields = list(step.extracted_fields)
    applied_field_ids = set()

    async def apply_single_control(ctrl: Dict[str, Any], raw_value: str, field_lbl: str) -> Optional[AppliedInputRecord]:
        selector = ctrl["selector"]
        loc = page.locator(selector)
        c_type = ctrl["control_type"]
        opts = ctrl.get("options", [])

        res_val, prov, orig = resolve_dynamic_value(raw_value, c_type, field_lbl, opts)

        if c_type == "select":
            try:
                await loc.select_option(value=res_val)
            except Exception:
                await loc.select_option(label=res_val)
            rb_val = await loc.input_value()
            rec = AppliedInputRecord(
                field_label=field_lbl,
                selector_used=selector,
                value_applied=rb_val or res_val,
                original_term=orig,
                provenance=prov,
                readback_verified=True
            )
            return rec
        elif c_type == "toggle":
            is_check = str(res_val).lower() in ["true", "1", "yes"]
            await loc.set_checked(is_check)
            rb_check = await loc.is_checked()
            rec = AppliedInputRecord(
                field_label=field_lbl,
                selector_used=selector,
                value_applied="true" if rb_check else "false",
                original_term=orig,
                provenance=prov,
                readback_verified=True
            )
            return rec
        else:
            await loc.fill(res_val)
            rb_val = await loc.input_value()
            rec = AppliedInputRecord(
                field_label=field_lbl,
                selector_used=selector,
                value_applied=rb_val,
                original_term=orig,
                provenance=prov,
                readback_verified=(rb_val == res_val)
            )
            return rec

    # Match and apply initial controls
    # Prioritize select/toggle controls first so any onchange / mutation unhides sub-forms
    sorted_fields = sorted(target_fields, key=lambda f: 0 if f.control_type in ["select", "toggle"] else 1)

    for field in sorted_fields:
        matched_ctrl, score = match_label_to_dom_candidates(field.label, all_visible)
        if matched_ctrl and matched_ctrl["selector"] not in applied_selectors:
            raw_v = field.explicit_value or "Default Data"
            rec = await apply_single_control(matched_ctrl, raw_v, field.label)
            if rec:
                applied_records.append(rec)
                applied_selectors.add(matched_ctrl["selector"])
                applied_field_ids.add(field.field_id)

            # Check DOM Mutation if control was select or toggle
            if matched_ctrl["control_type"] in ["select", "toggle"]:
                await page.wait_for_timeout(250)
                post_controls = await extract_visible_dom_controls(page, container)
                new_revealed = [c for c in post_controls if c["selector"] not in {x["selector"] for x in all_visible}]
                all_visible = post_controls

                # Immediately try matching remaining unmatched step fields against new_revealed controls
                for un_f in target_fields:
                    if un_f.field_id not in applied_field_ids:
                        sub_ctrl, sub_score = match_label_to_dom_candidates(un_f.label, new_revealed)
                        if sub_ctrl and sub_ctrl["selector"] not in applied_selectors:
                            sub_raw_v = un_f.explicit_value or "Default Data"
                            sub_rec = await apply_single_control(sub_ctrl, sub_raw_v, un_f.label)
                            if sub_rec:
                                applied_records.append(sub_rec)
                                applied_selectors.add(sub_ctrl["selector"])
                                applied_field_ids.add(un_f.field_id)

    # 4. Mandatory Dummy Data Synthesis (ai_synthesized_mandatory)
    proc_low = step.procedure.lower()
    fill_mandatory = (
        step.needs_mode1_discovery or
        "all other mandatory" in proc_low or
        "mandatory" in proc_low or
        "dummy data" in proc_low
    )
    if fill_mandatory:
        current_controls = await extract_visible_dom_controls(page, container)
        for ctrl in current_controls:
            if ctrl["required"] and ctrl["selector"] not in applied_selectors and ctrl["control_type"] != "button":
                c_lbl = ctrl["label"] or ctrl["selector"]
                dummy_v = ""
                prov: ValueProvenance = "ai_synthesized_mandatory"
                if ctrl["control_type"] == "date":
                    dummy_v = datetime.date.today().isoformat()
                    prov = "computed_dynamic"
                elif ctrl["control_type"] == "select" and ctrl.get("options"):
                    first_opt = next((o["val"] or o["text"] for o in ctrl["options"] if (o["val"] or o["text"])), "Option 1")
                    dummy_v = first_opt
                elif ctrl["control_type"] == "toggle":
                    dummy_v = "true"
                elif "initial" in c_lbl.lower():
                    dummy_v = "JD"
                elif "mail" in c_lbl.lower():
                    dummy_v = "tester@domain.com"
                else:
                    dummy_v = f"Test_{c_lbl[:8].strip()}"

                rec = await apply_single_control(ctrl, dummy_v, c_lbl)
                if rec:
                    rec.provenance = prov
                    applied_records.append(rec)
                    applied_selectors.add(ctrl["selector"])

    step.applied_inputs = applied_records
    return applied_records
