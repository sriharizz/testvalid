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
    ControlType
)

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

        # Determine target values from planned_step if available, else synthesize
        field_values: Dict[str, str] = {}
        if planned_step:
            for fa in planned_step.field_actions:
                field_values[fa.field_id] = fa.target_value
                field_values[fa.label] = fa.target_value

        for ef in step.extracted_fields:
            val = ef.explicit_value or field_values.get(ef.field_id) or field_values.get(ef.label) or "Default Data"
            
            # Map control type to expected ARIA role
            aria_role = "textbox"
            if ef.control_type == "select":
                aria_role = "combobox"
            elif ef.control_type == "toggle":
                aria_role = "checkbox"
            elif ef.control_type == "button_click":
                aria_role = "button"

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
                expect_auto_populated=(ef.control_type == "auto_populate_verify" or ef.auto_populated)
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
