from __future__ import annotations

from playwright.sync_api import Page

from backend.app.services.execution.locator_resolver import (
    LocatorResolutionError,
    LocatorResolver,
)


class NavigationExecutor:
    def __init__(self, locator_resolver: LocatorResolver | None = None) -> None:
        self.locators = locator_resolver or LocatorResolver()

    def navigate_to_screen(
        self,
        page: Page,
        breadcrumb: tuple[str, ...],
        screen_title: str,
    ) -> None:
        if not breadcrumb:
            raise RuntimeError("Catalog screen has no observed navigation breadcrumb.")
        for index, label in enumerate(breadcrumb):
            next_label = breadcrumb[index + 1] if index < len(breadcrumb) - 1 else None
            target = self._resolve_breadcrumb_item(page, label, next_label)
            if next_label and self._has_visible_descendant(target, next_label):
                continue
            expanded = self._expanded_state(target)
            if expanded == "true" and index < len(breadcrumb) - 1:
                continue
            target.click()
            if index < len(breadcrumb) - 1:
                next_item = page.get_by_text(next_label or "", exact=True)
                next_item.first.wait_for(state="visible", timeout=5000)
        self._wait_for_screen(page, screen_title)

    def _resolve_breadcrumb_item(
        self,
        page: Page,
        label: str,
        next_label: str | None,
    ):
        try:
            return self.locators.resolve_click_target(page, label)
        except LocatorResolutionError:
            if not next_label:
                raise

        matches = page.get_by_text(label, exact=True)
        visible = []
        for index in range(matches.count()):
            candidate = matches.nth(index)
            if candidate.is_visible():
                visible.append(candidate)
        if len(visible) < 2:
            raise LocatorResolutionError(
                f"No unique visible navigation item matched {label!r}."
            )

        ranked = [
            (self._ancestor_distance(candidate, next_label), candidate)
            for candidate in visible
        ]
        best_distance = min(distance for distance, _ in ranked)
        best = [candidate for distance, candidate in ranked if distance == best_distance]
        if best_distance >= 12 or len(best) != 1:
            raise LocatorResolutionError(
                f"Navigation item {label!r} remains ambiguous for next breadcrumb {next_label!r}."
            )
        return best[0]

    @staticmethod
    def _has_visible_descendant(candidate, label: str) -> bool:
        ancestor = candidate
        for _ in range(12):
            matches = ancestor.get_by_text(label, exact=True)
            for index in range(matches.count()):
                if matches.nth(index).is_visible():
                    return True
            ancestor = ancestor.locator("xpath=..")
        return False

    @staticmethod
    def _ancestor_distance(candidate, descendant_label: str) -> int:
        ancestor = candidate
        for distance in range(12):
            target = ancestor.get_by_text(descendant_label, exact=True)
            for index in range(target.count()):
                if target.nth(index).is_visible():
                    return distance
            ancestor = ancestor.locator("xpath=..")
        return 12

    @staticmethod
    def _expanded_state(target) -> str | None:
        return target.evaluate(
            """element => {
                let current = element;
                while (current) {
                    const value = current.getAttribute?.('aria-expanded');
                    if (value !== null && value !== undefined) return value;
                    current = current.parentElement;
                }
                return null;
            }"""
        )

    @staticmethod
    def _wait_for_screen(page: Page, screen_title: str) -> None:
        heading = page.get_by_role("heading", name=screen_title, exact=True)
        if heading.count() > 0:
            heading.first.wait_for(state="visible", timeout=8000)
            return
        text = page.get_by_text(screen_title, exact=True)
        text.first.wait_for(state="visible", timeout=8000)
