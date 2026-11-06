from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from urllib.parse import urlparse

from playwright.sync_api import Page

from backend.app.services.compilation.action_plan_compiler import (
    CompiledActionPlan,
    PlanOperation,
)
from backend.app.services.execution.action_dispatcher import ActionDispatcher
from backend.app.services.execution.navigation_executor import NavigationExecutor
from backend.app.services.execution.run_context import PlaywrightRunContext


@dataclass
class PlaywrightRunResult:
    status: str
    run_id: str
    artifact_directory: str
    completed_operations: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    blocked_operation: str | None = None
    failure: str | None = None


class PlaywrightRunner:
    """Execute only compiled operations; ambiguous targets fail closed."""

    def __init__(
        self,
        dispatcher: ActionDispatcher | None = None,
        navigator: NavigationExecutor | None = None,
        after_navigation: Callable[[Page], None] | None = None,
    ) -> None:
        self.dispatcher = dispatcher or ActionDispatcher()
        self.navigator = navigator or NavigationExecutor()
        self.after_navigation = after_navigation

    def execute(
        self,
        page: Page,
        plan: CompiledActionPlan,
        context: PlaywrightRunContext,
    ) -> PlaywrightRunResult:
        self._preflight(page, plan, context)
        run_directory = context.prepare()
        result = PlaywrightRunResult(
            status="RUNNING",
            run_id=context.run_id,
            artifact_directory=str(run_directory),
        )

        try:
            for index, operation in enumerate(plan.operations, start=1):
                if operation.kind == "click_control" and not context.allow_mutations:
                    result.status = "BLOCKED"
                    result.blocked_operation = operation.target_label
                    break

                if operation.kind == "navigate_screen":
                    self.navigator.navigate_to_screen(
                        page,
                        operation.screen_path,
                        operation.target_label or plan.screen_title,
                    )
                    if self.after_navigation is not None:
                        self.after_navigation(page)
                elif operation.kind == "capture_screenshot":
                    self._capture(page, context, run_directory, result, operation, index)
                else:
                    self.dispatcher.dispatch(page, operation)
                result.completed_operations.append(operation.kind)

        except Exception as error:
            result.status = "FAILED"
            result.failure = f"{type(error).__name__}: {error}"
            try:
                self._capture_failure(page, context, run_directory, result)
            except Exception:
                pass
        else:
            if result.status == "RUNNING":
                result.status = "COMPLETED"

        self._write_result(run_directory, result)
        return result

    @staticmethod
    def _preflight(
        page: Page,
        plan: CompiledActionPlan,
        context: PlaywrightRunContext,
    ) -> None:
        if plan.application != context.application:
            raise ValueError("Compiled plan application does not match the execution context.")
        if plan.environment.casefold() != context.environment.casefold():
            raise ValueError("Compiled plan environment does not match the execution context.")
        if context.environment.casefold() in {"production", "prod"}:
            raise ValueError("Production execution is blocked.")
        expected = urlparse(context.base_url)
        current = urlparse(page.url)
        if current.hostname and current.hostname.casefold() != (expected.hostname or "").casefold():
            raise ValueError("Authenticated browser is not on the configured product host.")

    @staticmethod
    def _capture(
        page: Page,
        context: PlaywrightRunContext,
        run_directory: Path,
        result: PlaywrightRunResult,
        operation: PlanOperation,
        index: int,
    ) -> None:
        label = operation.target_label or operation.kind
        stem = f"{index:03d}_{_slug(label)}"
        image_path = run_directory / f"{stem}.png"
        image_bytes = page.screenshot(full_page=context.full_page_screenshots)
        image_path.write_bytes(image_bytes)
        result.screenshots.append(str(image_path))
        _write_sidecar(
            image_path.with_suffix(".json"),
            {
                "run_id": context.run_id,
                "captured_at_utc": _now(),
                "capture_point": label,
                "operation": operation.kind,
                "source_step_ref": operation.source_step_ref,
                "screenshot_file": image_path.name,
            },
        )

    @staticmethod
    def _capture_failure(
        page: Page,
        context: PlaywrightRunContext,
        run_directory: Path,
        result: PlaywrightRunResult,
    ) -> None:
        image_path = run_directory / "failure.png"
        image_path.write_bytes(page.screenshot(full_page=context.full_page_screenshots))
        result.screenshots.append(str(image_path))
        _write_sidecar(
            image_path.with_suffix(".json"),
            {
                "run_id": context.run_id,
                "captured_at_utc": _now(),
                "capture_point": "failure",
                "screenshot_file": image_path.name,
            },
        )

    @staticmethod
    def _write_result(directory: Path, result: PlaywrightRunResult) -> None:
        _write_sidecar(directory / "run_result.json", result.__dict__)


def _write_sidecar(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return slug[:64] or "capture"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
