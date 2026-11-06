from __future__ import annotations

from typing import Any

from playwright.sync_api import Locator, Page


class LocatorResolutionError(RuntimeError):
    pass


class LocatorResolver:
    """Resolve only user-facing accessible names; ambiguity always stops the run."""

    def resolve_click_target(self, page: Page, name: str) -> Locator:
        return self._named_control(page, name, ("button", "link", "menuitem", "tab"))

    def resolve_field(self, scope: Locator, label: str) -> Locator:
        labelled = scope.get_by_label(label, exact=True)
        resolved = self._unique_visible(labelled, f"field label {label!r}", allow_missing=True)
        if resolved is not None:
            return resolved
        for role in ("textbox", "combobox", "checkbox", "switch", "radio", "spinbutton"):
            candidate = scope.get_by_role(role, name=label, exact=True)
            resolved = self._unique_visible(
                candidate,
                f"{role} named {label!r}",
                allow_missing=True,
            )
            if resolved is not None:
                return resolved

        # Some SPAs render a visible label beside its control without wiring
        # label[for] or an accessible name. Walk upward from the exact visible
        # label and accept only the nearest container with one visible form
        # control. This stays scoped to the selected section and fails closed
        # when the visual relationship is ambiguous.
        label_text = scope.get_by_text(label, exact=True)
        control_selector = (
            "input:not([type='hidden']), textarea, select, "
            "[role='textbox'], [role='combobox'], [role='checkbox'], "
            "[role='switch'], [role='radio'], [role='spinbutton']"
        )
        associated: list[Locator] = []
        for label_index in range(label_text.count()):
            visible_label = label_text.nth(label_index)
            try:
                if not visible_label.is_visible():
                    continue
            except Exception:
                continue
            container = visible_label
            for _ in range(8):
                container = container.locator("xpath=..")
                controls = container.locator(control_selector)
                visible_controls = [
                    controls.nth(control_index)
                    for control_index in range(controls.count())
                    if controls.nth(control_index).is_visible()
                ]
                if len(visible_controls) == 1:
                    associated.append(visible_controls[0])
                    break
                if len(visible_controls) > 1:
                    break
        if len(associated) == 1:
            control = associated[0]
            if not control.is_enabled():
                raise LocatorResolutionError(f"Target field {label!r} is disabled.")
            return control
        if len(associated) > 1:
            raise LocatorResolutionError(
                f"Visible label {label!r} was associated with multiple field containers."
            )
        raise LocatorResolutionError(f"No unique visible accessible field matched {label!r}.")

    def section_scope(self, page: Page, label: str) -> Locator:
        for role in ("region", "tabpanel", "group"):
            candidate = page.get_by_role(role, name=label, exact=True)
            resolved = self._unique_visible(
                candidate,
                f"{role} section {label!r}",
                allow_missing=True,
            )
            if resolved is not None:
                return resolved

        heading = self._named_control(page, label, ("heading",))
        for ancestor_selector in (
            "xpath=ancestor::*[@role='region'][1]",
            "xpath=ancestor::*[@role='tabpanel'][1]",
            "xpath=ancestor::section[1]",
            "xpath=ancestor::fieldset[1]",
            "xpath=..",
        ):
            ancestor = heading.locator(ancestor_selector)
            resolved = self._unique_visible(
                ancestor,
                f"container for section {label!r}",
                allow_missing=True,
            )
            if resolved is not None:
                return resolved
        raise LocatorResolutionError(f"No unique visible accessible section matched {label!r}.")

    def open_section(self, page: Page, label: str) -> Locator:
        # Section labels come from the retrieved catalog plan. Waiting for the
        # live label handles SPA screens whose shell appears before form content.
        page.get_by_text(label, exact=True).first.wait_for(
            state="visible",
            timeout=20000,
        )
        scope = self._section_container(page, label)
        if scope is not None:
            return scope

        header = self._named_control(page, label, ("button", "tab", "heading"))
        expanded = header.get_attribute("aria-expanded")
        if expanded != "true":
            header.click()
        for role in ("region", "tabpanel", "group"):
            candidate = page.get_by_role(role, name=label, exact=True)
            resolved = self._unique_visible(
                candidate,
                f"opened {role} section {label!r}",
                allow_missing=True,
            )
            if resolved is not None:
                return resolved
        return self.section_scope(page, label)

    def _section_container(self, page: Page, label: str) -> Locator | None:
        for role in ("region", "tabpanel", "group"):
            resolved = self._unique_visible(
                page.get_by_role(role, name=label, exact=True),
                f"{role} section {label!r}",
                allow_missing=True,
            )
            if resolved is not None:
                return resolved
        return None

    def _named_control(self, page: Page, name: str, roles: tuple[str, ...]) -> Locator:
        for role in roles:
            exact = page.get_by_role(role, name=name, exact=True)
            resolved = self._unique_visible(
                exact,
                f"{role} named {name!r}",
                allow_missing=True,
            )
            if resolved is not None:
                return resolved
            case_insensitive = page.get_by_role(role, name=name, exact=False)
            resolved = self._unique_visible(
                case_insensitive,
                f"{role} matching {name!r}",
                allow_missing=True,
            )
            if resolved is not None:
                return resolved
        text = page.get_by_text(name, exact=True)
        resolved = self._unique_visible(text, f"visible text {name!r}", allow_missing=True)
        if resolved is not None:
            return resolved
        raise LocatorResolutionError(f"No unique visible control matched {name!r}.")

    @staticmethod
    def _unique_visible(
        locator: Locator,
        description: str,
        *,
        allow_missing: bool = False,
    ) -> Locator | None:
        visible: list[Locator] = []
        for index in range(locator.count()):
            candidate = locator.nth(index)
            try:
                if candidate.is_visible():
                    visible.append(candidate)
            except Exception:
                continue
        if not visible and allow_missing:
            return None
        if len(visible) != 1:
            raise LocatorResolutionError(
                f"Expected exactly one visible match for {description}; found {len(visible)}."
            )
        candidate = visible[0]
        try:
            if not candidate.is_enabled():
                raise LocatorResolutionError(f"Target {description} is disabled.")
        except LocatorResolutionError:
            raise
        except Exception:
            # Non-form text and headings may not expose enabled state.
            pass
        return candidate


def read_value(locator: Locator) -> Any:
    try:
        return locator.input_value()
    except Exception:
        checked = locator.get_attribute("aria-checked")
        if checked is not None:
            return checked == "true"
        checked = locator.get_attribute("checked")
        if checked is not None:
            return True
        return locator.inner_text()
