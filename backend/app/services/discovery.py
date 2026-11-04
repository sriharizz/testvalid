from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from backend.app.domain.ui_discovery import (
    DiscoveryCoverage,
    DiscoveryEvidence,
    DiscoveryIssue,
    UIControlObservation,
    UIDiscoveryResult,
    UIRelationshipObservation,
    UIOptionObservation,
    UISectionObservation,
    UIScreenObservation,
    UITableObservation,
)


_NAV_SELECTOR = 'nav a, [role="navigation"] a'
_DANGEROUS_WORDS = {
    "save", "submit", "delete", "update", "register", "create", "edit",
    "approve", "sign", "send", "finalize", "finalise", "remove", "publish",
    "execute", "confirm", "logout", "log out", "sign out",
}
_LOGIN_SELECTOR = 'input[type="password"]:visible'

_INSPECT_SCRIPT = r"""() => {
  const visible = (el) => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const compact = (value, limit = 160) => {
    if (!value) return null;
    const text = String(value).replace(/\s+/g, ' ').trim();
    return text ? text.slice(0, limit) : null;
  };
  const nodes = [];
  const walk = (root) => {
    for (const el of root.querySelectorAll('*')) {
      nodes.push(el);
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  walk(document);
  const labelOf = (el) => {
    const labelled = el.getAttribute('aria-labelledby');
    if (labelled) {
      const text = labelled.split(/\s+/).map((id) => document.getElementById(id)?.textContent || '').join(' ');
      if (text.trim()) return compact(text);
    }
    if (el.labels && el.labels.length) return compact([...el.labels].map((x) => x.textContent || '').join(' '));
    return compact(el.getAttribute('aria-label') || el.getAttribute('title'));
  };
  const roleOf = (el) => {
    if (el.getAttribute('role')) return el.getAttribute('role');
    const tag = el.tagName.toLowerCase();
    if (tag === 'a') return 'link';
    if (tag === 'button') return 'button';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'select') return el.multiple ? 'listbox' : 'combobox';
    if (tag === 'input') {
      const type = (el.getAttribute('type') || 'text').toLowerCase();
      if (type === 'checkbox') return 'checkbox';
      if (type === 'radio') return 'radio';
      if (type === 'button' || type === 'submit' || type === 'reset') return 'button';
      return 'textbox';
    }
    return null;
  };
  const controls = [];
  const controlSelector = 'input,textarea,select,button,a,[role],[contenteditable="true"],summary';
  for (const el of nodes.filter((x) => x.matches?.(controlSelector) && visible(x))) {
    if (el.closest('tr,[role="row"]')) continue;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase() || null;
    const section = el.closest('fieldset,section,[role="region"],form');
    const sectionLabel = section
      ? compact(section.getAttribute('aria-label') || section.querySelector('legend,h1,h2,h3,h4,h5,h6')?.textContent)
      : null;
    const label = labelOf(el);
    const accessibleName = label || compact(el.innerText || el.textContent) || compact(el.getAttribute('placeholder'));
    const selectOptions = tag === 'select'
      ? [...el.options].map((o) => ({ label: compact(o.label || o.textContent), disabled: !!o.disabled, selected: !!o.selected }))
      : [];
    const controlled = el.getAttribute('aria-controls');
    const list = controlled ? document.getElementById(controlled) : null;
    const customOptions = list && (list.getAttribute('role') === 'listbox' || list.matches('[role="listbox"]'))
      ? [...list.querySelectorAll('[role="option"]')].filter(visible).map((o) => ({ label: compact(o.getAttribute('aria-label') || o.textContent), disabled: o.getAttribute('aria-disabled') === 'true', selected: o.getAttribute('aria-selected') === 'true' }))
      : [];
    let controlType = tag;
    if (tag === 'input') controlType = type || 'text';
    else if (el.getAttribute('role') === 'switch') controlType = 'switch';
    else if (el.getAttribute('role') === 'tab') controlType = 'tab';
    else if (el.getAttribute('role') === 'combobox') controlType = 'combobox';
    else if (el.getAttribute('contenteditable') === 'true') controlType = 'contenteditable';
    controls.push({
      tag, type: controlType, role: roleOf(el), label, name: accessibleName,
      placeholder: compact(el.getAttribute('placeholder')), input_type: type,
      required: el.required || el.getAttribute('aria-required') === 'true',
      required_evidence: el.required ? 'html_required' : (el.getAttribute('aria-required') === 'true' ? 'aria_required' : null),
      readonly: ('readOnly' in el) ? !!el.readOnly : null, disabled: !!el.disabled,
      section_label: sectionLabel, section_tag: section?.tagName.toLowerCase() || null,
      expanded: el.getAttribute('aria-expanded'), haspopup: el.getAttribute('aria-haspopup'),
      selected: el.getAttribute('aria-selected'), autocomplete: el.getAttribute('aria-autocomplete'),
      option_count: selectOptions.length + customOptions.length,
      options: [...selectOptions, ...customOptions],
      option_source: selectOptions.length ? 'native_select' : (customOptions.length ? 'custom_listbox' : 'none'),
      in_lookup: !!el.getAttribute('aria-autocomplete') || type === 'search' || !!el.closest('[role="grid"],table'),
      selector_index: controls.length
    });
  }
  const sections = [];
  for (const el of nodes.filter((x) => x.matches?.('fieldset,section,[role="region"],main,[role="main"]') && visible(x))) {
    const label = compact(el.getAttribute('aria-label') || el.querySelector('legend,h1,h2,h3,h4,h5,h6')?.textContent);
    sections.push({ tag: el.tagName.toLowerCase(), role: el.getAttribute('role'), label, selector_index: sections.length });
  }
  const headings = nodes.filter((x) => x.matches?.('h1,h2,h3,h4,h5,h6') && visible(x))
    .map((x) => ({ tag: x.tagName.toLowerCase(), label: compact(x.textContent), level: Number(x.tagName.slice(1)) }));
  const navLinks = [...document.querySelectorAll(_NAV_SELECTOR_PLACEHOLDER)].filter(visible).map((el, index) => ({
    label: compact(el.getAttribute('aria-label') || el.textContent),
    href: el.href || null, target: el.target || null, download: el.hasAttribute('download'), index
  }));
  const tables = nodes.filter((x) => x.matches?.('table,[role="grid"],[role="table"]') && visible(x)).map((el, index) => ({
    role: el.getAttribute('role') || 'table',
    headers: [...el.querySelectorAll('th,[role="columnheader"]')].filter(visible).map((x) => compact(x.textContent)).filter(Boolean),
    row_count: el.querySelectorAll('tr,[role="row"]').length,
    index
  }));
  const dialogs = nodes.filter((x) => x.matches?.('[role="dialog"],[role="alertdialog"],dialog[open]') && visible(x))
    .map((x) => compact(x.getAttribute('aria-label') || x.querySelector('h1,h2,h3,h4,[role="heading"]')?.textContent));
  return {
    title: compact(document.title),
    controls, sections, headings, navLinks, tables,
    dialogs: dialogs.filter(Boolean),
    option_elements_visible: [...document.querySelectorAll('[role="option"],option')].filter(visible).length,
    body_scroll_height: document.body?.scrollHeight || 0
  };
}""".replace("_NAV_SELECTOR_PLACEHOLDER", _NAV_SELECTOR)


@dataclass(frozen=True)
class DiscoveryPolicy:
    max_screens: int = 100
    max_interactions: int = 300
    max_navigation_visits: int = 100
    max_navigation_depth: int = 10
    interaction_timeout_ms: int = 1500
    capture_option_labels: bool = True
    live_discovery: bool = False
    environment_label: str = "fixture"


def sanitized_url(url: str) -> str:
    """Remove query, fragment and user-info from any recorded URL."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:14]}"


def _dangerous(label: str | None) -> bool:
    words = set(re.findall(r"[a-z]+", (label or "").casefold()))
    return bool(words & _DANGEROUS_WORDS)


def login_required(page: Page) -> bool:
    """Detect a visible password field without reading any credential field value."""
    try:
        return page.locator(_LOGIN_SELECTOR).count() > 0
    except Exception:
        return False


def _safe_screen(page: Page, policy: DiscoveryPolicy) -> dict[str, Any]:
    url = sanitized_url(page.url)
    raw = page.evaluate(_INSPECT_SCRIPT)
    # A live search/lookup control can expose business records in its options.
    # Keep only its existence/count; fixture discovery may retain labels.
    for control in raw["controls"]:
        if control["in_lookup"] and control["option_count"]:
            control["options"] = []
            control["options_withheld"] = True
        elif not policy.capture_option_labels and control["option_count"]:
            control["options"] = []
            control["options_withheld"] = True
        else:
            control["options_withheld"] = False
    raw["url"] = url
    raw["frame_descriptors"] = []
    return raw


def _fingerprint(raw: dict[str, Any]) -> str:
    stable = {
        "url": raw["url"],
        "title": raw["title"],
        "headings": raw["headings"],
        "sections": raw["sections"],
        "controls": [
            (x["role"], x["type"], x["name"], x["expanded"], x["selected"])
            for x in raw["controls"]
        ],
        "dialogs": raw["dialogs"],
        "tables": raw["tables"],
        "options_visible": raw["option_elements_visible"],
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()[:24]


def _make_screen(raw: dict[str, Any], *, observed_at: str, browser_channel: str) -> UIScreenObservation:
    fingerprint = _fingerprint(raw)
    screen_id = f"screen-{fingerprint}"
    evidence = DiscoveryEvidence(
        kind="dom_metadata",
        observed_at_utc=observed_at,
        screen_url=raw["url"],
        locator_recipe="visible DOM metadata; values and record rows excluded",
        fact="screen structure inspected without reading form values or table-row content",
    )
    sections: list[UISectionObservation] = []
    section_by_label: dict[str, str] = {}
    for section in raw["sections"]:
        key = f"{screen_id}:{section['tag']}:{section['selector_index']}"
        section_id = _id("section", key)
        section_by_label[section.get("label") or ""] = section_id
        sections.append(
            UISectionObservation(
                section_id=section_id,
                label=section.get("label"),
                role=section.get("role") or section.get("tag"),
                locator_recipe=f"{section['tag']} at observed DOM index {section['selector_index']}",
                evidence=[evidence],
            )
        )

    controls: list[UIControlObservation] = []
    for item in raw["controls"]:
        control_id = _id(
            "control",
            f"{screen_id}:{item['role']}:{item['name']}:{item['selector_index']}:{item['type']}",
        )
        options = [
            UIOptionObservation(
                label=option["label"] or "",
                disabled=option["disabled"],
                selected=option["selected"],
            )
            for option in item["options"]
        ]
        if item["option_count"] == 0:
            option_coverage = "not_applicable"
        elif item["options_withheld"]:
            option_coverage = "withheld_for_data_safety"
        elif len(options) < item["option_count"]:
            option_coverage = "partial"
        else:
            option_coverage = "complete"
        controls.append(
            UIControlObservation(
                control_id=control_id,
                role=item["role"],
                control_type=item["type"],
                accessible_name=item["name"],
                label=item["label"],
                placeholder=item["placeholder"],
                input_type=item["input_type"],
                required=item["required"],
                required_evidence=item["required_evidence"],
                readonly=item["readonly"],
                disabled=item["disabled"],
                section_id=section_by_label.get(item["section_label"] or ""),
                locator_recipe=f"role={item['role'] or item['type']}; name={item['name']!r}; observed index={item['selector_index']}",
                options=options,
                observed_option_count=item["option_count"],
                option_coverage=option_coverage,
                evidence=[evidence],
            )
        )

    tables: list[UITableObservation] = []
    for table in raw["tables"]:
        tables.append(
            UITableObservation(
                table_id=_id("table", f"{screen_id}:{table['index']}"),
                role=table["role"],
                headers=table["headers"],
                visible_row_count=table["row_count"],
                locator_recipe=f"{table['role']} at observed DOM index {table['index']}; cell values not read",
                evidence=[evidence],
            )
        )

    relationships: list[UIRelationshipObservation] = []
    for link in raw["navLinks"]:
        href = link.get("href") or ""
        target_path = sanitized_url(href) if href else None
        relationships.append(
            UIRelationshipObservation(
                relationship_type="navigation",
                source_id=screen_id,
                target_path=target_path,
                label=link.get("label"),
                status="observed",
                evidence=[
                    DiscoveryEvidence(
                        kind="navigation_link",
                        observed_at_utc=observed_at,
                        screen_url=raw["url"],
                        locator_recipe=f"{_NAV_SELECTOR} at observed index {link['index']}",
                        fact="visible link observed inside a navigation landmark",
                    )
                ],
            )
        )
    return UIScreenObservation(
        screen_id=screen_id,
        url=raw["url"],
        title=raw["title"],
        fingerprint=fingerprint,
        sections=sections,
        controls=controls,
        tables=tables,
        relationships=relationships,
        dialog_labels=raw["dialogs"],
        evidence=[evidence],
    )


def _same_origin(url_a: str, url_b: str) -> bool:
    a, b = urlsplit(url_a), urlsplit(url_b)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


def _link_block_reason(link: dict[str, Any], current_url: str) -> str | None:
    href = link.get("href") or ""
    if not href or href.startswith(("mailto:", "tel:", "javascript:")) or link.get("download"):
        return "navigation target is not a normal in-page link"
    if not _same_origin(current_url, href):
        return "cross-origin navigation is outside the authorized discovery boundary"
    if link.get("target") not in (None, "", "_self"):
        return "new-window navigation was not activated automatically"
    if urlsplit(href).query:
        return "query-bearing navigation may identify a business record; target was not opened"
    if re.search(r"/(?:\d{3,}|[0-9a-f]{8}-[0-9a-f-]{27,})(?:/|$)", urlsplit(href).path, re.IGNORECASE):
        return "record-like path was not opened"
    if _dangerous(link.get("label")):
        return "navigation label is associated with a business transaction or session exit"
    if any(
        token in urlsplit(href).path.casefold().split("/")
        for token in ("logout", "signout", "delete", "submit", "save", "update", "register", "create", "edit", "approve")
    ):
        return "path resembles a mutating or session-ending action"
    return None


def _interaction_candidates(page: Page, *, policy: DiscoveryPolicy) -> list[dict[str, Any]]:
    return page.evaluate(
        r"""() => {
          const visible = (el) => { const r=el.getBoundingClientRect(); const s=getComputedStyle(el); return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none'; };
          const text = (el) => (el.getAttribute('aria-label') || el.innerText || el.textContent || '').replace(/\s+/g,' ').trim().slice(0,160);
          const result=[];
          const add = (selector, kind, role) => [...document.querySelectorAll(selector)].filter(visible).forEach((el,index)=>result.push({kind,selector,index,name:text(el),role:el.getAttribute('role')||role}));
          add('details:not([open]) > summary','expand','button');
          add('button[aria-expanded="false"],[role="button"][aria-expanded="false"]','expand','button');
          add('[role="tab"]','tab','tab');
          add('[aria-haspopup="listbox"],[role="combobox"]:not(input)','dropdown','button');
          add('button[aria-haspopup="dialog"]','dialog','button');
          return result;
        }"""
    )


def _click_interaction(page: Page, item: dict[str, Any], timeout_ms: int) -> None:
    locator = page.locator(item["selector"]).nth(item["index"])
    locator.click(timeout=timeout_ms)


def _capture_state(
    page: Page,
    *,
    policy: DiscoveryPolicy,
    screens: list[UIScreenObservation],
    fingerprints: set[str],
    issues: list[DiscoveryIssue],
    navigation_links_observed: set[str],
) -> tuple[UIScreenObservation | None, dict[str, Any]]:
    raw = _safe_screen(page, policy)
    screen = _make_screen(raw, observed_at=_utc_now(), browser_channel="msedge" if policy.live_discovery else "fixture")
    for index, link in enumerate(raw["navLinks"]):
        link_key = f"{screen.url}|{link.get('label')}|{sanitized_url(link.get('href') or '')}"
        navigation_links_observed.add(link_key)
        reason = _link_block_reason(link, page.url)
        if reason:
            issues.append(
                DiscoveryIssue(
                    code="navigation_not_activated",
                    status="not_safely_discoverable",
                    summary=reason,
                    source_url=screen.url,
                    evidence=[
                        DiscoveryEvidence(
                            kind="navigation_link",
                            observed_at_utc=_utc_now(),
                            screen_url=screen.url,
                            locator_recipe=f"{_NAV_SELECTOR} at observed index {index}",
                            fact="visible navigation link deliberately not activated",
                        )
                    ],
                )
            )
    if screen.fingerprint in fingerprints:
        return None, raw
    fingerprints.add(screen.fingerprint)
    screens.append(screen)
    return screen, raw


def discover_page(page: Page, *, policy: DiscoveryPolicy | None = None) -> UIDiscoveryResult:
    """Inspect an already-authorized Playwright page using read-only UI actions.

    The caller owns the browser/context and authentication boundary. This method
    never reads form values, cookies, storage, request bodies or table-cell data.
    """
    policy = policy or DiscoveryPolicy()
    started = _utc_now()
    discovery_id = f"discovery-{uuid4().hex[:12]}"
    screens: list[UIScreenObservation] = []
    issues: list[DiscoveryIssue] = []
    fingerprints: set[str] = set()
    visited_hrefs: set[str] = set()
    navigation_links_observed: set[str] = set()
    navigation_links_visited = 0
    safe_interactions = 0
    navigation_stack: list[str] = []
    forbidden_responses: list[str] = []

    def on_response(response: Any) -> None:
        try:
            if response.status == 403:
                forbidden_responses.append(sanitized_url(response.url))
        except Exception:
            return

    page.on("response", on_response)

    while len(screens) < policy.max_screens:
        if policy.live_discovery and forbidden_responses:
            forbidden_url = forbidden_responses[-1]
            issues.append(
                DiscoveryIssue(
                    code="http_forbidden",
                    status="inaccessible",
                    summary="The application returned HTTP 403; live discovery stopped without bypassing access controls.",
                    source_url=forbidden_url,
                    evidence=[
                        DiscoveryEvidence(
                            kind="navigation_link",
                            observed_at_utc=_utc_now(),
                            screen_url=forbidden_url,
                            locator_recipe="HTTP response status",
                            fact=f"HTTP 403; visible message={_safe_error_forbidden(page)}",
                        )
                    ],
                )
            )
            break
        depth = len(navigation_stack)
        if depth > policy.max_navigation_depth:
            issues.append(
                DiscoveryIssue(
                    code="navigation_depth_limit",
                    status="partial",
                    summary="Navigation depth limit reached; remaining links were not visited.",
                    source_url=sanitized_url(page.url),
                )
            )
            if navigation_stack:
                navigation_stack.pop()
                try:
                    page.go_back(timeout=policy.interaction_timeout_ms, wait_until="domcontentloaded")
                except Exception:
                    break
                continue
            break
        if login_required(page):
            issues.append(
                DiscoveryIssue(
                    code="authentication_boundary",
                    status="inaccessible",
                    summary="A visible password field indicates authentication is required; no login content was inspected.",
                    source_url=sanitized_url(page.url),
                )
            )
            if navigation_stack:
                navigation_stack.pop()
                try:
                    page.go_back(timeout=policy.interaction_timeout_ms, wait_until="domcontentloaded")
                except Exception:
                    break
                continue
            break

        try:
            screen, raw = _capture_state(
                page,
                policy=policy,
                screens=screens,
                fingerprints=fingerprints,
                issues=issues,
                navigation_links_observed=navigation_links_observed,
            )
        except Exception as exc:
            issues.append(
                DiscoveryIssue(
                    code="page_inspection_failed",
                    status="inaccessible",
                    summary=f"Page structure could not be inspected ({type(exc).__name__}); page content was not logged.",
                    source_url=sanitized_url(page.url),
                )
            )
            continue
        # Safely expand visible UI affordances once per observed state.
        if screen is not None:
            tried_interactions: set[tuple[str, str, int]] = set()
            while safe_interactions < policy.max_interactions and not (policy.live_discovery and forbidden_responses):
                candidates = _interaction_candidates(page, policy=policy)
                candidate = next(
                    (
                        item for item in candidates
                        if (item["kind"], item["selector"], item["index"]) not in tried_interactions
                        and not _dangerous(item.get("name"))
                    ),
                    None,
                )
                if candidate is None:
                    break
                key = (candidate["kind"], candidate["selector"], candidate["index"])
                tried_interactions.add(key)
                before = page.url
                try:
                    _click_interaction(page, candidate, policy.interaction_timeout_ms)
                    safe_interactions += 1
                    after_screen, _after_raw = _capture_state(
                        page,
                        policy=policy,
                        screens=screens,
                        fingerprints=fingerprints,
                        issues=issues,
                        navigation_links_observed=navigation_links_observed,
                    )
                    if candidate["kind"] in {"dropdown", "dialog"}:
                        page.keyboard.press("Escape")
                    if after_screen is not None:
                        relationship_type = {
                            "expand": "reveals",
                            "tab": "tab_controls",
                            "dialog": "dialog_trigger",
                            "dropdown": "reveals",
                        }[candidate["kind"]]
                        screen.relationships.append(
                            UIRelationshipObservation(
                                relationship_type=relationship_type,
                                source_id=screen.screen_id,
                                target_id=after_screen.screen_id,
                                label=candidate.get("name"),
                                status="observed",
                                evidence=[
                                    DiscoveryEvidence(
                                        kind="safe_interaction",
                                        observed_at_utc=_utc_now(),
                                        screen_url=sanitized_url(before),
                                        locator_recipe=f"{candidate['role']} name={candidate.get('name')!r} at index {candidate['index']}",
                                        fact=f"safe {candidate['kind']} interaction revealed an observed UI state",
                                    )
                                ],
                            )
                        )
                except PlaywrightTimeoutError:
                    issues.append(
                        DiscoveryIssue(
                            code="safe_interaction_timeout",
                            status="partial",
                            summary=f"A safe {candidate['kind']} control did not respond within the configured timeout.",
                            source_url=sanitized_url(before),
                        )
                    )
                except Exception as exc:
                    issues.append(
                        DiscoveryIssue(
                            code="safe_interaction_failed",
                            status="partial",
                            summary=f"A safe {candidate['kind']} interaction failed ({type(exc).__name__}); details were not logged.",
                            source_url=sanitized_url(before),
                        )
                    )

        # Follow only visible same-origin links inside navigation landmarks.
        # Browser history returns to the source page; target URLs are never guessed.
        try:
            links = page.evaluate(
                r"""() => [...document.querySelectorAll('nav a, [role="navigation"] a')].map((el,index)=>({index,href:el.href||'',label:(el.getAttribute('aria-label')||el.textContent||'').replace(/\s+/g,' ').trim().slice(0,160),target:el.target||null,download:el.hasAttribute('download')}))"""
            )
        except Exception:
            links = []
        next_link = None
        current_raw = _safe_screen(page, policy)
        current_fingerprint = _fingerprint(current_raw)
        for link in links:
            key = f"{current_fingerprint}|{link.get('index')}|{link.get('label')}|{sanitized_url(link.get('href') or '')}"
            if key in visited_hrefs:
                continue
            visited_hrefs.add(key)
            reason = _link_block_reason(link, page.url)
            if reason:
                continue
            next_link = link
            break
        if next_link is not None:
            if navigation_links_visited >= policy.max_navigation_visits:
                issues.append(
                    DiscoveryIssue(
                        code="navigation_visit_limit",
                        status="partial",
                        summary="Navigation visit limit reached; additional links were not opened.",
                        source_url=sanitized_url(page.url),
                    )
                )
                break
            previous_url = page.url
            try:
                page.locator(_NAV_SELECTOR).nth(next_link["index"]).click(timeout=policy.interaction_timeout_ms)
                navigation_links_visited += 1
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=policy.interaction_timeout_ms)
                except PlaywrightTimeoutError:
                    pass
                if sanitized_url(page.url) in forbidden_responses:
                    issue_evidence = DiscoveryEvidence(
                        kind="navigation_link",
                        observed_at_utc=_utc_now(),
                        screen_url=sanitized_url(page.url),
                        locator_recipe=f"{_NAV_SELECTOR} at observed index {next_link['index']}",
                        fact=f"HTTP 403; visible message={_safe_error_forbidden(page)}",
                    )
                    issues.append(
                        DiscoveryIssue(
                            code="http_forbidden",
                            status="inaccessible",
                            summary="The application returned HTTP 403; discovery stopped at this page without bypassing access controls.",
                            source_url=sanitized_url(page.url),
                            evidence=[issue_evidence],
                        )
                    )
                    if policy.live_discovery:
                        break
                    page.go_back(timeout=policy.interaction_timeout_ms, wait_until="domcontentloaded")
                    continue
                if login_required(page):
                    issues.append(
                        DiscoveryIssue(
                            code="authentication_boundary",
                            status="inaccessible",
                            summary="A navigation boundary requires authentication; no login content was inspected.",
                            source_url=sanitized_url(page.url),
                        )
                    )
                    page.go_back(timeout=policy.interaction_timeout_ms, wait_until="domcontentloaded")
                    continue
                navigation_stack.append(sanitized_url(previous_url))
                continue
            except PlaywrightTimeoutError:
                issues.append(
                    DiscoveryIssue(
                        code="navigation_timeout",
                        status="inaccessible",
                        summary="A discovered navigation link did not complete within the configured timeout.",
                        source_url=sanitized_url(previous_url),
                    )
                )
            except Exception as exc:
                issues.append(
                    DiscoveryIssue(
                        code="navigation_failed",
                        status="inaccessible",
                        summary=f"A discovered navigation link failed ({type(exc).__name__}); details were not logged.",
                        source_url=sanitized_url(previous_url),
                    )
                )
        elif navigation_stack:
            navigation_stack.pop()
            try:
                page.go_back(timeout=policy.interaction_timeout_ms, wait_until="domcontentloaded")
            except Exception:
                issues.append(
                    DiscoveryIssue(
                        code="navigation_return_failed",
                        status="partial",
                        summary="Could not return through browser history; remaining navigation may be undiscovered.",
                        source_url=sanitized_url(page.url),
                    )
                )
                break
        else:
            break

    if safe_interactions >= policy.max_interactions:
        issues.append(
            DiscoveryIssue(
                code="interaction_limit",
                status="partial",
                summary="Safe interaction limit reached; further UI expansion was not attempted.",
                source_url=sanitized_url(page.url),
            )
        )

    controls = [control for screen in screens for control in screen.controls]
    option_count = sum(control.observed_option_count for control in controls)
    coverage = DiscoveryCoverage(
        screens_observed=len(screens),
        navigation_links_observed=len(navigation_links_observed),
        navigation_links_visited=navigation_links_visited,
        safe_interactions_explored=safe_interactions,
        controls_observed=len(controls),
        options_observed=option_count,
        issues=issues,
    )
    return UIDiscoveryResult(
        discovery_id=discovery_id,
        started_at_utc=started,
        completed_at_utc=_utc_now(),
        live_discovery=policy.live_discovery,
        browser_channel="msedge" if policy.live_discovery else "fixture",
        environment_label=policy.environment_label,
        screens=screens,
        coverage=coverage,
    )


def _safe_error_forbidden(page: Page) -> str:
    """Return only generic visible denial phrases; never dump an error page."""
    try:
        text = page.locator("body").inner_text(timeout=1000).casefold()
    except Exception:
        return "Visible error text unavailable"
    for phrase in ("forbidden", "access denied", "403"):
        if phrase in text:
            return phrase.upper() if phrase == "forbidden" else phrase
    return "Visible error text withheld"


def run_live_onepv_discovery(
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> UIDiscoveryResult | None:
    """Launch isolated, headed Edge and pause for manual authentication if needed."""
    base_url = os.environ.get("ONEPV_BASE_URL")
    if not base_url:
        output_fn("ONEPV_BASE_URL is not set; live discovery was not started.")
        return None
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
        output_fn("ONEPV_BASE_URL is invalid; provide an HTTP(S) development-site URL without embedded credentials.")
        return None
    recorded_url = sanitized_url(base_url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=False)
        context: BrowserContext = browser.new_context()
        page = context.new_page()
        try:
            response = page.goto(base_url, wait_until="domcontentloaded")
            if response is not None and response.status == 403:
                output_fn(
                    f"LIVE DISCOVERY STOPPED: HTTP 403 at {recorded_url}; "
                    f"time={_utc_now()}; visible message={_safe_error_forbidden(page)}. "
                    "No access-control bypass was attempted."
                )
                return None
            if login_required(page):
                output_fn("Authentication required. Enter credentials manually in the visible Edge window.")
                try:
                    confirmation = input_fn("After login completes, type AUTHENTICATED here and press Enter: ")
                except (EOFError, KeyboardInterrupt):
                    output_fn("Manual authentication confirmation was unavailable; live discovery stopped.")
                    return None
                if confirmation.strip() != "AUTHENTICATED":
                    output_fn("Authentication was not confirmed; live discovery stopped.")
                    return None
                if login_required(page):
                    output_fn("The login boundary is still visible; live discovery stopped without inspecting it.")
                    return None
            result = discover_page(
                page,
                policy=DiscoveryPolicy(
                    max_screens=5,
                    max_interactions=5,
                    max_navigation_visits=5,
                    interaction_timeout_ms=1000,
                    live_discovery=True,
                    environment_label="development",
                    capture_option_labels=False,
                ),
            )
            output_fn(
                f"Live discovery complete: {result.coverage.screens_observed} screens, "
                f"{result.coverage.controls_observed} controls, "
                f"{len(result.coverage.issues)} coverage issues."
            )
            return result
        except Exception as exc:
            output_fn(f"Live discovery stopped ({type(exc).__name__}); page details were not logged.")
            return None
        except KeyboardInterrupt:
            output_fn("Live discovery interrupted; the isolated browser session is closing.")
            return None
        finally:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    result = run_live_onepv_discovery()
    if result is None:
        sys.exit(1)
