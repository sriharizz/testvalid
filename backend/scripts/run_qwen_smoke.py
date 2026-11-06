from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
import re
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

# Direct script execution places backend/scripts on sys.path, so add the repo
# root before importing the application package.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.domain.ui_catalog import CatalogSnapshot
from backend.app.infrastructure.catalog_repository import JsonCatalogRepository
from backend.app.schemas.data_generation import (
    DataGenerationEnvelope,
    DataGenerationOutput,
    GenerationValidationReport,
)
from backend.app.services.catalog.catalog_manager import CatalogManager
from backend.app.services.compilation.action_plan_compiler import ActionPlanCompiler
from backend.app.services.execution.playwright_runner import PlaywrightRunner
from backend.app.services.execution.run_context import PlaywrightRunContext


DEFAULT_EVALUATION = ROOT / "backend/artifacts/qwen_evaluations/phase4-human-batch-20261105T094354Z.json"
CATALOG = ROOT / "catalog/ui/application_catalog.json"
MANIFEST = ROOT / "catalog/ui/discovery_manifest.json"

# Temporary smoke-only option substitutions, approved for this manual run.
# The saved Qwen evaluation remains unchanged; remove these after the smoke test.
TEMP_SMOKE_OPTION_OVERRIDES: dict[str, dict[tuple[str, str], str]] = {
    "human-01-reporter-details": {
        ("Relationship With Patient Code", "Physician"): "Vaccine Provider",
        ("Reporter Type Code", "Healthcare Professional"): "Physician",
        ("Title", "Dr."): "Mr.",
    },
    "human-04-reporter-country": {
        ("Relationship With Patient Code", "Patient"): "Patient/Parent",
    },
}


def _guard_extra_pages(context: object, main_page: object) -> list[object]:
    sessions: list[object] = []

    def attach(page: object) -> None:
        try:
            session = page.context.new_cdp_session(page)
            session.send("Debugger.enable")
            session.send("Debugger.setSkipAllPauses", {"skip": True})
            session.send("Debugger.setBreakpointsActive", {"active": False})

            def resume(_event: object) -> None:
                try:
                    session.send("Debugger.resume")
                except Exception:
                    pass

            session.on("Debugger.paused", resume)
            sessions.append(session)
        except Exception:
            pass
        if page is not main_page:
            try:
                page.close()
            except Exception:
                pass

    context.on("page", attach)
    for page in context.pages:
        attach(page)
    return sessions


def _resume_browser_page_targets(browser: object) -> tuple[object, int]:
    browser_session = browser.new_browser_cdp_session()
    targets = browser_session.send("Target.getTargets").get("targetInfos", [])
    attached_sessions: list[str] = []
    for target in targets:
        if target.get("type") != "page":
            continue
        attached = browser_session.send(
            "Target.attachToTarget",
            {"targetId": target["targetId"], "flatten": False},
        )
        session_id = attached["sessionId"]
        attached_sessions.append(session_id)
        for message_id, method, params in (
            (1, "Debugger.enable", {}),
            (2, "Debugger.setBreakpointsActive", {"active": False}),
            (3, "Debugger.setSkipAllPauses", {"skip": True}),
            (4, "Debugger.resume", {}),
        ):
            browser_session.send(
                "Target.sendMessageToTarget",
                {
                    "sessionId": session_id,
                    "message": json.dumps(
                        {"id": message_id, "method": method, "params": params}
                    ),
                },
            )
    return browser_session, len(attached_sessions)


def _load_case(
    evaluation_path: Path,
    case_id: str,
    snapshot: CatalogSnapshot,
) -> DataGenerationEnvelope:
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    cases = evaluation.get("parsed_output", {}).get("cases", [])
    case = next((item for item in cases if item.get("case_id") == case_id), None)
    if case is None:
        raise ValueError(f"Case {case_id!r} is missing from the saved Qwen evaluation.")
    if case.get("status") != "ready":
        raise ValueError("Saved Qwen output is not marked ready.")

    output_payload = {key: value for key, value in case.items() if key != "case_id"}
    output = DataGenerationOutput.model_validate(output_payload)
    retrieved_ids = {
        action.target_ref
        for action in output.action_intents
        if action.target_ref
    }
    retrieved_ids.update(value.field_ref for value in output.field_values)
    return DataGenerationEnvelope(
        output=output,
        validation=GenerationValidationReport(status="ready"),
        provider=str(evaluation.get("provider", "saved-evaluation")),
        model_name=str(evaluation.get("model", "unknown")),
        prompt_version=str(evaluation.get("prompt_version", "unknown")),
        catalog_snapshot_id=snapshot.snapshot_id,
        retrieved_card_ids=sorted(retrieved_ids),
        retrieval_selection_mode="saved_qwen_smoke",
    )


def _apply_temp_option_overrides(plan, case_id: str):
    replacements = TEMP_SMOKE_OPTION_OVERRIDES.get(case_id, {})
    if not replacements:
        return plan
    operations = []
    applied = set()
    for operation in plan.operations:
        key = (operation.target_label or "", str(operation.value))
        replacement = replacements.get(key) if operation.kind == "fill_field" else None
        if replacement is not None:
            print(
                f"Temporary smoke override for {case_id}: "
                f"{key[0]} {key[1]!r} -> {replacement!r}"
            )
            operation = operation.model_copy(
                update={"value": replacement, "value_mode": "runtime_search"}
            )
            applied.add(key)
        operations.append(operation)
    if applied != set(replacements):
        missing = sorted(set(replacements) - applied)
        raise ValueError(f"Temporary dropdown overrides did not match plan fields: {missing!r}")
    return plan.model_copy(update={"operations": operations})


def _wait_for_login(page) -> None:
    while urlparse(page.url).path.rstrip("/").casefold() == "/login":
        input(
            "Log in in this opened Edge window. After it redirects away from /login, "
            "return here and press Enter: "
        )
        page.wait_for_timeout(1000)
        if urlparse(page.url).path.rstrip("/").casefold() == "/login":
            print("The browser is still on /login; the smoke test has not started.")


def _minimize_visible_panels(page) -> bool:
    """Collapse a floating panel using an accessible name or its rendered header."""
    # page.frames already includes the main frame; avoid scanning it twice.
    scopes = list(page.frames)
    named_matches = []
    for scope in scopes:
        candidates = scope.locator("button, [role='button']")
        for index in range(candidates.count()):
            candidate = candidates.nth(index)
            try:
                if not candidate.is_visible() or not candidate.is_enabled():
                    continue
                accessible_name = candidate.get_attribute("aria-label") or ""
                title = candidate.get_attribute("title") or ""
                text = candidate.inner_text(timeout=500).strip()
                name = " ".join((accessible_name, title, text)).casefold()
                if re.search(r"\bminimi[sz]e\b", name):
                    named_matches.append(candidate)
            except Exception:
                continue

    if len(named_matches) > 1:
        raise RuntimeError(
            "More than one visible control is labeled Minimize; refusing an ambiguous click."
        )
    if named_matches:
        named_matches[0].click()
        return True

    # Some embedded widgets render icon-only controls without accessible names.
    # Find the visible widget title in any frame, then act only on three controls
    # aligned to its right in the same header row.
    visible_headings = []
    for scope in scopes:
        headings = scope.get_by_text("Amazon Connect", exact=True)
        visible_headings.extend(
            (scope, headings.nth(index))
            for index in range(headings.count())
            if headings.nth(index).is_visible()
        )
    if len(visible_headings) != 1:
        return False
    scope, heading = visible_headings[0]
    heading_handle = heading.element_handle()
    if heading_handle is None:
        return False

    # The observed widget exposes its three header icons without button roles.
    # Identify their live DOM elements by pointer cursor and alignment to the
    # title. Group nested icon nodes by horizontal center, then click through a
    # Playwright ElementHandle so normal actionability checks still apply.
    target = scope.evaluate_handle(
        """(heading) => {
          const title = heading.getBoundingClientRect();
          const titleHeight = title.height;
          if (!title.width || !titleHeight) return null;
          const candidates = [...document.querySelectorAll('body *')].filter((el) => {
            const style = getComputedStyle(el);
            const box = el.getBoundingClientRect();
            const centerY = box.top + box.height / 2;
            const sameRow = Math.abs(centerY - (title.top + titleHeight / 2)) <= titleHeight;
            const rightSide = box.left >= title.right;
            const iconSized = box.width > 0 && box.height > 0 &&
              box.width <= titleHeight * 2.5 && box.height <= titleHeight * 2.5;
            return style.cursor === 'pointer' && sameRow && rightSide && iconSized &&
              style.visibility !== 'hidden' && style.display !== 'none';
          });
          const groups = [];
          for (const el of candidates) {
            const box = el.getBoundingClientRect();
            const centerX = box.left + box.width / 2;
            let group = groups.find((item) => Math.abs(item.centerX - centerX) <= titleHeight / 3);
            if (!group) {
              group = { centerX, elements: [] };
              groups.push(group);
            }
            group.elements.push(el);
          }
          groups.sort((a, b) => a.centerX - b.centerX);
          if (groups.length !== 3) return null;
          const first = groups[0].elements.sort((a, b) => {
            const ar = a.getBoundingClientRect();
            const br = b.getBoundingClientRect();
            return (br.width * br.height) - (ar.width * ar.height);
          });
          return first[0] || null;
        }""",
        heading_handle,
    )
    element = target.as_element()
    if element is None:
        return False
    element.click()
    return True


def _after_navigation(page) -> None:
    if _minimize_visible_panels(page):
        print("Minimized the visible panel using its live header controls.")
    else:
        print("No unambiguous visible panel minimize control was found.")
    progressbars = page.get_by_role("progressbar")
    for index in range(progressbars.count()):
        progressbar = progressbars.nth(index)
        if progressbar.is_visible():
            progressbar.wait_for(state="hidden", timeout=20000)


def _reset_smoke_form(page) -> None:
    page.keyboard.press("Escape")
    reset = page.get_by_role("button", name="Reset", exact=True)
    if reset.count() != 1 or not reset.is_visible() or not reset.is_enabled():
        raise RuntimeError("Could not uniquely resolve the form Reset button between smoke cases.")
    reset.click()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one saved Qwen case against an authenticated development UI."
    )
    parser.add_argument("--base-url", default="https://dev.one-aipv.com/login")
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--allow-mutations", action="store_true")
    args = parser.parse_args()

    if args.allow_mutations:
        parser.error("This smoke script intentionally blocks Save/Submit/Delete actions.")
    if not args.evaluation.is_file():
        parser.error("Saved Qwen evaluation file was not found.")

    with tempfile.TemporaryDirectory(prefix="testvauto-catalog-") as temporary_root:
        manager = CatalogManager(JsonCatalogRepository(Path(temporary_root) / "catalog"))
        snapshot = manager.import_file(CATALOG, MANIFEST)
        case_ids = args.case_ids or ["human-01-reporter-details"]
        plans = []
        for case_id in case_ids:
            envelope = _load_case(args.evaluation, case_id, snapshot)
            plan = ActionPlanCompiler().compile(envelope, snapshot)
            plan = _apply_temp_option_overrides(plan, case_id)
            plans.append((case_id, plan))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="msedge",
            headless=False,
            args=["--new-window"],
        )
        close_browser_on_exit = True
        browser_context = browser.new_context()
        page = browser_context.new_page()
        browser_debug_session, recovered_target_count = _resume_browser_page_targets(browser)
        try:
            debugger_sessions = _guard_extra_pages(browser_context, page)
            page.goto(args.base_url, wait_until="domcontentloaded")
            print("The Playwright-controlled Edge window is open at the configured login URL.")
            print(
                "Debugger recovery attached to "
                f"{recovered_target_count} browser page target(s) and "
                f"{len(debugger_sessions)} Playwright page(s); extra pages close automatically."
            )
            _wait_for_login(page)
            for extra_page in list(browser_context.pages):
                if extra_page is not page:
                    try:
                        extra_page.close()
                    except Exception:
                        pass
            results = []
            for index, (case_id, plan) in enumerate(plans):
                if index:
                    _reset_smoke_form(page)
                print(f"Starting saved Qwen case {case_id} ({index + 1}/{len(plans)}).")
                run_context = PlaywrightRunContext(
                    application=plan.application,
                    environment=plan.environment,
                    base_url=args.base_url,
                    artifact_root=ROOT / "backend/artifacts/screenshots/playwright_runs",
                    headless=False,
                    allow_mutations=False,
                    full_page_screenshots=True,
                )
                result = PlaywrightRunner(after_navigation=_after_navigation).execute(
                    page,
                    plan,
                    run_context,
                )
                results.append((case_id, result))
                print(json.dumps({"case_id": case_id, **result.__dict__}, ensure_ascii=False, indent=2))

            summary = [
                {
                    "case_id": case_id,
                    "status": result.status,
                    "completed_fill_operations": result.completed_operations.count("fill_field"),
                    "blocked_operation": result.blocked_operation,
                    "failure": result.failure,
                    "artifact_directory": result.artifact_directory,
                }
                for case_id, result in results
            ]
            print("Batch summary:")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            close_browser_on_exit = False
            input("Inspect the final case in Edge; press Enter when finished reviewing: ")
            close_browser_on_exit = True
            return 1 if any(result.status == "FAILED" for _, result in results) else 0
        finally:
            if close_browser_on_exit:
                browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
