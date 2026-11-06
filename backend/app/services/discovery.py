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
    UITextObservation,
)


_DANGEROUS_WORDS = {
    "save", "submit", "delete", "update", "edit",
    "approve", "sign", "send", "finalize", "finalise", "remove", "publish",
    "execute", "confirm", "logout", "log out", "sign out",
}
_LOGIN_SELECTOR = 'input[type="password"]:visible'

_OBSERVE_SCRIPT = r"""(optionsPolicy) => {
  const collectOptionLabels = !optionsPolicy || optionsPolicy.captureOptionLabels !== false;
  const iconGlyphs = new Set([
    'keyboard_arrow_left', 'keyboard_arrow_right', 'keyboard_arrow_down', 'keyboard_arrow_up',
    'expand_less', 'expand_more', 'chevron_right', 'chevron_left', 'chevron_down', 'chevron_up',
    'minimize', 'fullscreen', 'fullscreen_exit', 'close', 'menu', 'more_vert', 'more_horiz',
    'search', 'filter_list', 'arrow_back', 'arrow_forward', 'arrow_drop_down', 'arrow_drop_up',
    'account_circle', 'person', 'help', 'info', 'warning', 'error', 'check', 'clear',
    'refresh', 'sync', 'edit', 'delete', 'add', 'remove', 'settings', 'save', 'download',
    'upload', 'file_upload', 'folder', 'folder_open', 'star', 'notifications'
  ]);

  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0' && r.width > 0 && r.height > 0;
  };

  const compact = (value, limit = 160) => {
    if (!value) return null;
    const text = String(value).replace(/\s+/g, ' ').trim();
    if (!text || iconGlyphs.has(text.toLowerCase())) return null;
    return text.slice(0, limit);
  };

  const isIcon = (text) => text && iconGlyphs.has(text.toLowerCase());

  function getCssSelector(el) {
    if (el.id) return `#${el.id}`;
    const path = [];
    while (el && el.nodeType === Node.ELEMENT_NODE) {
      let selector = el.tagName.toLowerCase();
      if (el.id) {
        path.unshift(`#${el.id}`);
        break;
      }
      let sibling = el;
      let nth = 1;
      while (sibling = sibling.previousElementSibling) {
        if (sibling.tagName.toLowerCase() === selector) nth++;
      }
      selector += `:nth-of-type(${nth})`;
      path.unshift(selector);
      el = el.parentElement;
    }
    return path.join(' > ');
  }

  const cleanFieldLabel = (value) => compact(value)?.replace(/[＊*]\s*$/, '').trim() || null;
  const fieldWrapperSelector = 'mat-form-field, .mat-form-field, .mat-mdc-form-field, .form-group, .form-field, .form-item, .field-container';

  const labelOf = (el) => {
    if (el.labels && el.labels.length) {
      const text = compact([...el.labels].map((x) => x.textContent || '').join(' '));
      if (text) return cleanFieldLabel(text);
    }
    const formField = el.closest(fieldWrapperSelector);
    if (formField) {
      const controlsInField = formField.querySelectorAll('input:not([type="hidden"]),textarea,select,mat-select,[role="textbox"],[role="combobox"],[role="checkbox"],[role="radio"],[role="switch"]');
      const matLabel = formField.querySelector('mat-label, label, .mat-mdc-floating-label, .mat-form-field-label, .form-label, .control-label');
      if (controlsInField.length === 1 && matLabel && cleanFieldLabel(matLabel.textContent)) return cleanFieldLabel(matLabel.textContent);
    }
    // Some Angular forms render the caption as a sibling above the control
    // instead of associating it with a native label/ARIA relationship.
    const controlRect = el.getBoundingClientRect();
    const nearby = [...document.querySelectorAll('label, mat-label, .form-label, .control-label, .mat-mdc-floating-label, .mat-form-field-label')]
      .filter((candidate) => candidate !== el && visible(candidate))
      .map((candidate) => {
        const rect = candidate.getBoundingClientRect();
        const text = cleanFieldLabel(candidate.innerText || candidate.textContent);
        const overlaps = Math.min(rect.right, controlRect.right) - Math.max(rect.left, controlRect.left) > 0;
        const gap = controlRect.top - rect.bottom;
        const labelWrapper = candidate.closest(fieldWrapperSelector);
        const controlWrapper = el.closest(fieldWrapperSelector);
        const wrapperMatches = labelWrapper ? labelWrapper === controlWrapper : !controlWrapper;
        return { text, overlaps, gap, wrapperMatches };
      })
      .filter((candidate) => candidate.text && candidate.overlaps && candidate.wrapperMatches && candidate.gap >= -2 && candidate.gap <= 48)
      .sort((a, b) => a.gap - b.gap);
    if (nearby.length && (nearby.length === 1 || nearby[0].gap < nearby[1].gap)) return nearby[0].text;
    const labelled = el.getAttribute('aria-labelledby');
    if (labelled) {
      const text = labelled.split(/\s+/).map((id) => document.getElementById(id)?.textContent || '').join(' ');
      if (cleanFieldLabel(text)) return cleanFieldLabel(text);
    }
    const direct = compact(el.getAttribute('aria-label') || el.getAttribute('title'));
    if (direct) return cleanFieldLabel(direct);
    return null;
  };

  const roleOf = (el) => {
    if (el.getAttribute('role')) return el.getAttribute('role');
    const tag = el.tagName.toLowerCase();
    if (tag === 'a') return 'link';
    if (tag === 'button') return 'button';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'select' || tag === 'mat-select') return el.multiple ? 'listbox' : 'combobox';
    if (tag === 'input') {
      const type = (el.getAttribute('type') || 'text').toLowerCase();
      if (type === 'checkbox') return 'checkbox';
      if (type === 'radio') return 'radio';
      if (type === 'button' || type === 'submit' || type === 'reset') return 'button';
      return 'textbox';
    }
    return null;
  };

  // 1. Identify Sections
  const sectionNodes = [];
  const sectionSelector = 'fieldset,section,[role="region"],main,[role="main"],mat-card,.mat-mdc-card,mat-expansion-panel';
  const sectionTitle = (el) => {
    const aria = compact(el.getAttribute('aria-label'));
    if (aria) return aria;
    if (el.matches('mat-expansion-panel')) {
      const title = el.querySelector(':scope > mat-expansion-panel-header mat-panel-title, :scope > mat-expansion-panel-header [role="heading"]');
      if (title && compact(title.textContent)) return compact(title.textContent);
    }
    const title = el.querySelector('legend,mat-card-title,.mat-mdc-card-title,h1,h2,h3,h4,h5,h6');
    return compact(title?.textContent);
  };
  for (const el of document.querySelectorAll(sectionSelector)) {
    if (!visible(el)) continue;
    const label = sectionTitle(el);
    sectionNodes.push({ el, tag: el.tagName.toLowerCase(), role: el.getAttribute('role'), label, selector_index: sectionNodes.length });
  }

  // 2. Identify Controls (Form Fields & Buttons)
  const controls = [];
  const controlSelector = 'input:not([type="hidden"]),textarea,select,button,a[href],[role="button"],[role="link"],[role="textbox"],[role="combobox"],[role="checkbox"],[role="radio"],[role="switch"],[role="tab"],[contenteditable="true"],summary,mat-select';
  for (const el of document.querySelectorAll(controlSelector)) {
    if (!visible(el)) continue;
    if (el.closest('tr,[role="row"]')) continue;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase() || null;

    // Find enclosing section
    const section = el.closest(sectionSelector);
    const sectionAncestors = [];
    for (let ancestor = el.parentElement; ancestor; ancestor = ancestor.parentElement) {
      if (!ancestor.matches('main,[role="main"]') && sectionNodes.some((entry) => entry.el === ancestor && entry.label)) sectionAncestors.push(ancestor);
    }
    sectionAncestors.reverse();
    const sectionPath = sectionAncestors.map((ancestor) => sectionNodes.find((entry) => entry.el === ancestor).label);
    const sectionLabel = section ? sectionTitle(section) : null;
    const label = labelOf(el);
    const isValueBearingControl = ['input', 'textarea', 'select', 'mat-select'].includes(tag)
      || el.getAttribute('contenteditable') === 'true'
      || ['combobox', 'listbox', 'textbox'].includes(el.getAttribute('role'));
    // Never use a form control's rendered text as its name: custom comboboxes,
    // selects and contenteditables may display the current user-entered value.
    const accessibleName = label
      || (isValueBearingControl ? null : compact(el.innerText || el.textContent))
      || compact(el.getAttribute('placeholder'));

    // Options for selects / comboboxes
    const selectOptions = tag === 'select'
      ? [...el.options].map((o) => ({ label: collectOptionLabels ? compact(o.label || o.textContent) : null, disabled: !!o.disabled, selected: collectOptionLabels && !!o.selected }))
      : [];
    const controlled = el.getAttribute('aria-controls');
    const list = controlled ? document.getElementById(controlled) : null;
    let customOptions = list && (list.getAttribute('role') === 'listbox' || list.matches('[role="listbox"]'))
      ? [...list.querySelectorAll('[role="option"]')].filter(visible).map((o) => ({ label: collectOptionLabels ? compact(o.getAttribute('aria-label') || o.textContent) : null, disabled: o.getAttribute('aria-disabled') === 'true', selected: collectOptionLabels && o.getAttribute('aria-selected') === 'true' }))
      : [];
    if (!selectOptions.length && !customOptions.length && (tag === 'mat-select' || el.getAttribute('role') === 'combobox')) {
      const overlayOptions = [...document.querySelectorAll('.cdk-overlay-container [role="option"], .cdk-overlay-container mat-option')]
        .filter(visible)
        .map((o) => ({
          label: collectOptionLabels ? compact(o.getAttribute('aria-label') || o.textContent) : null,
          disabled: o.getAttribute('aria-disabled') === 'true' || o.hasAttribute('disabled'),
          selected: collectOptionLabels && o.getAttribute('aria-selected') === 'true'
        }));
      if (overlayOptions.length) {
        customOptions = overlayOptions;
      }
    }

    let controlType = tag;
    if (tag === 'input') controlType = type || 'text';
    else if (el.getAttribute('role') === 'switch') controlType = 'switch';
    else if (el.getAttribute('role') === 'tab') controlType = 'tab';
    else if (el.getAttribute('role') === 'combobox' || tag === 'mat-select') controlType = 'combobox';
    else if (el.getAttribute('contenteditable') === 'true') controlType = 'contenteditable';

    // Discard pure decorative icons registered as controls
    if (tag === 'mat-icon' || isIcon(accessibleName)) continue;

    controls.push({
      tag, type: controlType, role: roleOf(el), label, name: accessibleName,
      is_form_field: isValueBearingControl && !el.closest('mat-paginator, [class*="paginator"]'),
      placeholder: compact(el.getAttribute('placeholder')), input_type: type,
      required: el.required || el.getAttribute('aria-required') === 'true',
      required_evidence: el.required ? 'html_required' : (el.getAttribute('aria-required') === 'true' ? 'aria_required' : null),
      readonly: ('readOnly' in el) ? !!el.readOnly : null, disabled: !!el.disabled,
      section_label: sectionLabel, section_path: sectionPath,
      section_indices: sectionAncestors.map((ancestor) => sectionNodes.find((entry) => entry.el === ancestor).selector_index),
      section_tag: section?.tagName.toLowerCase() || null,
      expanded: el.getAttribute('aria-expanded'), haspopup: el.getAttribute('aria-haspopup'),
      selected: collectOptionLabels ? el.getAttribute('aria-selected') : null, autocomplete: el.getAttribute('aria-autocomplete'),
      option_count: selectOptions.length + customOptions.length,
      options: [...selectOptions, ...customOptions],
      option_source: selectOptions.length ? 'native_select' : (customOptions.length ? 'custom_listbox' : 'none'),
      in_lookup: !!el.getAttribute('aria-autocomplete') || type === 'search' || !!el.closest('[role="grid"],table'),
      selector_index: controls.length
    });
  }

  // 3. Meaningful Visible Text (Headings, Descriptions, Hints, Messages)
  const texts = [];
  const textSelector = 'h1,h2,h3,h4,h5,h6,[role="heading"],p,.description,.help-text,mat-hint,.hint,mat-error,.error,[role="alert"]';
  for (const el of document.querySelectorAll(textSelector)) {
    if (!visible(el)) continue;
    if (el.closest('table,[role="row"],[contenteditable="true"],[role="textbox"]')) continue;
    const text = compact(el.innerText || el.textContent);
    if (!text || isIcon(text)) continue;
    const tag = el.tagName.toLowerCase();
    const section = el.closest(sectionSelector);
    const sectionLabel = section
      ? compact(section.getAttribute('aria-label') || section.querySelector('legend,mat-card-title,.mat-mdc-card-title,mat-panel-title,h1,h2,h3,h4,h5,h6')?.textContent)
      : null;
    let kind = 'paragraph';
    if (/^h[1-6]$/.test(tag) || el.getAttribute('role') === 'heading') kind = 'heading';
    else if (el.matches('mat-hint, .hint, .help-text, .description')) kind = 'hint';
    else if (el.matches('mat-error, .error, [role="alert"]')) kind = 'validation_message';
    texts.push({
      text,
      kind,
      tag,
      section_label: sectionLabel,
      locator_recipe: getCssSelector(el)
    });
  }

  // 4. Observation-Driven State-Aware Navigation & Expandable Groups
  const navItems = [];
  const expandableGroups = [];
  const groupElements = new Set();
  const seenNav = new Set();
  const seenGroups = new Set();

  const isExpansionIcon = (str) => {
    if (!str) return null;
    const s = str.toLowerCase().trim();
    if (['expand_less', 'chevron_up', 'keyboard_arrow_up', 'arrow_drop_up'].includes(s)) return 'expanded';
    if (['expand_more', 'chevron_down', 'keyboard_arrow_down', 'arrow_drop_down', 'chevron_right', 'keyboard_arrow_right'].includes(s)) return 'collapsed';
    return null;
  };

  // Find top-level navigation container roots
  const containerRoots = [];
  const candidateRoots = document.querySelectorAll('nav, aside, app-sidebar, [role="navigation"], [class*="sidebar"], [class*="side-nav"], [class*="menu"]');
  for (const root of candidateRoots) {
    if (!visible(root)) continue;
    let isNested = false;
    let p = root.parentElement;
    while (p) {
      if ([...candidateRoots].includes(p)) { isNested = true; break; }
      p = p.parentElement;
    }
    if (!isNested) containerRoots.push(root);
  }

  for (const root of containerRoots) {
    for (const el of root.querySelectorAll('*')) {
      if (!visible(el)) continue;
      if (el.tagName.toLowerCase() === 'mat-icon' || el.classList.contains('material-icons')) continue;

      // Skip elements that are nested inside an already classified expandable group header
      let insideGroup = false;
      for (const g of groupElements) {
        if (g.contains(el)) { insideGroup = true; break; }
      }
      if (insideGroup) continue;

      const s = getComputedStyle(el);
      const isClickable = (
        el.tagName.toLowerCase() === 'a' ||
        el.tagName.toLowerCase() === 'button' ||
        el.tagName.toLowerCase() === 'summary' ||
        el.getAttribute('role') === 'menuitem' ||
        el.getAttribute('role') === 'link' ||
        s.cursor === 'pointer' ||
        el.classList.contains('hoverBox') ||
        el.hasAttribute('routerlink') ||
        el.hasAttribute('aria-expanded')
      );
      if (!isClickable) continue;

      // Menu semantics can live on a wrapper while visible text is nested.
      const menuTrigger = el.closest('[aria-haspopup="menu"], [aria-haspopup="true"], .hoverBox');
      const hasPopup = menuTrigger?.getAttribute('aria-haspopup') || el.getAttribute('aria-haspopup');
      const isMenuTrigger = !!menuTrigger && (hasPopup === 'menu' || hasPopup === 'true' || menuTrigger.classList.contains('hoverBox'));
      const navigationOwner = isMenuTrigger ? menuTrigger : el;

      // Extract clean text excluding icons from the navigation owner.
      const clone = navigationOwner.cloneNode(true);
      clone.querySelectorAll('mat-icon, .material-icons, svg').forEach(i => i.remove());
      const text = compact(clone.innerText || clone.textContent);
      if (!text || isIcon(text)) continue;

      // Generic State-Aware Expandable Group / Accordion Detection
      let expansionFromIcon = null;
      for (const iconEl of el.querySelectorAll('mat-icon, .material-icons, i, span')) {
        const iconState = isExpansionIcon(iconEl.textContent || iconEl.className);
        if (iconState) { expansionFromIcon = iconState; break; }
      }

      const ariaExpanded = el.getAttribute('aria-expanded');
      const itemContainer = el.closest('.menu-item, li, mat-expansion-panel, details, [class*="item"]') || el.parentElement;
      const siblingSubItems = itemContainer
        ? [...itemContainer.querySelectorAll('a, button, [role="menuitem"], .hoverBox, [class*="sub-menu"], [style*="cursor: pointer"]')].filter(c => c !== el && !el.contains(c))
        : [];
      const hasVisibleChildren = siblingSubItems.some(c => visible(c));
      const hasSubItemsInDOM = siblingSubItems.length > 0;

      const isAccordionTag = navigationOwner.tagName.toLowerCase() === 'summary' || navigationOwner.matches?.('mat-expansion-panel-header, .mat-expansion-panel-header');
      const isParentContainer = navigationOwner.classList.contains('parent') || navigationOwner.closest('.parent') !== null;
      const isGroupHeader = isAccordionTag || (!isMenuTrigger && (expansionFromIcon !== null || ariaExpanded !== null || (hasSubItemsInDOM && isParentContainer)));

      if (isGroupHeader) {
        groupElements.add(el);
        let isExpanded = null;
        if (ariaExpanded === 'true') isExpanded = true;
        else if (ariaExpanded === 'false') isExpanded = false;
        else if (expansionFromIcon === 'expanded') isExpanded = true;
        else if (expansionFromIcon === 'collapsed') isExpanded = false;
        else if (hasVisibleChildren) isExpanded = true;
        else if (hasSubItemsInDOM && !hasVisibleChildren) isExpanded = false;

        if (!seenGroups.has(text)) {
          seenGroups.add(text);
          expandableGroups.push({
            label: text,
            kind: 'expandable_group',
            is_expanded: isExpanded,
            children_count: siblingSubItems.length,
            visible_children_count: siblingSubItems.filter(c => visible(c)).length,
            selector: getCssSelector(el),
            tag: el.tagName.toLowerCase(),
          });
        }
        continue;
      }

      // If el contains direct clickable children with distinct text, it's a wrapper, not a leaf
      let hasChildClickablesWithDiffText = false;
      let hasSameTextLinkChild = false;
      const directChildren = el.querySelectorAll('a, button, [role="menuitem"], .hoverBox, [style*="cursor: pointer"]');
      for (const child of directChildren) {
        if (child === el) continue;
        const cClone = child.cloneNode(true);
        cClone.querySelectorAll('mat-icon, .material-icons, svg').forEach(i => i.remove());
        const cText = compact(cClone.innerText || cClone.textContent);
        if (cText && cText !== text) {
          hasChildClickablesWithDiffText = true;
          break;
        }
        if (cText === text && child.matches('a[href], [role="link"]')) hasSameTextLinkChild = true;
      }
      if (hasChildClickablesWithDiffText || (hasSameTextLinkChild && !isMenuTrigger)) continue;

      const navKey = `${text}|${navigationOwner.href || ''}|${getCssSelector(navigationOwner)}`;
      if (!seenNav.has(navKey)) {
        seenNav.add(navKey);
        navItems.push({
          label: text,
          kind: 'leaf_navigation',
          tag: navigationOwner.tagName.toLowerCase(),
          href: navigationOwner.href || null,
          target: navigationOwner.target || null,
          download: navigationOwner.hasAttribute('download'),
          selector: getCssSelector(navigationOwner),
          menu_trigger: isMenuTrigger,
          navigation_landmark: true,
          index: navItems.length
        });
      }
    }
  }

  // Also include standard links across document
  for (const el of document.querySelectorAll('a[href]:not([download])')) {
    if (!visible(el)) continue;
    const text = compact(el.innerText || el.textContent || el.getAttribute('aria-label'));
    const navKey = `${text}|${el.href || ''}|${getCssSelector(el)}`;
    if (text && !seenNav.has(navKey) && !isIcon(text)) {
      seenNav.add(navKey);
      navItems.push({
        label: text,
        tag: 'a',
        href: el.href || null,
        target: el.target || null,
        download: el.hasAttribute('download'),
        selector: getCssSelector(el),
        navigation_landmark: false,
        index: navItems.length
      });
    }
  }

  // Headings
  const headings = document.querySelectorAll('h1,h2,h3,h4,h5,h6');
  const headingList = [...headings].filter(visible).map(h => ({
    tag: h.tagName.toLowerCase(),
    label: compact(h.textContent),
    level: Number(h.tagName.slice(1))
  })).filter(h => h.label);

  const tables = [...document.querySelectorAll('table,[role="grid"],[role="table"]')].filter(visible).map((el, index) => ({
    role: el.getAttribute('role') || 'table',
    headers: [...el.querySelectorAll('th,[role="columnheader"]')].filter(visible).map((x) => compact(x.textContent)).filter(Boolean),
    row_count: el.querySelectorAll('tr,[role="row"]').length,
    index
  }));

  const dialogs = [...document.querySelectorAll('[role="dialog"],[role="alertdialog"],dialog[open]')].filter(visible)
    .map((x) => compact(x.getAttribute('aria-label') || x.querySelector('h1,h2,h3,h4,[role="heading"]')?.textContent));

  return {
    title: compact(document.title),
    sections: sectionNodes.map(s => ({ tag: s.tag, role: s.role, label: s.label, selector_index: s.selector_index })),
    controls,
    texts,
    headings: headingList,
    navLinks: navItems,
    expandableGroups: expandableGroups,
    tables,
    dialogs: dialogs.filter(Boolean),
    unvisited_tabs: [...document.querySelectorAll('[role="tab"][aria-selected="false"]')].filter(visible).length,
    collapsed_panels: [...document.querySelectorAll('mat-expansion-panel:not(.mat-expanded), details:not([open])')].filter(visible).length,
    virtual_scrolls: [...document.querySelectorAll('cdk-virtual-scroll-viewport, [class*="virtual-scroll"]')].filter(visible).length,
    option_elements_visible: [...document.querySelectorAll('[role="option"], option')].filter(visible).length,
    body_scroll_height: document.body?.scrollHeight || 0
  };
}"""


@dataclass(frozen=True)
class DiscoveryPolicy:
    max_screens: int = 100
    max_interactions: int = 300
    max_navigation_visits: int = 100
    max_navigation_depth: int = 10
    interaction_timeout_ms: int = 1500
    capture_option_labels: bool = True
    inspect_dropdown_options: bool = False
    live_discovery: bool = False
    environment_label: str = "fixture"
    allowed_navigation_labels: tuple[str, ...] | None = None
    workflow_scope: str | None = None


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


def _normalized_label(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").casefold()).strip()


def _workflow_label_matches(label: str | None, workflow_scope: str) -> bool:
    observed = _normalized_label(label)
    requested = _normalized_label(workflow_scope)
    return bool(observed and requested and (observed == requested or observed in requested or requested in observed))


def login_required(page: Page) -> bool:
    """Detect a visible password field without reading any credential field value."""
    try:
        return page.locator(_LOGIN_SELECTOR).count() > 0
    except Exception:
        return False


def _wait_for_angular_idle(page: Page, timeout_ms: int = 5000) -> bool:
    """Wait for all visible Angular spinners/progress indicators and aria-busy states to settle."""
    spinner_selector = (
        'mat-spinner, mat-progress-spinner, mat-progress-bar, '
        '[role="progressbar"], [aria-busy="true"], '
        '.mat-mdc-progress-spinner, .mat-progress-spinner'
    )
    script = r"""(sel) => {
        const visible = (el) => {
            const s = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
        };
        const elements = document.querySelectorAll(sel);
        for (const el of elements) {
            if (visible(el)) return true;
        }
        return false;
    }"""
    try:
        is_active = page.evaluate(script, spinner_selector)
        if not is_active:
            return True
        page.wait_for_function(
            r"""(sel) => {
                const visible = (el) => {
                    const s = getComputedStyle(el);
                    const r = el.getBoundingClientRect();
                    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
                };
                const elements = document.querySelectorAll(sel);
                for (const el of elements) {
                    if (visible(el)) return false;
                }
                return true;
            }""",
            arg=spinner_selector,
            timeout=timeout_ms,
        )
        return True
    except PlaywrightTimeoutError:
        return False
    except Exception:
        return True


def _safe_screen(page: Page, policy: DiscoveryPolicy) -> dict[str, Any]:
    url = sanitized_url(page.url)
    raw = page.evaluate(_OBSERVE_SCRIPT, {"captureOptionLabels": policy.capture_option_labels})
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
            (x["role"], x["type"], x["name"], x["section_label"], x["expanded"], x["selected"])
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
    section_by_index: dict[int, str] = {}
    section_by_label: dict[str, str] = {}
    for section in raw["sections"]:
        key = f"{screen_id}:{section['tag']}:{section['selector_index']}"
        section_id = _id("section", key)
        section_by_index[section["selector_index"]] = section_id
        if section.get("label"):
            section_by_label.setdefault(section["label"], section_id)
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
    form_fields: list[UIControlObservation] = []
    for item in raw["controls"]:
        control_id = _id(
            "control",
            f"{screen_id}:{item['section_label']}:{item['role']}:{item['name']}:{item['selector_index']}:{item['type']}",
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
        control = UIControlObservation(
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
                section_id=section_by_index.get((item.get("section_indices") or [None])[-1]),
                label_match_status="associated" if item.get("label") else "missing",
                section_path=item.get("section_path") or [],
                locator_recipe=(
                    f"candidate: label={item['label']!r}; section_path={item.get('section_path') or []!r}; validate uniqueness before use"
                    if item.get("label") else
                    f"unresolved form field: role={item['role'] or item['type']}; no associated visible label"
                ),
                options=options,
                observed_option_count=item["option_count"],
                option_coverage=option_coverage,
                evidence=[evidence],
            )
        controls.append(control)
        if item.get("is_form_field"):
            form_fields.append(control)

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
                        locator_recipe=link.get("selector") or f"observed nav link {link['index']}",
                        fact="visible link observed inside a navigation landmark",
                    )
                ],
            )
        )

    texts: list[UITextObservation] = []
    for t in raw.get("texts", []):
        texts.append(
            UITextObservation(
                text=t["text"],
                kind=t["kind"],
                tag=t["tag"],
                section_id=section_by_label.get(t.get("section_label") or ""),
                locator_recipe=t.get("locator_recipe") or t["tag"],
            )
        )

    return UIScreenObservation(
        screen_id=screen_id,
        url=raw["url"],
        title=raw["title"],
        fingerprint=fingerprint,
        sections=sections,
        controls=controls,
        form_fields=form_fields,
        tables=tables,
        relationships=relationships,
        dialog_labels=raw["dialogs"],
        texts=texts,
        evidence=[evidence],
    )


def _same_origin(url_a: str, url_b: str) -> bool:
    a, b = urlsplit(url_a), urlsplit(url_b)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


def _link_block_reason(link: dict[str, Any], current_url: str, policy: DiscoveryPolicy | None = None) -> str | None:
    href = link.get("href") or ""
    label = link.get("label") or ""

    if href:
        target_norm = sanitized_url(href).rstrip("/")
        curr_norm = sanitized_url(current_url).rstrip("/")
        if target_norm == curr_norm:
            return "navigation target is the current page"
        if not _same_origin(current_url, href):
            return "cross-origin navigation is outside the authorized discovery boundary"
        if href.startswith(("mailto:", "tel:", "javascript:")) or link.get("download"):
            return "navigation target is not a normal in-page link"
        if link.get("target") not in (None, "", "_self"):
            return "new-window navigation was not activated automatically"
        if urlsplit(href).query:
            return "query-bearing navigation may identify a business record; target was not opened"
        if re.search(r"/(?:\d{3,}|[0-9a-f]{8}-[0-9a-f-]{27,})(?:/|$)", urlsplit(href).path, re.IGNORECASE):
            return "record-like path was not opened"
        if any(
            token in urlsplit(href).path.casefold().split("/")
            for token in ("logout", "signout", "delete", "submit", "save", "update", "register", "create", "edit", "approve")
        ):
            return "path resembles a mutating or session-ending action"
    else:
        if not label.strip():
            return "navigation target lacks accessible label"
        if label.casefold() in ("home", "dashboard") and current_url.rstrip("/").endswith(("/dashboard", "/home")):
            return "navigation target is the current page"

    if _dangerous(label):
        return "navigation label is associated with a business transaction or session exit"

    if policy and policy.allowed_navigation_labels is not None:
        norm_label = label.casefold().strip()
        allowed = any(
            norm_label == allowed_item.casefold() or norm_label.startswith(allowed_item.casefold())
            for allowed_item in policy.allowed_navigation_labels
        )
        if not allowed:
            return "navigation label not in the configured allowlist for this discovery session"

    return None


def _interaction_candidates(page: Page, *, policy: DiscoveryPolicy) -> list[dict[str, Any]]:
    candidates = page.evaluate(
        r"""() => {
          const visible = (el) => { const r=el.getBoundingClientRect(); const s=getComputedStyle(el); return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none'; };
          const text = (el) => (el.getAttribute('aria-label') || el.innerText || el.textContent || '').replace(/\s+/g,' ').trim().slice(0,160);
          const result=[];
          const add = (selector, kind, role) => [...document.querySelectorAll(selector)].filter(visible).forEach((el,index)=>result.push({kind,selector,index,name:text(el),role:el.getAttribute('role')||role,in_navigation:!!el.closest('nav,aside,app-sidebar,[role="navigation"],[class*="sidebar"],[class*="side-nav"]')}));
          add('details:not([open]) > summary','expand','button');
          add('button[aria-expanded="false"],[role="button"][aria-expanded="false"]','expand','button');
          add('mat-expansion-panel:not(.mat-expanded) mat-expansion-panel-header','expand','button');
          add('.mat-expansion-panel-header[aria-expanded="false"]','expand','button');
          add('[role="tab"]','tab','tab');
          add('mat-select:not([disabled])','dropdown','combobox');
          add('[aria-haspopup="listbox"],[role="combobox"]:not(input)','dropdown','button');
          add('[aria-haspopup="menu"],[aria-haspopup="true"],.hoverBox','menu','button');
          add('button[aria-haspopup="dialog"]','dialog','button');
          return result;
        }"""
    )
    if not policy.inspect_dropdown_options:
        candidates = [candidate for candidate in candidates if candidate["kind"] != "dropdown"]
    return candidates


def _click_interaction(page: Page, item: dict[str, Any], timeout_ms: int) -> None:
    locator = page.locator(item["selector"]).nth(item["index"])
    locator.click(timeout=timeout_ms)


def _expand_closed_containers(
    page: Page,
    timeout_ms: int,
    raw: dict[str, Any] | None = None,
    *,
    expand_navigation_groups: bool = True,
    expand_page_sections: bool = True,
) -> None:
    """Ensure accordions/details are expanded so navigation and form elements are visible."""
    # State-aware expansion: only expand groups that are explicitly collapsed
    if expand_navigation_groups and raw and "expandableGroups" in raw:
        for group in raw["expandableGroups"]:
            if group.get("is_expanded") is False:
                sel = group.get("selector")
                if sel:
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0:
                            loc.click(timeout=timeout_ms)
                            _wait_for_angular_idle(page, timeout_ms=timeout_ms)
                    except Exception:
                        pass
            # If is_expanded is True: ALREADY EXPANDED, DO NOT CLICK TO COLLAPSE!
            # If is_expanded is None: AMBIGUOUS, PRESERVE AND DO NOT BLINDLY CLICK!

    if not expand_page_sections:
        return
    expand_selector = 'details:not([open]) > summary, mat-expansion-panel:not(.mat-expanded) mat-expansion-panel-header, .mat-expansion-panel-header[aria-expanded="false"]'
    try:
        count = page.locator(expand_selector).count()
        for i in range(min(count, 10)):
            try:
                page.locator(expand_selector).nth(i).click(timeout=timeout_ms)
            except Exception:
                pass
    except Exception:
        pass


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
        link_key = f"{screen.url}|{link.get('label')}|{sanitized_url(link.get('href') or '')}|{link.get('selector')}"
        navigation_links_observed.add(link_key)
        reason = _link_block_reason(link, page.url, policy=policy)
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
                            locator_recipe=link.get("selector") or f"observed nav link {link['index']}",
                            fact="visible navigation link deliberately not activated",
                        )
                    ],
                )
            )
    # Record expandable groups in relationships and flag ambiguous groups
    for group in raw.get("expandableGroups", []):
        if screen:
            screen.relationships.append(
                UIRelationshipObservation(
                    relationship_type="reveals",
                    source_id=screen.screen_id,
                    target_id=None,
                    label=group.get("label"),
                    status="observed",
                    evidence=[
                        DiscoveryEvidence(
                            kind="dom_metadata",
                            observed_at_utc=_utc_now(),
                            screen_url=screen.url,
                            locator_recipe=group.get("selector") or "expandable group",
                            fact=f"expandable group observed; is_expanded={group.get('is_expanded')}; children={group.get('children_count')}",
                        )
                    ],
                )
            )
        if group.get("is_expanded") is None:
            issues.append(
                DiscoveryIssue(
                    code="ambiguous_expandable_group",
                    status="partial",
                    summary=f"Expandable group '{group.get('label')}' has ambiguous expansion state; was not clicked automatically.",
                    source_url=screen.url if screen else sanitized_url(page.url),
                )
            )

    # Check for unexpanded/lazy affordances
    lazy_reasons = []
    if raw.get("unvisited_tabs"):
        lazy_reasons.append(f"{raw['unvisited_tabs']} unvisited tabs")
    if raw.get("collapsed_panels"):
        lazy_reasons.append(f"{raw['collapsed_panels']} collapsed sections")
    if raw.get("virtual_scrolls"):
        lazy_reasons.append(f"{raw['virtual_scrolls']} virtual scroll viewports")
    if lazy_reasons:
        issues.append(
            DiscoveryIssue(
                code="lazy_content_detected",
                status="partial",
                summary=f"Screen contains potentially unexpanded content ({', '.join(lazy_reasons)}); inventory may be partial.",
                source_url=screen.url,
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
    workflow_match_status = "not_requested" if not policy.workflow_scope else "not_found"
    workflow_root_depth: int | None = None

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

        # Check loading indicators readiness
        idle = _wait_for_angular_idle(page, timeout_ms=policy.interaction_timeout_ms)
        if not idle:
            issues.append(
                DiscoveryIssue(
                    code="page_loading_timeout",
                    status="partial",
                    summary="Angular loading indicator remained active after timeout; page readiness could not be verified.",
                    source_url=sanitized_url(page.url),
                )
            )

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

        if policy.workflow_scope and workflow_match_status == "not_found":
            observed_screen_labels = [raw.get("title")]
            observed_screen_labels.extend(item.get("label") for item in raw.get("headings", []))
            observed_screen_labels.append(
                urlsplit(page.url).path.replace("/", " ").replace("-", " ").replace("_", " ")
            )
            if any(_workflow_label_matches(label, policy.workflow_scope) for label in observed_screen_labels):
                workflow_match_status = "reached"
                workflow_root_depth = len(navigation_stack)

        # Safely expand visible UI affordances
        tried_interactions: set[tuple[str, str, int]] = set()
        while safe_interactions < policy.max_interactions and not (policy.live_discovery and forbidden_responses):
            candidates = _interaction_candidates(page, policy=policy)
            candidate = next(
                (
                    item for item in candidates
                    if (item["kind"], item["selector"], item["index"]) not in tried_interactions
                    and not _dangerous(item.get("name"))
                    and (
                        not policy.workflow_scope
                        or item["kind"] != "menu"
                        or (
                            workflow_match_status != "reached"
                            and _workflow_label_matches(item.get("name"), policy.workflow_scope)
                        )
                        or (workflow_match_status == "reached" and not item.get("in_navigation"))
                    )
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
                if (
                    policy.workflow_scope
                    and candidate["kind"] == "menu"
                    and _workflow_label_matches(candidate.get("name"), policy.workflow_scope)
                    and sanitized_url(page.url) != sanitized_url(before)
                ):
                    workflow_match_status = "reached"
                    workflow_root_depth = len(navigation_stack)
                _wait_for_angular_idle(page, timeout_ms=policy.interaction_timeout_ms)
                after_screen, _after_raw = _capture_state(
                    page,
                    policy=policy,
                    screens=screens,
                    fingerprints=fingerprints,
                    issues=issues,
                    navigation_links_observed=navigation_links_observed,
                )
                if policy.workflow_scope and _after_raw:
                    observed_labels = [_after_raw.get("title")]
                    observed_labels.extend(item.get("label") for item in _after_raw.get("headings", []))
                    observed_labels.append(
                        urlsplit(page.url).path.replace("/", " ").replace("-", " ").replace("_", " ")
                    )
                    if any(_workflow_label_matches(label, policy.workflow_scope) for label in observed_labels):
                        workflow_match_status = "reached"
                        workflow_root_depth = len(navigation_stack)
                if candidate["kind"] in {"dropdown", "dialog"}:
                    page.keyboard.press("Escape")
                    if candidate["kind"] == "dialog":
                        try:
                            page.evaluate("() => { for (const d of document.querySelectorAll('dialog')) { if (d.open) try { d.close(); } catch(e){} } }")
                        except Exception:
                            pass
                if screen is not None and after_screen is not None:
                    relationship_type = {
                        "expand": "reveals",
                        "tab": "tab_controls",
                        "menu": "reveals",
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

        # Safe interactions may reveal flyouts outside the original nav subtree.
        # Refresh the observation before choosing a workflow route.
        try:
            _current_screen, raw = _capture_state(
                page,
                policy=policy,
                screens=screens,
                fingerprints=fingerprints,
                issues=issues,
                navigation_links_observed=navigation_links_observed,
            )
        except Exception:
            pass

        # Before evaluating navigation links, ensure expandable menus are open
        _expand_closed_containers(
            page,
            policy.interaction_timeout_ms,
            raw,
            expand_navigation_groups=not policy.workflow_scope or workflow_match_status != "reached",
            expand_page_sections=not policy.workflow_scope or workflow_match_status == "reached",
        )
        # Re-observe after opening collapsed groups so newly revealed child
        # destinations can participate in workflow matching.
        if raw.get("expandableGroups"):
            try:
                _expanded_screen, raw = _capture_state(
                    page,
                    policy=policy,
                    screens=screens,
                    fingerprints=fingerprints,
                    issues=issues,
                    navigation_links_observed=navigation_links_observed,
                )
            except Exception:
                pass

        # Follow visible links from observation
        next_link = None
        current_url_clean = sanitized_url(page.url)
        available_links = [
            link for link in raw.get("navLinks", [])
            if not link.get("menu_trigger")
            and _link_block_reason(link, page.url, policy=policy) is None
        ]
        if policy.workflow_scope and workflow_match_status != "reached":
            matching_links = [
                link for link in available_links
                if not link.get("menu_trigger") and _workflow_label_matches(link.get("label"), policy.workflow_scope)
            ]
            if len(matching_links) > 1:
                workflow_match_status = "ambiguous"
                issues.append(
                    DiscoveryIssue(
                        code="workflow_scope_ambiguous",
                        status="incomplete",
                        summary="More than one visible navigation destination matches the requested workflow; none was opened.",
                        source_url=sanitized_url(page.url),
                    )
                )
            elif matching_links:
                next_link = matching_links[0]
                key = f"{current_url_clean}|{next_link.get('selector')}|{next_link.get('label')}|{sanitized_url(next_link.get('href') or '')}"
                if key in visited_hrefs:
                    next_link = None
                else:
                    visited_hrefs.add(key)
            else:
                workflow_match_status = "not_found"

        elif policy.workflow_scope and workflow_match_status == "reached":
            # Within the selected workflow, explore content links. Keep global
            # navigation excluded so sibling modules are not crawled.
            for link in available_links:
                if link.get("navigation_landmark"):
                    continue
                key = f"{current_url_clean}|{link.get('selector')}|{link.get('label')}|{sanitized_url(link.get('href') or '')}"
                if key in visited_hrefs:
                    continue
                visited_hrefs.add(key)
                next_link = link
                break

        for link in ([] if policy.workflow_scope else available_links):
            key = f"{current_url_clean}|{link.get('selector')}|{link.get('label')}|{sanitized_url(link.get('href') or '')}"
            if key in visited_hrefs:
                continue
            visited_hrefs.add(key)
            next_link = link
            break

        if policy.workflow_scope and next_link is None and workflow_match_status == "not_found":
            issues.append(
                DiscoveryIssue(
                    code="workflow_scope_not_found",
                    status="incomplete",
                    summary="The requested workflow was not found among safely observed navigation labels; no unrelated destination was opened.",
                    source_url=sanitized_url(page.url),
                )
            )
            break
        if policy.workflow_scope and workflow_match_status == "ambiguous":
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
            before_fingerprint = _fingerprint(raw)
            is_workflow_target = bool(
                policy.workflow_scope
                and _workflow_label_matches(next_link.get("label"), policy.workflow_scope)
            )
            try:
                clicked = False
                link_selector = next_link.get("selector")
                if link_selector and page.locator(link_selector).count() > 0:
                    try:
                        page.locator(link_selector).first.click(timeout=policy.interaction_timeout_ms)
                        clicked = True
                    except Exception:
                        pass
                if not clicked and next_link.get("href"):
                    try:
                        page.locator(f'a[href="{next_link["href"]}"]').first.click(timeout=policy.interaction_timeout_ms)
                        clicked = True
                    except Exception:
                        pass
                if not clicked:
                    page.get_by_text(next_link["label"], exact=False).first.click(timeout=policy.interaction_timeout_ms)
                navigation_links_visited += 1
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=policy.interaction_timeout_ms)
                except PlaywrightTimeoutError:
                    pass
                try:
                    page.wait_for_function(
                        r"""(prevUrl) => window.location.href !== prevUrl""",
                        arg=previous_url,
                        timeout=min(2500, policy.interaction_timeout_ms),
                    )
                except Exception:
                    pass
                _wait_for_angular_idle(page, timeout_ms=policy.interaction_timeout_ms)
                try:
                    page.wait_for_timeout(500)
                except Exception:
                    pass

                # Verify route or content transition
                after_fingerprint = _fingerprint(_safe_screen(page, policy))
                url_changed = sanitized_url(page.url) != sanitized_url(previous_url)
                content_changed = after_fingerprint != before_fingerprint
                if not (url_changed or content_changed):
                    issues.append(
                        DiscoveryIssue(
                            code="navigation_transition_unverified",
                            status="inaccessible",
                            summary="Navigation click did not result in a verified route or content transition.",
                            source_url=sanitized_url(previous_url),
                        )
                    )
                    continue

                if sanitized_url(page.url) in forbidden_responses:
                    issue_evidence = DiscoveryEvidence(
                        kind="navigation_link",
                        observed_at_utc=_utc_now(),
                        screen_url=sanitized_url(page.url),
                        locator_recipe=next_link.get("selector") or f"observed nav link {next_link.get('index', 0)}",
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
                if is_workflow_target:
                    workflow_match_status = "reached"
                    workflow_root_depth = len(navigation_stack)
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
        elif policy.workflow_scope:
            if workflow_root_depth is not None and len(navigation_stack) > workflow_root_depth:
                navigation_stack.pop()
                try:
                    page.go_back(timeout=policy.interaction_timeout_ms, wait_until="domcontentloaded")
                except Exception:
                    issues.append(
                        DiscoveryIssue(
                            code="workflow_navigation_return_failed",
                            status="partial",
                            summary="Could not return to a previously observed screen within the selected workflow.",
                            source_url=sanitized_url(page.url),
                        )
                    )
                    break
                continue
            break
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

    if len(screens) >= policy.max_screens:
        issues.append(
            DiscoveryIssue(
                code="screen_limit",
                status="partial",
                summary="Screen limit reached; additional workflow states were not inspected.",
                source_url=sanitized_url(page.url),
            )
        )

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
    unique_form_fields: dict[tuple[Any, ...], UIControlObservation] = {}
    for screen in screens:
        occurrence_by_signature: dict[tuple[Any, ...], int] = {}
        for field in screen.form_fields:
            signature = (
                field.label,
                field.control_type,
                tuple(field.section_path),
                field.placeholder,
                field.input_type,
            )
            occurrence = occurrence_by_signature.get(signature, 0)
            occurrence_by_signature[signature] = occurrence + 1
            unique_form_fields.setdefault((screen.url, *signature, occurrence), field)
    aggregated_form_fields = list(unique_form_fields.values())

    # Determine completion status
    if workflow_match_status in {"not_found", "ambiguous"}:
        discovery_status = "INCOMPLETE"
    elif len(screens) == 0 or len(navigation_links_observed) == 0:
        discovery_status = "INCOMPLETE"
        if len(navigation_links_observed) == 0:
            issues.append(
                DiscoveryIssue(
                    code="no_navigation_candidates_discovered",
                    status="incomplete",
                    summary="Zero navigation candidates discovered; crawler could not traverse the application.",
                    source_url=sanitized_url(page.url),
                )
            )
    elif any(issue.status in {"inaccessible", "incomplete", "partial"} for issue in issues):
        discovery_status = "PARTIAL"
    else:
        discovery_status = "COMPLETED"

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
        discovery_status=discovery_status,
        workflow_scope=policy.workflow_scope,
        workflow_match_status=workflow_match_status,
        form_fields=aggregated_form_fields,
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


def run_live_discovery(
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = lambda msg: print(msg, flush=True),
) -> UIDiscoveryResult | None:
    """Launch headed Edge for a user-scoped workflow and wait for manual auth."""
    base_url = (os.environ.get("UI_DISCOVERY_BASE_URL") or os.environ.get("ONEPV_BASE_URL") or "").strip()
    if not base_url:
        base_url = input_fn("Product URL to discover: ").strip()
    if not base_url:
        output_fn("A product URL is required; live discovery was not started.")
        return None
    workflow_scope = (os.environ.get("UI_DISCOVERY_WORKFLOW") or input_fn("Workflow to discover: ")).strip()
    if not workflow_scope:
        output_fn("A workflow scope is required; live discovery was not started.")
        return None
    environment_label = (
        (os.environ.get("UI_DISCOVERY_ENVIRONMENT") or "")
        or input_fn("Authorized environment (development, validation, or test): ").strip().casefold()
    ).strip().casefold()
    if environment_label not in {"development", "validation", "test"}:
        output_fn("Live discovery is limited to an explicitly identified development, validation, or test environment.")
        return None
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
        output_fn("Product URL is invalid; provide an authorized HTTP(S) URL without embedded credentials.")
        return None
    recorded_url = sanitized_url(base_url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="msedge",
            headless=False,
            ignore_default_args=["--disable-popup-blocking"],
        )
        context: BrowserContext = browser.new_context()
        page = context.new_page()

        def _disable_debugger(target_page: Page) -> None:
            try:
                cdp = context.new_cdp_session(target_page)
                cdp.send("Debugger.enable")
                cdp.send("Debugger.setSkipAllPauses", {"skip": True})
                cdp.send("Debugger.setBreakpointsActive", {"active": False})
            except Exception:
                pass

        _disable_debugger(page)

        def _on_new_page(new_page: Page) -> None:
            _disable_debugger(new_page)
            try:
                new_page.close()
            except Exception:
                pass

        context.on("page", _on_new_page)
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
                output_fn("Authentication required. Please log in using the Edge browser window.")
                output_fn("Discovery will start automatically as soon as you log in (no need to type in the terminal)...")
                try:
                    page.wait_for_function(
                        r"""() => {
                            const pwd = document.querySelector('input[type="password"]');
                            const notLogin = !window.location.pathname.toLowerCase().includes('/login');
                            return (!pwd || notLogin) && (window.location.pathname.length > 1);
                        }""",
                        timeout=300000,
                    )
                    page.wait_for_timeout(2000)
                    output_fn("Login detected! Commencing UI discovery...")
                except PlaywrightTimeoutError:
                    output_fn("Login wait timed out after 5 minutes; live discovery stopped.")
                    return None
                except Exception as exc:
                    output_fn(f"Login wait interrupted ({type(exc).__name__}); stopping.")
                    return None
            for p in list(context.pages):
                if p != page:
                    try:
                        p.close()
                    except Exception:
                        pass
            _disable_debugger(page)
            output_fn("Waiting for the product navigation to settle naturally...")
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            try:
                page.wait_for_selector(
                    'app-sidebar, nav, aside, .sidebar, [class*="sidebar"], [role="navigation"]',
                    timeout=15000,
                )
            except Exception:
                pass
            try:
                page.wait_for_timeout(2000)
            except Exception:
                pass
            result = discover_page(
                page,
                policy=DiscoveryPolicy(
                    max_screens=100,
                    max_interactions=300,
                    max_navigation_visits=100,
                    interaction_timeout_ms=1500,
                    live_discovery=True,
                    environment_label=environment_label,
                    capture_option_labels=False,
                    allowed_navigation_labels=None,
                    workflow_scope=workflow_scope,
                ),
            )
            form_fields = result.form_fields
            associated_fields = sum(field.label_match_status == "associated" for field in form_fields)
            output_fn(
                f"Live discovery status: {result.discovery_status} - {result.coverage.screens_observed} screens, "
                f"workflow '{workflow_scope}' ({result.workflow_match_status}), "
                f"{len(form_fields)} form fields ({associated_fields} labeled, "
                f"{len(form_fields) - associated_fields} unresolved), "
                f"{result.coverage.navigation_links_visited} navigation visited, "
                f"{len(result.coverage.issues)} coverage issues."
            )
            artifact_dir = os.path.join("backend", "artifacts")
            os.makedirs(artifact_dir, exist_ok=True)
            artifact_path = os.path.join(artifact_dir, "ui_discovery_live.json")
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))
            output_fn(f"Saved discovery report artifact to: {artifact_path}")
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


def run_live_onepv_discovery(
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = lambda msg: print(msg, flush=True),
) -> UIDiscoveryResult | None:
    """Backward-compatible entry point; inputs are still runtime configurable."""
    return run_live_discovery(input_fn=input_fn, output_fn=output_fn)


if __name__ == "__main__":
    result = run_live_discovery()
    if result is None:
        sys.exit(1)
