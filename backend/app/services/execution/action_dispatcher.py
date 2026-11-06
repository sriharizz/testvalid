from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Locator, Page

from backend.app.services.compilation.action_plan_compiler import PlanOperation
from backend.app.services.execution.locator_resolver import LocatorResolver, read_value


class ActionExecutionError(RuntimeError):
    pass


class ActionDispatcher:
    def __init__(self, locator_resolver: LocatorResolver | None = None) -> None:
        self.locators = locator_resolver or LocatorResolver()

    def dispatch(self, page: Page, operation: PlanOperation) -> None:
        if operation.kind == "open_section":
            self.locators.open_section(page, operation.target_label or "")
        elif operation.kind == "fill_field":
            self._fill_field(page, operation)
        elif operation.kind == "click_control":
            target = self.locators.resolve_click_target(page, operation.target_label or "")
            target.click()
        elif operation.kind == "capture_screenshot":
            return
        else:
            raise ActionExecutionError(f"Unsupported operation kind: {operation.kind}")

    def _fill_field(self, page: Page, operation: PlanOperation) -> None:
        section_label = operation.screen_path[-1] if operation.screen_path else ""
        scope = self.locators.section_scope(page, section_label)
        field = self.locators.resolve_field(scope, operation.target_label or "")
        kind = (operation.control_kind or "").casefold()
        value = operation.value

        if kind in {"switch", "checkbox", "toggle", "boolean"}:
            desired = _to_bool(value)
            current = _current_checked(field)
            if current != desired:
                field.click()
            observed = _current_checked(field)
            if observed != desired:
                raise ActionExecutionError(
                    f"Readback mismatch for boolean field {operation.target_label!r}."
                )
            return

        tag_name = str(field.evaluate("element => element.tagName.toLowerCase()"))
        if kind in {"dropdown", "select", "combobox", "mat-select"}:
            self._select_option(page, field, operation, tag_name)
            return

        text_value = "" if value is None else str(value)
        field.fill(text_value)
        observed = read_value(field)
        if str(observed) != text_value:
            raise ActionExecutionError(
                f"Readback mismatch for field {operation.target_label!r}."
            )

    def _select_option(
        self,
        page: Page,
        field: Locator,
        operation: PlanOperation,
        tag_name: str,
    ) -> None:
        value = "" if operation.value is None else str(operation.value)
        if tag_name == "select":
            field.select_option(label=value)
            selected = field.locator("option:checked").inner_text()
            if selected.strip() != value:
                raise ActionExecutionError(
                    f"Readback mismatch for dropdown {operation.target_label!r}."
                )
            return

        field.click()
        if operation.value_mode == "runtime_search":
            try:
                field.fill(value)
            except Exception:
                self._fill_runtime_search(page, value, operation)
        option = page.get_by_role("option", name=value, exact=True)
        option.first.wait_for(state="visible", timeout=5000)
        option = self.locators._unique_visible(option, f"dropdown option {value!r}")
        option.click()
        observed = " ".join(read_value(field).split())
        if observed != value:
            raise ActionExecutionError(
                f"Readback mismatch for dropdown {operation.target_label!r}."
            )

    def _fill_runtime_search(
        self,
        page: Page,
        value: str,
        operation: PlanOperation,
    ) -> None:
        if operation.search_input_label:
            candidates = page.get_by_role(
                "textbox",
                name=operation.search_input_label,
                exact=True,
            )
            try:
                unique = self.locators._unique_visible(
                    candidates,
                    f"dropdown search {operation.search_input_label!r}",
                )
                unique.fill(value)
                return
            except Exception:
                # A catalog label may not be wired to an accessible textbox;
                # fall through to the currently open listbox scope.
                pass

        listboxes = page.get_by_role("listbox")
        visible_listboxes = [
            listboxes.nth(index)
            for index in range(listboxes.count())
            if listboxes.nth(index).is_visible()
        ]
        if len(visible_listboxes) != 1:
            raise ActionExecutionError(
                f"Runtime dropdown search for {operation.target_label!r} has no unique open listbox."
            )
        candidates = visible_listboxes[0].get_by_role("textbox")
        visible = [
            candidates.nth(index)
            for index in range(candidates.count())
            if candidates.nth(index).is_visible()
        ]
        if len(visible) != 1:
            raise ActionExecutionError(
                f"Runtime dropdown search for {operation.target_label!r} is ambiguous."
            )
        visible[0].fill(value)


def _to_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().casefold()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    raise ActionExecutionError("Boolean control received a non-boolean value.")


def _current_checked(locator: Locator) -> bool:
    try:
        return locator.is_checked()
    except Exception:
        state = locator.get_attribute("aria-checked")
        if state in {"true", "false"}:
            return state == "true"
        raise ActionExecutionError("Control does not expose an accessible checked state.")
