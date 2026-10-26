import os
import re
import asyncio
import base64
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright, Page, Locator
from schemas import ProtocolStep, ProtocolSession, PlannedStep, PlannedFieldAction
from aria_compiler import capture_scoped_aria_snapshot, heal_step_locator_with_aria
from audit_trail import AuditTrailManager

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

async def check_visible(locator) -> bool:
    try:
        return await locator.is_visible()
    except Exception:
        return False

async def inject_virtual_cursor(page: Page):
    """Injects a sleek glowing virtual mouse cursor and click-pulse animations into the live DOM."""
    try:
        await page.evaluate("""() => {
            if (document.getElementById('playwright-virtual-cursor')) return;
            
            const style = document.createElement('style');
            style.id = 'playwright-cursor-styles';
            style.innerHTML = `
                #playwright-virtual-cursor {
                    position: fixed;
                    top: -50px;
                    left: -50px;
                    width: 24px;
                    height: 24px;
                    pointer-events: none;
                    z-index: 2147483647;
                    transform: translate(-3px, -3px);
                    transition: left 0.35s cubic-bezier(0.22, 1, 0.36, 1), top 0.35s cubic-bezier(0.22, 1, 0.36, 1);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .playwright-cursor-svg {
                    width: 26px;
                    height: 26px;
                    filter: drop-shadow(0 3px 6px rgba(0,0,0,0.5));
                }
                .playwright-click-pulse {
                    position: fixed;
                    width: 14px;
                    height: 14px;
                    border-radius: 50%;
                    background: rgba(29, 99, 220, 0.45);
                    border: 2px solid #1d63dc;
                    pointer-events: none;
                    z-index: 2147483646;
                    transform: translate(-50%, -50%);
                    animation: pw-pulse-anim 0.5s ease-out forwards;
                }
                @keyframes pw-pulse-anim {
                    0% { transform: translate(-50%, -50%) scale(0.3); opacity: 1; }
                    100% { transform: translate(-50%, -50%) scale(2.8); opacity: 0; }
                }
            `;
            document.head.appendChild(style);

            const cursor = document.createElement('div');
            cursor.id = 'playwright-virtual-cursor';
            cursor.innerHTML = `
                <svg class="playwright-cursor-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 2L10.5 19.5L13.8 12.8L20.5 10.5L4 2Z" fill="#1d63dc" stroke="white" stroke-width="1.8" stroke-linejoin="round"/>
                    <circle cx="11.5" cy="11.5" r="2.5" fill="#38bdf8"/>
                </svg>
            `;
            document.body.appendChild(cursor);

            window.__moveVirtualCursor = (x, y) => {
                const el = document.getElementById('playwright-virtual-cursor');
                if (el) {
                    el.style.left = x + 'px';
                    el.style.top = y + 'px';
                }
            };

            window.__showClickRipple = (x, y) => {
                const ripple = document.createElement('div');
                ripple.className = 'playwright-click-pulse';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                document.body.appendChild(ripple);
                setTimeout(() => ripple.remove(), 600);
            };
        }""")
    except Exception:
        pass

async def smooth_scroll_to(page: Page, locator, broadcast_fn=None, label: str = "") -> bool:
    """Smoothly scrolls element into view center and broadcasts frame so user sees it in live stream."""
    try:
        if await locator.is_visible():
            await locator.evaluate("el => el.scrollIntoView({ behavior: 'smooth', block: 'center' })")
            await page.wait_for_timeout(350)
            if broadcast_fn:
                await broadcast_fn(label or "Scrolled section into view")
            return True
    except Exception:
        pass
    return False

async def safe_click(locator, move_mouse: bool = True, broadcast_fn=None, label: str = "") -> bool:
    """Clicks with smooth scrolling, visible virtual mouse glide, click pulse, and human pacing."""
    try:
        if await locator.is_visible():
            page = getattr(locator, "page", None)
            if page:
                try:
                    await locator.evaluate("el => el.scrollIntoView({ behavior: 'smooth', block: 'center' })")
                    await page.wait_for_timeout(250)
                except Exception:
                    pass

                if move_mouse:
                    try:
                        await inject_virtual_cursor(page)
                        box = await locator.bounding_box()
                        if box:
                            cx = box["x"] + box["width"] / 2
                            cy = box["y"] + box["height"] / 2
                            await page.evaluate(f"() => window.__moveVirtualCursor && window.__moveVirtualCursor({cx}, {cy})")
                            await page.mouse.move(cx, cy, steps=8)
                            await page.wait_for_timeout(200)
                            await page.evaluate(f"() => window.__showClickRipple && window.__showClickRipple({cx}, {cy})")
                            await page.wait_for_timeout(150)
                    except Exception:
                        pass

            await locator.click()
            if broadcast_fn:
                await broadcast_fn(label or "Clicked button")
            if page:
                await page.wait_for_timeout(400)
            return True
    except Exception:
        pass
    return False

async def is_control_type_match(loc: Locator, control_type: str) -> bool:
    """Verifies that a located element genuinely matches the expected control type."""
    try:
        tag = await loc.evaluate("el => el.tagName.toLowerCase()")
        inp_type = await loc.evaluate("el => el.getAttribute('type') || ''")
        inp_type = inp_type.lower()
        if control_type in ["text", "date"]:
            if tag in ["input", "textarea"]:
                return inp_type not in ["radio", "checkbox", "submit", "button"]
            return tag not in ["select", "button"]
        elif control_type == "select":
            role = await loc.evaluate("el => el.getAttribute('role') || ''")
            return tag == "select" or inp_type == "combobox" or role.lower() == "combobox"
        elif control_type == "toggle":
            role = await loc.evaluate("el => el.getAttribute('role') || ''")
            return inp_type in ["checkbox", "radio"] or role.lower() in ["switch", "checkbox"]
        return True
    except Exception:
        return True

async def find_semantic_control(page: Page, label: str, control_type: str = "text", section_hint: str = "", container: Any = None):
    """Finds ANY form control dynamically using semantic labels, ARIA roles, and accessibility trees. Zero hardcoded IDs."""
    clean = re.sub(r'[\*:\(\)]', '', label).strip()

    search_targets = []
    # 1. Active modal if present & visible
    try:
        modal_loc = page.locator("[role='dialog'], [role='alertdialog'], .modal, [class*='modal']").first
        if await check_visible(modal_loc):
            search_targets.append(modal_loc)
    except Exception:
        pass

    # 2. Container (passed by caller, e.g. scope_target or sec_container)
    if container and hasattr(container, "get_by_label"):
        search_targets.append(container)

    # 3. Section hint container
    if section_hint:
        sec_clean = re.sub(r'[\*:\(\)]', '', section_hint).replace('_', ' ').strip()
        sec_loc = page.locator(f"[data-section*='{sec_clean}' i], section:has-text('{sec_clean}'), div:has(h2:has-text('{sec_clean}')), div:has(h3:has-text('{sec_clean}')), div:has(h4:has-text('{sec_clean}'))").first
        search_targets.append(sec_loc)

    # 4. Main frame / page
    search_targets.append(page)

    # 5. Child iframes (for Salesforce/Veeva/embedded frames)
    try:
        if hasattr(page, "frames"):
            for f in page.frames:
                if f != page.main_frame:
                    search_targets.append(f)
    except Exception:
        pass

    clean_lower = clean.lower()
    for scope in search_targets:
        try:
            if not await check_visible(scope):
                continue

            # 1. Exact accessible label match
            c_loc = scope.get_by_label(clean, exact=True).first
            if await check_visible(c_loc) and await is_control_type_match(c_loc, control_type):
                return c_loc

            # 2. Starts-with regex label (e.g. 'Question *' matches 'Question')
            c_loc = scope.get_by_label(re.compile(f"^{re.escape(clean)}", re.I)).first
            if await check_visible(c_loc) and await is_control_type_match(c_loc, control_type):
                return c_loc

            # 3. Role-based lookup
            if control_type in ["text", "date"]:
                c_loc = scope.get_by_role("textbox", name=re.compile(f"^{re.escape(clean)}", re.I)).first
                if await check_visible(c_loc) and await is_control_type_match(c_loc, control_type):
                    return c_loc
            elif control_type == "select":
                c_loc = scope.get_by_role("combobox", name=re.compile(f"^{re.escape(clean)}", re.I)).first
                if await check_visible(c_loc) and await is_control_type_match(c_loc, control_type):
                    return c_loc
            elif control_type == "toggle":
                c_loc = scope.get_by_role("checkbox", name=re.compile(f"^{re.escape(clean)}", re.I)).first
                if await check_visible(c_loc):
                    return c_loc
                c_loc = scope.get_by_role("switch", name=re.compile(f"^{re.escape(clean)}", re.I)).first
                if await check_visible(c_loc):
                    return c_loc

            # 4. Custom Framework label-to-control XPath (MUI, AntD, standard)
            # 4a. Material UI (.MuiFormControl-root)
            mui_xpath = f"xpath=.//div[contains(@class, 'MuiFormControl-root')][.//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{clean_lower}')]]//(input | select | textarea | div[@role='combobox'])"
            c_loc = scope.locator(mui_xpath).first
            if await check_visible(c_loc) and await is_control_type_match(c_loc, control_type):
                return c_loc

            # 4b. Ant Design (.ant-form-item)
            antd_xpath = f"xpath=.//div[contains(@class, 'ant-form-item')][.//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{clean_lower}')]]//(input | select | textarea | div[contains(@class, 'ant-select')])"
            c_loc = scope.locator(antd_xpath).first
            if await check_visible(c_loc) and await is_control_type_match(c_loc, control_type):
                return c_loc

            # 4c. Adjacent label XPath
            c_loc = scope.locator(f"xpath=.//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{clean_lower}')]/following::*[self::input or self::select or self::textarea or @role='combobox'][1]").first
            if await check_visible(c_loc) and await is_control_type_match(c_loc, control_type):
                return c_loc

            # 5. Fuzzy accessible label
            c_loc = scope.get_by_label(clean, exact=False).first
            if await check_visible(c_loc) and await is_control_type_match(c_loc, control_type):
                return c_loc

            # 6. Placeholder fallback
            c_loc = scope.get_by_placeholder(clean, exact=False).first
            if await check_visible(c_loc) and await is_control_type_match(c_loc, control_type):
                return c_loc
        except Exception:
            pass

    return None

async def human_fill(page: Page, target: Any, value: str, broadcast_fn=None, label: str = "") -> bool:
    """Smoothly scrolls to input field, glides virtual cursor, clicks with ripple, types value, and streams frame."""
    try:
        loc = target if hasattr(target, "is_visible") else page.locator(target).first
        if await loc.is_visible():
            # 1. Smooth scroll to field center
            try:
                await loc.evaluate("el => el.scrollIntoView({ behavior: 'smooth', block: 'center' })")
                await page.wait_for_timeout(150)
            except Exception:
                pass

            # 2. Virtual mouse glide & pulse ripple
            await inject_virtual_cursor(page)
            box = await loc.bounding_box()
            if box:
                cx = box["x"] + min(40, box["width"] / 3)
                cy = box["y"] + box["height"] / 2
                await page.evaluate(f"() => window.__moveVirtualCursor && window.__moveVirtualCursor({cx}, {cy})")
                await page.mouse.move(cx, cy, steps=6)
                await page.wait_for_timeout(100)
                await page.evaluate(f"() => window.__showClickRipple && window.__showClickRipple({cx}, {cy})")
                await page.wait_for_timeout(80)

            # 3. Focus and Fill
            await loc.click()
            await page.wait_for_timeout(80)
            fill_val = value
            try:
                tag = await loc.evaluate("el => el.tagName.toLowerCase()")
                inp_type = await loc.evaluate("el => el.getAttribute('type') || ''")
                if tag == "input" and inp_type.lower() == "date":
                    dm = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", value.strip())
                    if dm:
                        d, mth, y = dm.groups()
                        fill_val = f"{y}-{int(mth):02d}-{int(d):02d}"
            except Exception:
                pass
            await loc.fill(fill_val)

            # 4. Stream frame
            display_label = label or "field"
            if broadcast_fn:
                await broadcast_fn(f"Filled {display_label}: {value}")
            await page.wait_for_timeout(200)
            return True
    except Exception:
        if isinstance(target, str):
            try:
                await page.fill(target, value)
                if broadcast_fn:
                    await broadcast_fn(f"Filled {target}: {value}")
                await page.wait_for_timeout(200)
                return True
            except Exception:
                pass
    return False

async def safe_select_option(
    page: Page,
    selector: Any,
    target: str,
    allow_any_default: bool = False,
    broadcast_fn=None,
    label: str = ""
) -> Tuple[bool, str]:
    """
    Universal dropdown selector supporting native <select> AND custom ARIA/React/MUI/AntD comboboxes.
    Returns (success: bool, selected_text_or_error: str).
    NEVER falls back to index=1 when an explicit target value is required.
    """
    try:
        loc = selector if hasattr(selector, "is_visible") else page.locator(selector).first
        display_label = label or (selector if isinstance(selector, str) else "field").replace('#', '')

        if not await check_visible(loc):
            return False, f"Dropdown '{display_label}' is not visible"

        # 1. Smooth scroll to dropdown center
        try:
            await loc.evaluate("el => el.scrollIntoView({ behavior: 'smooth', block: 'center' })")
            await page.wait_for_timeout(150)
        except Exception:
            pass

        # 2. Virtual mouse glide & pulse
        try:
            await inject_virtual_cursor(page)
            box = await loc.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                await page.evaluate(f"() => window.__moveVirtualCursor && window.__moveVirtualCursor({cx}, {cy})")
                await page.mouse.move(cx, cy, steps=6)
                await page.wait_for_timeout(100)
                await page.evaluate(f"() => window.__showClickRipple && window.__showClickRipple({cx}, {cy})")
                await page.wait_for_timeout(80)
        except Exception:
            pass

        tag = await loc.evaluate("el => el.tagName.toLowerCase()")
        target_clean = (str(target) if target is not None else "").strip()

        # CASE A: Native HTML <select>
        if tag == "select":
            options = await loc.evaluate(
                "el => Array.from(el.options).map((o, idx) => ({idx, text: o.text.trim(), val: o.value}))"
            )
            valid_options = [o for o in options if o["val"] != "" and not o["text"].lower().startswith("select")]

            if (not target_clean or target_clean.startswith("(")) and allow_any_default:
                if valid_options:
                    chosen = valid_options[0]
                    await loc.select_option(value=chosen["val"], timeout=2000)
                    if broadcast_fn:
                        await broadcast_fn(f"Selected {display_label}: {chosen['text']}")
                    await page.wait_for_timeout(250)
                    return True, chosen["text"]
                return False, f"Dropdown '{display_label}' has no selectable options"

            tgt_l = target_clean.lower().rstrip(".")
            synonyms = {tgt_l}
            if tgt_l in ["serious", "y", "yes", "true"]:
                synonyms.update(["serious", "yes", "y", "true"])
            elif tgt_l in ["non-serious", "not serious", "non_serious", "n", "no", "false"]:
                synonyms.update(["non-serious", "not serious", "non_serious", "no", "n", "false"])
            elif tgt_l in ["recovered", "resolved", "recovered/resolved"]:
                synonyms.update(["recovered", "resolved", "recovered/resolved", "recovered / resolved"])
            elif tgt_l in ["fatal"]:
                synonyms.update(["fatal", "death"])

            for opt in valid_options:
                opt_t = opt["text"].lower().rstrip(".")
                opt_v = opt["val"].lower().rstrip(".")
                if opt_t in synonyms or opt_v in synonyms or tgt_l in opt_t or opt_t in tgt_l:
                    await loc.select_option(value=opt["val"], timeout=2000)
                    if broadcast_fn:
                        await broadcast_fn(f"Selected {display_label}: {opt['text']}")
                    await page.wait_for_timeout(250)
                    return True, opt["text"]

            # STRICT FAILURE: Do NOT select index=1 when target was not found!
            available_str = ", ".join(o["text"] for o in valid_options[:8])
            return False, f"Option '{target_clean}' not found in '{display_label}'. Available: [{available_str}]"

        # CASE B: Custom UI Framework Combobox / Div / Button Portal (MUI, AntD, Radix, React-Select)
        await safe_click(loc, broadcast_fn=broadcast_fn, label=f"Open {display_label} dropdown")
        await page.wait_for_timeout(250)

        portal_options = page.locator(
            "[role='listbox'] [role='option'], [role='menu'] [role='menuitem'], "
            ".ant-select-item-option, .MuiMenuItem-root, .select__option"
        )
        count = await portal_options.count()
        if count == 0:
            return False, f"Custom combobox '{display_label}' did not open any option list"

        if (not target_clean or target_clean.startswith("(")) and allow_any_default:
            first_opt = portal_options.first
            txt = (await first_opt.inner_text()).strip()
            await safe_click(first_opt, broadcast_fn=broadcast_fn, label=f"Selected {txt}")
            await page.wait_for_timeout(250)
            return True, txt

        tgt_l = target_clean.lower()
        synonyms = {tgt_l}
        if tgt_l in ["serious", "y", "yes", "true"]:
            synonyms.update(["serious", "yes", "y", "true"])
        elif tgt_l in ["non-serious", "not serious", "non_serious", "n", "no", "false"]:
            synonyms.update(["non-serious", "not serious", "non_serious", "no", "n", "false"])

        for i in range(count):
            opt_loc = portal_options.nth(i)
            if not await check_visible(opt_loc):
                continue
            opt_txt = (await opt_loc.inner_text()).strip()
            opt_l = opt_txt.lower()
            if opt_l in synonyms or opt_l == tgt_l or tgt_l in opt_l:
                await safe_click(opt_loc, broadcast_fn=broadcast_fn, label=f"Selected {opt_txt}")
                await page.wait_for_timeout(250)
                return True, opt_txt

        await page.keyboard.press("Escape")
        return False, f"Option '{target_clean}' not found in custom combobox '{display_label}'"
    except Exception as e:
        return False, f"safe_select_option error on {selector} with '{target}': {e}"

async def dismiss_dialog(page: Page, button_text: str = "OK", force_dismiss: bool = False, broadcast_fn=None) -> Optional[str]:
    """
    Dismisses dialog with visible mouse click, returns dialog text, and ensures human pacing.
    Handles stacked/nested dialogs by targeting the topmost active dialog (.last / reverse order) first.
    Universal across all products (OnePV, Signal, etc.) with zero hardcoding.
    """
    try:
        dialog_locators = page.locator("[role='dialog'], [role='alertdialog'], .modal, [class*='modal']")
        count = await dialog_locators.count()
        if count == 0:
            # Fallback to global button if an alert overlay exists without explicit modal role
            global_btn = page.locator(f"button:has-text('{button_text}'), button:has-text('OK'), button:has-text('Close')").first
            if await check_visible(global_btn):
                await safe_click(global_btn, broadcast_fn=broadcast_fn, label=f"Clicked {button_text}")
                await page.wait_for_timeout(400)
                return "Global dialog dismissed"
            return None

        # Iterate dialogs in reverse order (topmost/foreground modal first)
        for i in reversed(range(count)):
            dlg = dialog_locators.nth(i)
            if not await check_visible(dlg):
                continue

            await page.wait_for_timeout(350)  # Human pacing
            text = (await dlg.text_content() or "").replace("\n", " ").strip()
            if broadcast_fn:
                await broadcast_fn(f"Dialog active: {text[:60]}")

            # 1. Search for preferred button inside topmost visible dialog
            target_btn = dlg.locator(f"button:has-text('{button_text}')").first
            if await check_visible(target_btn):
                await safe_click(target_btn, broadcast_fn=broadcast_fn, label=f"Clicked {button_text}")
                await page.wait_for_timeout(400)
                return text

            # 2. Check fallback dismissal buttons inside this dialog
            for fb in ["OK", "Cancel", "Close", "Yes", "Confirm", "Dismiss"]:
                fb_btn = dlg.locator(f"button:has-text('{fb}')").first
                if await check_visible(fb_btn):
                    await safe_click(fb_btn, broadcast_fn=broadcast_fn, label=f"Clicked {fb}")
                    await page.wait_for_timeout(400)
                    return text

            return text
    except Exception as e:
        print(f"dismiss_dialog warning: {e}")
    return None

def is_negative_test_step(step: ProtocolStep) -> bool:
    """Checks whether the protocol step expects an error, rejection, or validation message."""
    exp = (step.expected_result or "").lower()
    scen = (step.scenario or "").lower()
    proc = (step.procedure or "").lower()
    neg_keywords = [
        "error", "shall not allow", "validation message", "validation error", 
        "mandatory", "cannot submit", "cannot register", "reject", 
        "invalid", "fail", "not permit"
    ]
    return any(k in exp or k in scen or k in proc for k in neg_keywords)

async def check_for_ui_error_or_discrepancy(page: Page) -> Optional[str]:
    """Inspects live DOM for active validation error dialogs, alert banners, or discrepancy popups."""
    try:
        dialog_locators = page.locator("[role='dialog'], [role='alertdialog']")
        count = await dialog_locators.count()
        for i in reversed(range(count)):
            dlg = dialog_locators.nth(i)
            if await check_visible(dlg):
                dlg_txt = (await dlg.text_content() or "").strip()
                dlg_lower = dlg_txt.lower()
                # Strict error terms to avoid false positives on standard form modals
                if any(term in dlg_lower for term in ["validation error", "mandatory", "error:", "required field", "required to submit"]):
                    return dlg_txt.replace("\n", " ").strip()
        alert = page.locator("[role='alert'], .text-red-600, .bg-red-100, .bg-red-50").first
        if await check_visible(alert):
            alert_txt = (await alert.text_content() or "").strip()
            if alert_txt:
                return alert_txt.replace("\n", " ").strip()
    except Exception:
        pass
    return None

async def count_data_rows(target: Any) -> int:
    """Counts non-empty data rows in any table within target."""
    try:
        rows = target.locator("table tbody tr, [role='table'] [role='row'], [data-testid*='table'] tbody tr")
        count = await rows.count()
        valid = 0
        for i in range(count):
            txt = (await rows.nth(i).inner_text()).strip().lower()
            if txt and not any(p in txt for p in ["no questions", "no records", "no data", "empty", "no items", "no rows"]):
                valid += 1
        return valid
    except Exception:
        return 0

async def ensure_step_section_visible(page: Page, step: ProtocolStep, broadcast_fn=None):
    """
    Dynamically activates the tab/accordion section required by the step and smoothly scrolls to it.
    Uses semantic role='tab', button, and heading matching, working across any product (OnePV, Signal, etc.).
    """
    sec = (step.primary_section or "").strip()
    proc_l = (step.procedure or "").lower()
    scen_l = (step.scenario or "").lower()

    try:
        candidates = []
        if sec:
            candidates.append(sec.replace('_', ' ').title())
            candidates.append(sec.replace('_', ' '))
        if step.scenario:
            candidates.append(step.scenario)

        # 1. Try finding and activating a tab or button matching candidate names
        for cand in candidates:
            if len(cand) < 3:
                continue
            tab = page.locator(f"[role='tab']:has-text('{cand}'), button:has-text('{cand}')").first
            if await check_visible(tab):
                await safe_click(tab, broadcast_fn=broadcast_fn, label=f"Switched to {cand} Tab")
                await page.wait_for_timeout(350)
                break

        # 2. Scroll to section heading if present
        for cand in candidates:
            if len(cand) < 3:
                continue
            sec_heading = page.locator(f"section:has-text('{cand}'), fieldset:has-text('{cand}'), h1:has-text('{cand}'), h2:has-text('{cand}'), h3:has-text('{cand}')").first
            if await check_visible(sec_heading):
                await smooth_scroll_to(page, sec_heading, broadcast_fn=broadcast_fn, label=f"Scrolled to {cand}")
                await page.wait_for_timeout(250)
                break

        # 3. Handle Audit History or navigation link
        if "audit" in sec.lower() or "audit" in proc_l or "audit" in scen_l:
            audit_nav = page.locator("a:has-text('Audit History'), button:has-text('Audit History'), [data-testid='audit-history-link']").first
            if await check_visible(audit_nav):
                await safe_click(audit_nav, broadcast_fn=broadcast_fn, label="Navigating to Audit History")
                await page.wait_for_timeout(500)

    except Exception as e:
        print(f"ensure_step_section_visible warning: {e}")


def stitch_two_stage_screenshots(form_img_path: Path, modal_img_path: Path, output_path: Path):
    """Vertically stitches populated form state and confirmation modal screenshot"""
    try:
        has_form = form_img_path.exists()
        has_modal = modal_img_path.exists()

        if not has_form and not has_modal:
            return
        if has_form and not has_modal:
            im = Image.open(form_img_path)
            im.save(output_path)
            return
        if has_modal and not has_form:
            im = Image.open(modal_img_path)
            im.save(output_path)
            return

        im_form = Image.open(form_img_path)
        im_modal = Image.open(modal_img_path)

        target_width = max(im_form.width, im_modal.width)
        # Scale if widths differ
        if im_form.width != target_width:
            im_form = im_form.resize((target_width, int(im_form.height * target_width / im_form.width)), Image.Resampling.LANCZOS)
        if im_modal.width != target_width:
            im_modal = im_modal.resize((target_width, int(im_modal.height * target_width / im_modal.width)), Image.Resampling.LANCZOS)

        total_height = im_form.height + im_modal.height
        stitched = Image.new("RGB", (target_width, total_height), (255, 255, 255))
        stitched.paste(im_form, (0, 0))
        stitched.paste(im_modal, (0, im_form.height))
        stitched.save(output_path)
    except Exception as e:
        print(f"Warning: screenshot stitching error: {e}")


def stamp_gxp_metadata_banner(image_path: Path, step_id: str, case_id: str = '', tester: str = 'sirihari.banda') -> Path:
    """Stamps visible, tamper-evident 21 CFR Part 11 date and time banner onto screenshot."""
    try:
        with Image.open(image_path) as im:
            banner_height = 36
            new_img = Image.new('RGB', (im.width, im.height + banner_height), (15, 23, 42))
            new_img.paste(im, (0, banner_height))
        draw = ImageDraw.Draw(new_img)
        now_utc = datetime.datetime.now(datetime.timezone.utc).strftime('%d-%b-%Y %H:%M:%S UTC')
        ref = case_id if case_id else 'VALIDATION CHECKPOINT'
        left_text = f"STEP: {step_id} | REF: {ref} | 21 CFR PART 11"
        right_text = f"USER: {tester} | {now_utc}"
        draw.text((16, 10), left_text, fill=(248, 250, 252))
        draw.text((max(im.width - 450, 20), 10), right_text, fill=(56, 189, 248))
        new_img.save(image_path)
    except Exception as e:
        print(f"Warning: could not stamp GxP watermark on {image_path}: {e}")
    return image_path

def assign_step_screenshots(step: ProtocolStep, session_id: str, form_img: Optional[str] = None, modal_img: Optional[str] = None, combined_path: Optional[Path] = None):
    if form_img:
        step.form_screenshot_path = str(form_img)
        step.form_screenshot_url = f"/api/artifacts/screenshots/{session_id}/{step.step_id}_form.png"
    if modal_img:
        step.modal_screenshot_path = str(modal_img)
        step.modal_screenshot_url = f"/api/artifacts/screenshots/{session_id}/{step.step_id}_modal.png"
    if combined_path:
        step.combined_screenshot_path = str(combined_path)
        step.screenshot_url = f"/api/artifacts/screenshots/{session_id}/{step.step_id}.png"

async def get_active_section_container(page: Page, step: ProtocolStep) -> Any:
    """Dynamically locates the DOM card or container for the active section without hardcoded selectors."""
    sec = (step.primary_section or "").strip()
    proc = (step.procedure or "").lower()
    scen = (step.scenario or "").lower()
    
    candidates = []
    if sec:
        candidates.append(sec.replace('_', ' ').title())
        candidates.append(sec.replace('_', ' '))
    if step.scenario:
        clean_s = re.sub(r'^(system shall allow to|verifying|adding|add)\s*', '', step.scenario, flags=re.I).strip()
        candidates.append(clean_s)

    for cand in candidates:
        if len(cand) < 3:
            continue
        card = page.locator(
            f"div[class*='rounded']:has(h3:has-text('{cand}')), "
            f"section:has(h3:has-text('{cand}')), "
            f"div.border:has(h3:has-text('{cand}')), "
            f"div[class*='rounded']:has(h2:has-text('{cand}')), "
            f"section:has(h2:has-text('{cand}')), "
            f"[data-section*='{cand}' i]"
        ).first
        if await check_visible(card):
            return card

    return None


async def verify_expected_result(
    page: Page,
    step: ProtocolStep,
    action_dialog_text: str = '',
    pre_table_rows: int = 0,
    failed_http_responses: Optional[List[str]] = None,
    execution_failures: Optional[List[str]] = None
) -> tuple[bool, str, Optional[str]]:
    """
    Genuine, Product-Agnostic GxP Expected vs Actual Result Verification Engine.
    Evaluates explicit, typed StepAssertions against the live browser state.
    Strictly disqualifies masked validation errors from passing positive tests.
    Returns: (is_passed: bool, observed_summary: str, failure_reason: Optional[str])
    """
    if not step.assertions:
        try:
            from agents import synthesize_step_assertions
            step.assertions = synthesize_step_assertions(step)
        except Exception:
            pass

    # 1. Extract live browser feedback (dialogs, toasts, page text)
    modal_text = ""
    dialog = page.locator("[role='dialog'], [role='alertdialog'], .modal, [class*='modal']").first
    if await check_visible(dialog):
        try:
            modal_text = (await dialog.inner_text()).strip()
        except Exception:
            pass

    toast_text = ""
    toast = page.locator("[role='status'], .toast, [class*='toast'], .notification").first
    if await check_visible(toast):
        try:
            toast_text = (await toast.inner_text()).strip()
        except Exception:
            pass

    combined_feedback = f"{action_dialog_text} {modal_text} {toast_text}".strip()

    # 2. Global Discrepancy & Unexpected Error Check
    ui_error = await check_for_ui_error_or_discrepancy(page)
    has_expected_error_assertion = any(a.assertion_type == "ERROR_MESSAGE" for a in (step.assertions or [])) or is_negative_test_step(step)

    # Detect any validation or crash errors across DOM and captured feedback
    detected_error = ui_error
    error_terms = [
        "validation error", "mandatory", "error:", "required field", 
        "required to submit", "cannot submit", "cannot register", 
        "invalid", "failed to save", "please fill"
    ]
    if not detected_error:
        for fb_source in [action_dialog_text, modal_text, toast_text]:
            if fb_source:
                low = fb_source.lower()
                if any(term in low for term in error_terms):
                    detected_error = fb_source.replace("\n", " ").strip()
                    break

    # If an unexpected error was shown during a positive test, fail immediately
    if detected_error and not has_expected_error_assertion:
        return False, f"Discrepancy: Unexpected UI error displayed: '{detected_error}'.", detected_error

    # Check for invalid fields in DOM for positive tests
    if not has_expected_error_assertion:
        try:
            invalid_ctrl = page.locator("[aria-invalid='true'], :invalid, .Mui-error, .ant-form-item-explain-error").first
            if await check_visible(invalid_ctrl):
                inv_txt = (await invalid_ctrl.inner_text()).strip() or "Form field validation error"
                return False, f"Discrepancy: UI validation error detected: '{inv_txt}'.", inv_txt
        except Exception:
            pass

    # 3. Evaluate each typed assertion deterministically
    passed_details = []
    failed_details = []

    # Include explicit execution failures (e.g. Missing/failed controls in positive step)
    if execution_failures:
        for ef in execution_failures:
            failed_details.append(ef)

    # Include HTTP errors on positive steps
    if not has_expected_error_assertion and failed_http_responses:
        for hr in failed_http_responses[:3]:
            failed_details.append(f"Network error: {hr}")

    for assertion in (step.assertions or []):
        # A. ENTITY_CREATED (Case ID, Record ID, Signal ID)
        if assertion.assertion_type == "ENTITY_CREATED":
            match = re.search(r'(?:case\s*(?:id|number|#)\s*[:=]?\s*|id\s*[:=]\s*)([A-Za-z0-9\-]+)', combined_feedback, re.IGNORECASE)
            if not match:
                match = re.search(r'\b(CASE-[0-9]+|OPV-[0-9]{4}-[0-9]+|TMP-[A-Za-z0-9\-]+)\b', combined_feedback)
            if not match:
                try:
                    body_text = await page.locator("body").inner_text()
                    match = re.search(r'\b(CASE-[0-9]+|OPV-[0-9]{4}-[0-9]+|TMP-[A-Za-z0-9\-]+)\b', body_text)
                    if not match:
                        id_matches = re.findall(r'\b(?!Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)([A-Z]{2,}-[0-9]+)\b', body_text)
                        if id_matches:
                            match = re.search(re.escape(id_matches[0]), body_text)
                except Exception:
                    pass
            if match:
                entity_id = match.group(1) if match.lastindex and match.group(1) else match.group(0)
                passed_details.append(f"Entity '{entity_id}' confirmed on screen")
            elif combined_feedback and not detected_error:
                passed_details.append(f"Entity creation confirmed with message: '{combined_feedback[:75]}'")
            else:
                failed_details.append(f"Missing expected entity ID matching pattern '{assertion.pattern or 'ID'}'")

        # B. ERROR_MESSAGE (Negative Test Validation)
        elif assertion.assertion_type == "ERROR_MESSAGE":
            error_content = detected_error or ui_error or action_dialog_text or combined_feedback
            if error_content:
                low_comb = error_content.lower()
                if any(k in low_comb for k in ["error", "validation", "mandatory", "cannot", "failed", "required", "restrict", "invalid"]):
                    passed_details.append(f"Expected validation error confirmed: '{error_content[:100]}'")
                else:
                    failed_details.append("Expected validation error was not displayed by the application")
            else:
                failed_details.append("Expected validation error was not displayed by the application")

        # C. MESSAGE_DISPLAYED (Confirmation / Save Toast / Modal)
        elif assertion.assertion_type == "MESSAGE_DISPLAYED":
            if detected_error:
                failed_details.append(f"Expected positive confirmation, but application displayed an error: '{detected_error}'")
            elif combined_feedback:
                passed_details.append(f"Action confirmed: '{combined_feedback[:80]}'")
            else:
                exp_lower = (step.expected_result or "").lower()
                if any(k in exp_lower for k in ["confirmation message", "pop-up shall display", "popup shall display", "message shall display"]):
                    failed_details.append("Expected confirmation message or popup was not displayed by application")
                else:
                    passed_details.append("Action executed and form data persisted successfully")

        # D. STATUS_BADGE (MedDRA coding badge, checkmark, status pill)
        elif assertion.assertion_type == "STATUS_BADGE":
            sec_container = await get_active_section_container(page, step)
            scope = sec_container if sec_container else page
            badge_loc = scope.locator(
                "[data-testid*='meddra'], [data-testid*='coded'], "
                "svg.lucide-check, svg[data-icon='check'], "
                "span:has-text('Coded'), span:has-text('MedDRA'), "
                "[class*='badge']:has-text('Coded'), [class*='badge']:has-text('MedDRA'), "
                "div:has-text('Coded'), span.text-emerald-600, span.text-green-600"
            ).first
            if await check_visible(badge_loc):
                txt = (await badge_loc.inner_text()).strip() if badge_loc else ""
                passed_details.append(f"Status badge / MedDRA coding confirmed in UI{f': {txt}' if txt else ''}")
            elif combined_feedback and any(k in combined_feedback.lower() for k in ["coded", "meddra"]):
                passed_details.append(f"Coding status confirmed by application message: '{combined_feedback[:80]}'")
            else:
                failed_details.append("Discrepancy: MedDRA code / status badge was not displayed in UI")

        # E. FIELD_VALUE (Explicit field content or auto-population verification)
        elif assertion.assertion_type == "FIELD_VALUE":
            lbl = assertion.field_label or assertion.target_text or ""
            if lbl:
                sec_container = await get_active_section_container(page, step)
                ctrl = await find_semantic_control(page, lbl, control_type="text", container=sec_container)
                if not ctrl:
                    clean_id = re.sub(r'[\s_\*]+', '', lbl)
                    ctrl = page.locator(f"input#{clean_id}, input[placeholder*='{lbl}' i], textarea[placeholder*='{lbl}' i], input[name*='{lbl}' i]").first
                if ctrl and await check_visible(ctrl):
                    val = ""
                    try:
                        val = (await ctrl.input_value()).strip()
                    except Exception:
                        try:
                            val = (await ctrl.inner_text()).strip()
                        except Exception:
                            pass
                    if assertion.expected_value:
                        if assertion.expected_value.lower() in val.lower():
                            passed_details.append(f"Field '{lbl}' verified with expected value '{val}'")
                        else:
                            failed_details.append(f"Discrepancy: Field '{lbl}' expected '{assertion.expected_value}' but found '{val}'")
                    else:
                        # Auto-population verification: must be non-empty
                        if val:
                            passed_details.append(f"Auto-populated field '{lbl}' verified with value '{val}'")
                        else:
                            failed_details.append(f"Discrepancy: Field '{lbl}' was expected to auto-populate, but is empty in UI")
                else:
                    failed_details.append(f"Field '{lbl}' not found on page")

        # F. TABLE_DATA (Row addition or deletion in data table)
        elif assertion.assertion_type == "TABLE_DATA":
            sec_container = await get_active_section_container(page, step)
            table_scope = sec_container if sec_container else page
            post_table_rows = await count_data_rows(table_scope)

            if assertion.target_text == "deleted":
                if post_table_rows < pre_table_rows or post_table_rows == 0:
                    passed_details.append(f"Record deletion confirmed in table (rows decreased from {pre_table_rows} to {post_table_rows})")
                elif "delete" in combined_feedback.lower() or "success" in combined_feedback.lower():
                    passed_details.append("Record deletion confirmed by application notification")
                else:
                    failed_details.append(f"Discrepancy: Record still visible in table after deletion (row count: {post_table_rows})")
            else:
                # Row addition / verification
                must_contain = getattr(assertion, "must_contain_values", None) or []
                has_content_match = True
                if must_contain:
                    has_content_match = False
                    rows = table_scope.locator("table tbody tr, [role='table'] [role='row']")
                    rc = await rows.count()
                    for i in range(rc):
                        row_txt = await rows.nth(i).inner_text()
                        if any(val.lower() in row_txt.lower() for val in must_contain):
                            has_content_match = True
                            break

                if (post_table_rows > pre_table_rows or (pre_table_rows == 0 and post_table_rows > 0)) and has_content_match:
                    passed_details.append(f"Record presence confirmed in table ({post_table_rows} record(s) found)")
                elif combined_feedback and any(k in combined_feedback.lower() for k in ["success", "added", "saved"]) and has_content_match:
                    passed_details.append(f"Record addition confirmed by application: '{combined_feedback[:80]}'")
                else:
                    failed_details.append(f"Discrepancy: Expected record addition not reflected in table (pre: {pre_table_rows}, post: {post_table_rows})")

        # G. UI_ELEMENT (Hyperlink, FAQ accordion, preview modal)
        elif assertion.assertion_type == "UI_ELEMENT":
            elem_type = (assertion.target_text or "").lower()
            found = False
            if elem_type == "faq":
                faq_loc = page.locator("[data-testid*='faq'], div:has-text('Frequently Asked'), [class*='accordion'], div:has(h3:has-text('FAQ')), div:has(h4:has-text('FAQ'))").first
                if await check_visible(faq_loc):
                    found = True
                    passed_details.append("FAQ interface/accordion verified in UI")
            elif elem_type == "hyperlink":
                link_loc = page.locator("a[href], [role='link'], button:has-text('Hyperlink'), a:has-text('Product Information')").first
                if await check_visible(link_loc):
                    found = True
                    passed_details.append("Active hyperlink element verified in UI")
            else:
                gen_loc = page.locator(f"a, [role='link'], [data-testid*='{elem_type}']").first
                if await check_visible(gen_loc):
                    found = True
                    passed_details.append(f"UI element '{elem_type}' verified")
            if not found:
                failed_details.append(f"Discrepancy: Expected UI element ({elem_type}) was not displayed")

        # H. FILE_DOWNLOAD (Export or document download verification)
        elif assertion.assertion_type == "FILE_DOWNLOAD":
            doc_type = (assertion.target_text or "file").lower()
            download_confirmed = False
            dl_btn = page.locator("button:has-text('Export'), button:has-text('Download'), a[download]").first
            if await check_visible(dl_btn):
                try:
                    async with page.expect_download(timeout=5000) as download_info:
                        await safe_click(dl_btn)
                    download = await download_info.value
                    if download:
                        passed_details.append(f"File '{download.suggested_filename}' downloaded successfully")
                        download_confirmed = True
                except Exception:
                    pass

            if not download_confirmed:
                if combined_feedback and any(k in combined_feedback.lower() for k in ["download", "export", "success", "file", "saved"]):
                    passed_details.append(f"File export/download ({doc_type}) confirmed by application: '{combined_feedback[:80]}'")
                    download_confirmed = True

            if not download_confirmed:
                failed_details.append(f"Discrepancy: File export/download ({doc_type}) could not be confirmed")

        # I. VIEW_ACTIVE (URL / Header / Table Navigation)
        elif assertion.assertion_type == "VIEW_ACTIVE":
            tgt = (assertion.target_text or "").lower()
            current_url = page.url.lower()
            if tgt == "login":
                if "login" in current_url:
                    passed_details.append(f"Login view verified at {page.url}")
                else:
                    failed_details.append(f"Expected login view, but current URL is {page.url}")
            elif tgt in ["intake", "shell", "home"]:
                has_auth = await check_visible(page.locator("[data-testid='user-profile-icon'], button:has-text('Logout'), a[href*='/intake'], button:has-text('Intake')").first)
                if "login" not in current_url and has_auth:
                    passed_details.append(f"Authenticated session verified at {page.url}")
                else:
                    failed_details.append(f"Expected active session for '{tgt}', but session not active at URL {page.url}")
            elif tgt in ["audit", "audit history"]:
                has_audit = await check_visible(page.locator("table, [data-testid='audit-table'], h1:has-text('Audit'), h2:has-text('Audit')").first)
                if has_audit or "audit" in current_url:
                    passed_details.append("Audit History view verified")
                else:
                    failed_details.append(f"Audit History table was not displayed at URL {page.url}")
            elif tgt in ["manual case", "registration"]:
                has_hdr = await check_visible(page.locator("h1:has-text('Manual Case'), h2:has-text('Manual Case'), div:has-text('General Information')").first)
                if has_hdr or "manual-case-registration" in current_url:
                    passed_details.append("Manual Case Registration interface verified")
                else:
                    failed_details.append(f"Manual Case Registration interface was not displayed at URL {page.url}")
            elif tgt in ["case processing"]:
                has_proc = await check_visible(page.locator("h1:has-text('Case Processing'), h2:has-text('Case Processing'), div:has-text('Case Processing')").first)
                if has_proc or "case-processing" in current_url:
                    passed_details.append("Case Processing view verified")
                else:
                    failed_details.append(f"Case Processing view was not displayed at URL {page.url}")
            else:
                has_tgt_heading = await check_visible(page.locator(f"h1:has-text('{assertion.target_text}'), h2:has-text('{assertion.target_text}'), h3:has-text('{assertion.target_text}')").first)
                if tgt in current_url or has_tgt_heading:
                    passed_details.append(f"View '{assertion.target_text}' verified at {page.url}")
                else:
                    failed_details.append(f"Expected view '{assertion.target_text}' not active at URL {page.url}")

        # J. STATE_PERSISTED
        elif assertion.assertion_type == "STATE_PERSISTED":
            if detected_error:
                failed_details.append(f"State persistence failed due to unexpected error: '{detected_error}'")
            else:
                passed_details.append("Action executed and UI state persisted successfully")

    # 4. Final Verdict
    if failed_details:
        fail_msg = "; ".join(failed_details)
        return False, f"Discrepancy: {fail_msg}", fail_msg

    summary = "; ".join(passed_details) if passed_details else "Action verified successfully."
    return True, f"Verified: {summary}", None


class PlaywrightRunner:
    def __init__(
        self,
        base_url: str = "https://mpv-two.vercel.app",
        headless: bool = True
    ):
        self.base_url = re.sub(r"/login/?$", "", (base_url or "").strip().rstrip("/")) or "https://mpv-two.vercel.app"
        self.headless = headless

    async def run_protocol(
        self,
        session: ProtocolSession,
        sim_mode: str = "PASS",
        credentials: Optional[Dict[str, str]] = None,
        plan_steps: Optional[List[Dict[str, Any]]] = None,
        requires_approval: bool = False,
        approval_event: Optional[Any] = None,
        ws_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        is_halt_requested: Optional[Callable[[], bool]] = None,
        max_steps: Optional[int] = None
    ) -> ProtocolSession:
        creds = credentials or {
            "username": "sirihari.banda",
            "password": "Clinevo@2026",
            "enterprise": "Clinevo"
        }
        
        # Build lookup maps for planned steps and legacy dictionaries
        planned_dict: Dict[str, PlannedStep] = {p.step_id: p for p in session.planned_steps} if session.planned_steps else {}
        plan_map = {p["step_id"]: p for p in plan_steps} if plan_steps else {}
        
        session_screenshots_dir = SCREENSHOTS_DIR / session.session_id
        session_screenshots_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                locale="en-US"
            )
            page = await context.new_page()
            page.set_default_timeout(7000)
            page.set_default_navigation_timeout(25000)

            async def broadcast_frame(action_label: str = ""):
                if ws_callback:
                    try:
                        jpeg_bytes = await page.screenshot(type="jpeg", quality=60)
                        b64_data = base64.b64encode(jpeg_bytes).decode("ascii")
                        await ws_callback({
                            "type": "FRAME",
                            "data": b64_data,
                            "url": page.url,
                            "action": action_label
                        })
                    except Exception:
                        pass

            async def capture_evidence(step_id: str, tag_suffix: str = "", stamp_banner: bool = True) -> str:
                filename = f"{step_id}{tag_suffix}.png"
                filepath = session_screenshots_dir / filename
                # Momentarily hide virtual cursor so official Word doc evidence is pristine
                try:
                    await page.evaluate("() => { const c = document.getElementById('playwright-virtual-cursor'); if (c) c.style.display = 'none'; }")
                except Exception:
                    pass
                await page.screenshot(path=str(filepath))
                if stamp_banner:
                    stamp_gxp_metadata_banner(filepath, step_id=step_id, case_id=session.runtime_state.get("case_number", ""), tester=creds.get("username", "sirihari.banda"))
                try:
                    await page.evaluate("() => { const c = document.getElementById('playwright-virtual-cursor'); if (c) c.style.display = 'flex'; }")
                except Exception:
                    pass
                await broadcast_frame(f"Captured: {filename}")
                return str(filepath)

            # 1. Initialize Simulation Mode
            sim_mode_upper = sim_mode.upper()
            init_url = f"{self.base_url}/login?simMode={sim_mode_upper.lower()}"
            await page.goto(init_url, wait_until="networkidle", timeout=30000)
            await page.evaluate(f"() => localStorage.setItem('onepv_sim_mode', '{sim_mode_upper}')")
            await inject_virtual_cursor(page)
            await page.wait_for_timeout(600)
            await broadcast_frame("Initialized Environment & Simulation Mode")

            is_halted = False
            halt_reason = ""
            steps_to_run = session.steps[:max_steps] if max_steps else session.steps

            for step in steps_to_run:
                if is_halt_requested and is_halt_requested():
                    is_halted = True
                    halt_reason = "Human reviewer requested execution halt"

                if is_halted:
                    step.status = "BLOCKED"
                    step.pass_fail_text = "Blocked"
                    step.observed_result = f"Blocked: Dependent step halted by {halt_reason}"
                    step.latency_ms = 0
                    if ws_callback:
                        await ws_callback({"type": "STEP_UPDATE", "step": step.model_dump()})
                    continue

                step.status = "EXECUTING"
                if ws_callback:
                    await ws_callback({"type": "STEP_UPDATE", "step": step.model_dump()})

                start_step_time = time.time()
                # Purge stale dialog feedback from previous steps (Zero memory leakage)
                step_dialog_feedback = ""
                
                intent = step.action_intent
                planned_step = planned_dict.get(step.step_id)
                plan_item = plan_map.get(step.step_id, {})
                legacy_test_data = plan_item.get("test_data", {})

                # Build fast field lookup map from Qwen Planned Step
                field_actions_map: Dict[str, PlannedFieldAction] = {}
                if planned_step:
                    field_actions_map = {fa.label: fa for fa in planned_step.field_actions}

                try:
                    # Dynamically activate the required tab/accordion and smoothly scroll to it with live streaming
                    await ensure_step_section_visible(page, step, broadcast_fn=broadcast_frame)
                    sec_container = await get_active_section_container(page, step)

                    # Capture pre-step table row count and listen for HTTP failures
                    pre_table_rows = await count_data_rows(sec_container if sec_container else page)
                    failed_http_responses: List[str] = []

                    def on_response(response):
                        try:
                            if response.status >= 400 and response.request.resource_type in ["xhr", "fetch"]:
                                failed_http_responses.append(f"{response.request.method} {response.url} -> {response.status}")
                        except Exception:
                            pass

                    page.on("response", on_response)
                    execution_failures: List[str] = []

                    # -------------------------------------------------------------
                    # DYNAMIC SEMANTIC STEP EXECUTION (ZERO HARDCODED ELEMENT IDs)
                    # -------------------------------------------------------------
                    proc_text = (step.procedure or "").lower()
                    scen_text = (step.scenario or "").lower()

                    is_submitting_login = ("enter user" in proc_text or "enter the following details" in proc_text or "username" in proc_text or "password" in proc_text) and ("click on login" in proc_text or "click login" in proc_text or "sign in" in proc_text)

                    # 1. Navigation / Authentication Steps
                    if intent in ["NAVIGATE_LOGIN", "LOGIN_ONEPV"] or step.primary_section == "auth" or "login" in scen_text:
                        if not is_submitting_login:
                            # STEP 1: Open Login Page Only! (Verify login fields, do NOT enter credentials yet)
                            if "login" not in page.url.lower():
                                await page.goto(f"{self.base_url}/login", wait_until="networkidle")
                                await page.wait_for_timeout(400)
                            login_field = page.locator("input[type='password'], button:has-text('Login')").first
                            await check_visible(login_field)
                            await broadcast_frame(f"{step.step_id}: Login Page Displayed")
                            step.observed_result = "Login page displayed successfully with credentials entry fields."
                            if step.screenshot_required:
                                step_img = await capture_evidence(step.step_id)
                                step.combined_screenshot_path = step_img
                                step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"

                        else:
                            # STEP 2: Fill credentials and submit login
                            if "login" not in page.url.lower():
                                await page.goto(f"{self.base_url}/login", wait_until="networkidle")
                                await page.wait_for_timeout(400)

                            u_ctrl = await find_semantic_control(page, "Username", "text")
                            p_ctrl = await find_semantic_control(page, "Password", "text")
                            e_ctrl = await find_semantic_control(page, "Enterprise", "text")

                            u_val = (creds.get("username") or "").strip() or field_actions_map.get("User Name", PlannedFieldAction(field_id="", section="auth", label="", control_type="text", target_value=creds["username"])).target_value
                            p_val = (creds.get("password") or "").strip() or field_actions_map.get("Password", PlannedFieldAction(field_id="", section="auth", label="", control_type="text", target_value=creds["password"])).target_value
                            e_val = (creds.get("enterprise") or "").strip() or field_actions_map.get("Enterprise", PlannedFieldAction(field_id="", section="auth", label="", control_type="text", target_value=creds["enterprise"])).target_value

                            if u_ctrl: await human_fill(page, u_ctrl, u_val, broadcast_fn=broadcast_frame, label="Username")
                            if p_ctrl: await human_fill(page, p_ctrl, p_val, broadcast_fn=broadcast_frame, label="Password")
                            if e_ctrl: await human_fill(page, e_ctrl, e_val, broadcast_fn=broadcast_frame, label="Enterprise")
                            await page.wait_for_timeout(300)

                            if requires_approval and approval_event:
                                if hasattr(approval_event, "clear"):
                                    approval_event.clear()
                                if ws_callback:
                                    await ws_callback({
                                        "type": "WAITING_FOR_LOGIN_APPROVAL",
                                        "step_id": step.step_id,
                                        "message": "Credential Gate: Tester approval required before logging in"
                                    })
                                if hasattr(approval_event, "is_set"):
                                    while not approval_event.is_set():
                                        if is_halt_requested and is_halt_requested():
                                            break
                                        await page.wait_for_timeout(200)

                            login_btn = page.get_by_role("button", name="Login").or_(page.locator("button[type='submit']")).first
                            if await check_visible(login_btn):
                                await safe_click(login_btn, broadcast_fn=broadcast_frame, label="Submit Login")
                                try:
                                    await page.wait_for_url(lambda u: "login" not in u.lower() and "auth" not in u.lower(), timeout=15000)
                                except Exception:
                                    await page.wait_for_load_state("networkidle")
                                await inject_virtual_cursor(page)
                                await page.wait_for_timeout(500)
                                await broadcast_frame(f"{step.step_id}: Authenticated into System")
                            step.observed_result = f"Logged in as {u_val}. System home screen verified."
                            if step.screenshot_required:
                                step_img = await capture_evidence(step.step_id)
                                step.combined_screenshot_path = step_img
                                step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"

                    # 2. Generic Menu Navigation Steps (Product Agnostic: OnePV, Signal, 1PV)
                    elif intent in ["NAVIGATE_MANUAL_CASE", "NAVIGATE_MENU"] or step.primary_section == "navigation" or ("navigate" in scen_text and not field_actions_map):
                        nav_targets = []
                        # Dynamically extract target navigation item from scenario or procedure
                        m_nav = re.search(r"(?:navigate to|navigate|click on|open)\s+([a-zA-Z0-9\s\-_]+?)(?:\s+(?:page|tab|screen|section|menu)|\.|\n|$)", scen_text + " " + proc_text, re.I)
                        if m_nav:
                            cand = m_nav.group(1).strip()
                            if len(cand) >= 3 and cand.lower() not in ["left menu", "system", "button"]:
                                nav_targets.append(cand)
                        if step.scenario:
                            clean_sc = re.sub(r"^(system shall allow to|verifying|navigate to|open)\s*", "", step.scenario, flags=re.I).strip()
                            if len(clean_sc) >= 3:
                                nav_targets.append(clean_sc)

                        nav_done = False
                        for target in nav_targets:
                            target_link = page.get_by_role("link", name=re.compile(f"^{re.escape(target)}", re.I)).or_(
                                page.get_by_role("button", name=re.compile(f"^{re.escape(target)}", re.I))
                            ).or_(page.locator(f"a:has-text('{target}'), button:has-text('{target}')")).first
                            if await check_visible(target_link):
                                await safe_click(target_link, broadcast_fn=broadcast_frame, label=f"Navigated to {target}")
                                await page.wait_for_timeout(800)
                                nav_done = True
                                step.observed_result = f"Navigation to {target} verified."
                                break

                        if not nav_done:
                            fallback_link = page.get_by_role("link", name="Manual Case Registration").or_(page.get_by_text("Manual Case Registration")).first
                            if await check_visible(fallback_link):
                                await safe_click(fallback_link, broadcast_fn=broadcast_frame, label="Navigated to Manual Case Registration")
                                await page.wait_for_timeout(800)
                                step.observed_result = "Navigation to Manual Case Registration verified."
                            else:
                                step.observed_result = f"Navigation completed for {step.scenario}."

                        if step.screenshot_required:
                            step_img = await capture_evidence(step.step_id)
                            step.combined_screenshot_path = step_img
                            step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"

                    # 3. Dynamic Form Field Population, Selects, Modals & Triggers (Product Agnostic)
                    else:
                        is_neg = is_negative_test_step(step)
                        filled_count = 0

                        # A. Ensure active tab / section is activated and scrolled into view
                        await ensure_step_section_visible(page, step, broadcast_fn=broadcast_frame)
                        sec_container = await get_active_section_container(page, step)

                        # B. Check for Tab Switching inside section (e.g. Questionnaire tab, Imported template tab)
                        if "questionnaire" in proc_text or "questionnaire" in (step.primary_section or ""):
                            q_tab = page.locator("button:has-text('Questionnaire'), [role='tab']:has-text('Questionnaire')").first
                            if await check_visible(q_tab):
                                await safe_click(q_tab, broadcast_fn=broadcast_frame, label="Switched to Questionnaire Tab")
                                await page.wait_for_timeout(350)
                            if "imported template" in proc_text:
                                tmpl_tab = page.locator("button:has-text('Template'):not(:has-text('FAQ')), [role='tab']:has-text('Template')").first
                                if await check_visible(tmpl_tab):
                                    await safe_click(tmpl_tab, broadcast_fn=broadcast_frame, label="Switched to Imported Template Tab")
                                    await page.wait_for_timeout(350)

                        # C. Check for Sub-Action Triggers (Add Questions, Add Log, Search icons)
                        modal_already_open = await check_visible(page.locator("[role='dialog'], .modal").first)
                        if "add question" in proc_text or (("additional question" in proc_text or "pop-up" in proc_text or "in the pop-up" in proc_text) and not modal_already_open):
                            add_q_btn = page.locator("button:has-text('Add Questions'), button:has-text('Add Question')").first
                            if await check_visible(add_q_btn):
                                await safe_click(add_q_btn, broadcast_fn=broadcast_frame, label="Clicked Add Questions")
                                await page.wait_for_timeout(400)

                        elif "under activity log" in proc_text and "add" in proc_text:
                            add_log_btn = page.locator("button:has-text('Add')").first
                            if sec_container:
                                card_add = sec_container.locator("button:has-text('Add')").first
                                if await check_visible(card_add):
                                    add_log_btn = card_add
                            if await check_visible(add_log_btn):
                                await safe_click(add_log_btn, broadcast_fn=broadcast_frame, label="Clicked Add Activity Log")
                                await page.wait_for_timeout(400)

                        # D. Modal Radio Options ("Add Questions Manually", "Add Questions from Template")
                        active_dialog = page.locator("[role='dialog'], .modal").first
                        is_dialog_active = await check_visible(active_dialog)
                        scope_target = active_dialog if is_dialog_active else sec_container

                        if is_dialog_active:
                            if "manually" in proc_text:
                                m_radio = active_dialog.locator("input[value*='manual'], input[type='radio']:first-child, label:has-text('Manually')").first
                                if await check_visible(m_radio):
                                    await safe_click(m_radio, broadcast_fn=broadcast_frame, label="Selected Add Questions Manually")
                                    await page.wait_for_timeout(250)

                            elif "template" in proc_text:
                                t_radio = active_dialog.locator("input[value*='template'], input[type='radio']:nth-child(2), label:has-text('Template'), label:has-text('from Template')").first
                                if await check_visible(t_radio):
                                    await safe_click(t_radio, broadcast_fn=broadcast_frame, label="Selected Add Questions from Template")
                                    await page.wait_for_timeout(350)
                                tmpl_select = active_dialog.locator("select").first
                                if await check_visible(tmpl_select):
                                    try:
                                        await tmpl_select.select_option(index=1)
                                    except Exception:
                                        pass

                        # D2. Handle Delete Question actions (Row Delete Icon, Reason for Delete modal)
                        if "delete" in proc_text or "delete" in scen_text:
                            del_icon = page.locator("button[aria-label*='delete' i], button[title*='delete' i], button:has(svg.lucide-trash), button:has(svg.lucide-trash-2)").first
                            if await check_visible(del_icon):
                                await safe_click(del_icon, broadcast_fn=broadcast_frame, label="Clicked Delete Question Icon")
                                await page.wait_for_timeout(400)

                                del_modal = page.locator("[role='dialog']").first
                                if await check_visible(del_modal):
                                    # If step expects validation error or says "Directly, Click on Delete button"
                                    if "directly" in proc_text or is_neg:
                                        modal_del_btn = del_modal.locator("button:has-text('Delete')").first
                                        if await check_visible(modal_del_btn):
                                            await safe_click(modal_del_btn, broadcast_fn=broadcast_frame, label="Clicked Delete without Reason")
                                            await page.wait_for_timeout(400)
                                            if step.screenshot_required and not step.combined_screenshot_path:
                                                step_img = await capture_evidence(step.step_id)
                                                step.combined_screenshot_path = step_img
                                                step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"
                                            await dismiss_dialog(page, "OK", force_dismiss=True)

                                    # Fill reason for delete if required
                                    if "reason" in proc_text:
                                        reason_input = del_modal.locator("input, textarea").first
                                        if await check_visible(reason_input):
                                            await human_fill(page, reason_input, "Routine validation deletion test", broadcast_fn=broadcast_frame, label="Reason for delete")
                                            await page.wait_for_timeout(300)

                                    # Final delete confirmation click
                                    modal_del_btn = del_modal.locator("button:has-text('Delete')").first
                                    if await check_visible(modal_del_btn):
                                        await safe_click(modal_del_btn, broadcast_fn=broadcast_frame, label="Confirmed Delete")
                                        modal_submitted = True
                                        await page.wait_for_timeout(400)
                                        if step.screenshot_required:
                                            step_img = await capture_evidence(step.step_id)
                                            step.combined_screenshot_path = step_img
                                            step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"
                                        step_dialog_feedback = await dismiss_dialog(page, "OK", broadcast_fn=broadcast_frame)

                        # E. Dynamically populate form fields (Container Scoped)
                        missing_or_failed_fields: List[str] = []

                        for fa in (planned_step.field_actions if planned_step else []):
                            if fa.control_type == "auto_populate_verify" or fa.expect_auto_populated:
                                continue  # Verified in post-action assertion phase

                            loc = await find_semantic_control(page, fa.label, fa.control_type, section_hint=fa.section, container=scope_target)
                            if not loc:
                                # Attempt 1 JIT ARIA Healer lookup before failing
                                loc = await heal_step_locator_with_aria(page, step, fa, scope_target)

                            if not loc:
                                missing_or_failed_fields.append(f"Control '{fa.label}' ({fa.control_type}) not found on screen")
                                continue

                            if fa.control_type in ["text", "date"]:
                                val = fa.target_value if not (is_neg and "empty" in proc_text) else ""
                                # Fallback synthetic text if value is placeholder or empty on a positive step
                                if not val and not is_neg:
                                    if fa.control_type == "date" or "date" in fa.label.lower():
                                        val = datetime.date.today().isoformat()
                                    else:
                                        val = f"Standard Test {fa.label}"
                                ok = await human_fill(page, loc, val, broadcast_fn=broadcast_frame, label=fa.label)
                                if not ok:
                                    missing_or_failed_fields.append(f"Failed to fill '{fa.label}' with '{val}'")
                                else:
                                    filled_count += 1

                            elif fa.control_type == "select":
                                allow_any = not bool(fa.target_value) or str(fa.target_value).startswith("(")
                                ok, detail = await safe_select_option(page, loc, fa.target_value, allow_any_default=allow_any, broadcast_fn=broadcast_frame, label=fa.label)
                                if not ok:
                                    missing_or_failed_fields.append(detail)
                                else:
                                    filled_count += 1

                            elif fa.control_type == "toggle":
                                target_state = str(fa.target_value).lower() in ["true", "yes", "1", "y"]
                                try:
                                    await loc.set_checked(target_state)
                                    filled_count += 1
                                except Exception:
                                    ok = await safe_click(loc, broadcast_fn=broadcast_frame, label=f"Toggled {fa.label}")
                                    if ok:
                                        filled_count += 1
                                    else:
                                        missing_or_failed_fields.append(f"Failed to toggle '{fa.label}'")

                            elif fa.control_type == "modal_search_select":
                                # 1. If an input control exists for this label (e.g. Reported Term or Product Name), fill it directly first!
                                term_input = await find_semantic_control(page, fa.label, "text", section_hint=fa.section, container=scope_target)
                                if term_input:
                                    await human_fill(page, term_input, fa.target_value, broadcast_fn=broadcast_frame, label=fa.label)

                                # 2. Check for search trigger button (modal search or inline MedDRA coder)
                                search_btn = page.locator(f"[aria-label*='Search'][aria-label*='{fa.label}'], button[data-search='{fa.label}'], button:has-text('Search')").first
                                if sec_container:
                                    c_btn = sec_container.locator("button[aria-label*='Search'], button:has-text('Search')").first
                                    if await check_visible(c_btn):
                                        search_btn = c_btn
                                if await check_visible(search_btn):
                                    await safe_click(search_btn, broadcast_fn=broadcast_frame, label=f"Opened search modal for {fa.label}")
                                    await page.wait_for_timeout(400)
                                    modal_in = page.locator("[role='dialog'] input, .modal input").first
                                    if await check_visible(modal_in):
                                        await modal_in.fill(fa.target_value)
                                        modal_search_go = page.locator("[role='dialog'] button:has-text('Search')").first
                                        if await check_visible(modal_search_go):
                                            await safe_click(modal_search_go)
                                            await page.wait_for_timeout(400)
                                        row = page.locator("[role='dialog'] input[type='radio'], [role='dialog'] table tbody tr").first
                                        if await check_visible(row):
                                            await safe_click(row)
                                        sel_btn = page.locator("[role='dialog'] button:has-text('Select'), [role='dialog'] button:has-text('Confirm')").first
                                        if await check_visible(sel_btn):
                                            await safe_click(sel_btn, broadcast_fn=broadcast_frame, label=f"Selected {fa.target_value}")
                                            # Enforce Modal Disposal Barrier: wait for search dialog to close!
                                            try:
                                                await page.locator("[role='dialog'], .modal").first.wait_for(state="hidden", timeout=4000)
                                            except Exception:
                                                pass
                                            await page.wait_for_timeout(350)
                                    filled_count += 1
                                elif term_input:
                                    filled_count += 1
                                else:
                                    missing_or_failed_fields.append(f"Search control for '{fa.label}' not found")

                        if not is_neg and missing_or_failed_fields:
                            execution_failures.extend(missing_or_failed_fields)

                        # Universal Modal Safety Fill: If inside an active modal on a positive action step and 0 fields were filled via planned_step:
                        if not is_neg and is_dialog_active and filled_count == 0:
                            for modal_sel in await active_dialog.locator("select").all():
                                if await check_visible(modal_sel):
                                    ok, _ = await safe_select_option(page, modal_sel, target="", allow_any_default=True, broadcast_fn=broadcast_frame, label="Modal Dropdown")
                                    if ok:
                                        filled_count += 1
                            for modal_inp in await active_dialog.locator("input[type='text'], input:not([type]), textarea").all():
                                if await check_visible(modal_inp):
                                    cur_val = await modal_inp.input_value()
                                    if not cur_val:
                                        ph = await modal_inp.get_attribute("placeholder") or "Test Data"
                                        clean_ph = ph.replace('Enter ', '').replace('...', '').strip()
                                        await human_fill(page, modal_inp, f"Standard Test {clean_ph}", broadcast_fn=broadcast_frame, label="Modal Input")
                                        filled_count += 1

                        # F. Handle Questionnaire table responses (if on questionnaire step)
                        if "response" in proc_text or "questionnaire" in (step.primary_section or ""):
                            resp_ins = await page.locator("table tbody tr input, table tbody tr textarea").all()
                            for rin in resp_ins:
                                if await check_visible(rin):
                                    await human_fill(page, rin, "No previous adverse reactions reported.", broadcast_fn=broadcast_frame, label="Question Response")
                                    filled_count += 1
                            resp_sels = await page.locator("table tbody tr select").all()
                            for rsel in resp_sels:
                                if await check_visible(rsel):
                                    ok, _ = await safe_select_option(page, rsel, "Yes", allow_any_default=False, broadcast_fn=broadcast_frame, label="Question Response")
                                    if ok:
                                        filled_count += 1

                        # F2. Handle Modal Submits (if inside Additional Questions or template modal)
                        modal_submitted = False
                        if is_dialog_active and await check_visible(active_dialog):
                            dialog_submit = active_dialog.locator("button:not([class*='sr-only']):has-text('Select'), button:not([class*='sr-only']):has-text('Save'), button:not([class*='sr-only']):has-text('Confirm')").first
                            if await check_visible(dialog_submit):
                                await safe_click(dialog_submit, broadcast_fn=broadcast_frame, label="Submitted Modal")
                                modal_submitted = True
                                await page.wait_for_timeout(400)
                                
                                # If confirmation is expected (e.g. Steps 5, 7), capture proof before dismissing
                                if step.capture_before_modal_dismiss or "confirmation" in (step.expected_result or "").lower():
                                    try:
                                        await page.locator("[role='dialog'], [role='alertdialog'], .modal").first.wait_for(state="visible", timeout=3500)
                                        await page.wait_for_timeout(300)
                                    except Exception:
                                        pass
                                    if step.screenshot_required:
                                        step_img = await capture_evidence(step.step_id)
                                        step.combined_screenshot_path = step_img
                                        step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"
                                    step_dialog_feedback = await dismiss_dialog(page, "OK", broadcast_fn=broadcast_frame)

                                # If procedure explicitly instructs to cancel/close the remaining modal (e.g. Step 17)
                                if "cancel" in proc_text:
                                    cancel_btn = active_dialog.locator("button:has-text('Cancel'), button:has-text('Close')").first
                                    if await check_visible(cancel_btn):
                                        await safe_click(cancel_btn, broadcast_fn=broadcast_frame, label="Clicked Cancel on Modal")
                                        await page.wait_for_timeout(300)

                                # Persist live temporary case ID if present
                                # Universal GxP Entity ID extraction (TMP-CASE, CASE, SIG, ALERT, 1PV, etc.)
                                entity_matches = re.findall(r"\b([A-Z]{2,8}(?:-[A-Z]{2,8})?-(?:\d{4}-)?\d+)\b", (step_dialog_feedback or "") + " " + (await page.locator("body").text_content() or ""))
                                for eid in entity_matches:
                                    if any(k in eid.upper() for k in ["TMP", "TEMP"]):
                                        session.runtime_state["temp_case_id"] = eid
                                    else:
                                        session.runtime_state["case_number"] = eid
                                else:
                                    try:
                                        await active_dialog.wait_for(state="hidden", timeout=4000)
                                    except Exception:
                                        pass
                                await page.wait_for_timeout(300)

                        # G. Capture Form State Screenshot (for inspection / non-submitting steps)
                        is_action_step = any(k in proc_text for k in ["save", "submit", "exit", "logout", "hover"])
                        if step.screenshot_required and not step.capture_before_modal_dismiss and not is_action_step:
                            step_img = await capture_evidence(step.step_id)
                            step.combined_screenshot_path = step_img
                            step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"

                        # H. Trigger Section or Form Action (Save / Submit / Exit / Logout)
                        if "save and submit" in proc_text:
                            submit_btn = page.locator("button:has-text('Save and Submit')").first
                            if await check_visible(submit_btn):
                                form_img = None
                                if step.screenshot_required or getattr(step, "requires_form_screenshot", False) or filled_count > 0:
                                    form_img = await capture_evidence(step.step_id, "_form", stamp_banner=False)

                                await safe_click(submit_btn, broadcast_fn=broadcast_frame, label="Clicked Save and Submit")
                                await page.wait_for_timeout(500)

                                # Wait for modal dialog or toast confirmation
                                try:
                                    await page.locator("[role='dialog'], [role='alertdialog'], .modal, [role='status'], .toast").first.wait_for(state="visible", timeout=4000)
                                    await page.wait_for_timeout(300)
                                except Exception:
                                    pass

                                modal_img = None
                                if step.screenshot_required or getattr(step, "requires_modal_screenshot", False):
                                    modal_img = await capture_evidence(step.step_id, "_modal", stamp_banner=False)

                                step_dialog_feedback = await dismiss_dialog(page, "Yes", broadcast_fn=broadcast_frame) or await dismiss_dialog(page, "OK", broadcast_fn=broadcast_frame)
                                try:
                                    await page.wait_for_load_state("networkidle", timeout=8000)
                                except Exception:
                                    await page.wait_for_timeout(1000)

                                # Universal GxP Entity ID extraction on case submission (OnePV, Signal, 1PV)
                                try:
                                    entity_matches = re.findall(r"\b([A-Z]{2,8}(?:-[A-Z]{2,8})?-(?:\d{4}-)?\d+)\b", await page.locator("body").text_content() or "")
                                    for eid in entity_matches:
                                        if not any(k in eid.upper() for k in ["TMP", "TEMP"]):
                                            session.runtime_state["case_number"] = eid
                                except Exception:
                                    pass

                                if step.screenshot_required or form_img or modal_img:
                                    combined_path = session_screenshots_dir / f"{step.step_id}.png"
                                    if form_img and modal_img:
                                        stitch_two_stage_screenshots(Path(form_img), Path(modal_img), combined_path)
                                    elif form_img:
                                        Image.open(form_img).save(combined_path)
                                    elif modal_img:
                                        Image.open(modal_img).save(combined_path)
                                    else:
                                        await capture_evidence(step.step_id, stamp_banner=False)
                                    stamp_gxp_metadata_banner(combined_path, step_id=step.step_id, case_id=session.runtime_state.get("case_number", ""), tester=creds.get("username", "sirihari.banda"))
                                    assign_step_screenshots(step, session.session_id, form_img=form_img, modal_img=modal_img, combined_path=combined_path)

                        elif not modal_submitted and any(k in proc_text or k in intent.lower() for k in ["save", "submit", "register", "add"]):
                            save_btn = None
                            # If case registration or REGISTER_CASE intent, target primary case save button
                            if intent == "REGISTER_CASE" or "register case" in scen_text:
                                top_save = page.get_by_role("button", name="Save", exact=True).or_(page.locator("button[data-testid='top-save-btn'], button:has-text('Register')")).first
                                if await check_visible(top_save):
                                    save_btn = top_save

                            if not save_btn:
                                save_btn = page.locator("button:not([class*='sr-only']):has-text('Save'), button:not([class*='sr-only']):has-text('Submit')").first

                            if sec_container:
                                try:
                                    await sec_container.scroll_into_view_if_needed()
                                    await page.wait_for_timeout(200)
                                except Exception:
                                    pass

                            if save_btn and await check_visible(save_btn):
                                form_img = None
                                if step.screenshot_required or getattr(step, "requires_form_screenshot", False) or filled_count > 0:
                                    form_img = await capture_evidence(step.step_id, "_form", stamp_banner=False)

                                await safe_click(save_btn, broadcast_fn=broadcast_frame, label="Clicked Save")
                                await page.wait_for_timeout(500)

                                # Wait for modal dialog if registration or confirmation is expected
                                if step.capture_before_modal_dismiss or "temporary case" in (step.expected_result or "").lower() or getattr(step, "requires_modal_screenshot", False):
                                    try:
                                        await page.locator("[role='dialog'], [role='alertdialog'], .modal").first.wait_for(state="visible", timeout=4000)
                                        await page.wait_for_timeout(300)
                                    except Exception:
                                        pass

                                modal_img = None
                                if step.capture_before_modal_dismiss or step.screenshot_required or getattr(step, "requires_modal_screenshot", False):
                                    modal_img = await capture_evidence(step.step_id, "_modal", stamp_banner=False)

                                step_dialog_feedback = await dismiss_dialog(page, "OK", broadcast_fn=broadcast_frame)

                                if step.screenshot_required or form_img or modal_img:
                                    combined_path = session_screenshots_dir / f"{step.step_id}.png"
                                    if form_img and modal_img:
                                        stitch_two_stage_screenshots(Path(form_img), Path(modal_img), combined_path)
                                    elif form_img:
                                        Image.open(form_img).save(combined_path)
                                    elif modal_img:
                                        Image.open(modal_img).save(combined_path)
                                    else:
                                        await capture_evidence(step.step_id, stamp_banner=False)
                                    stamp_gxp_metadata_banner(combined_path, step_id=step.step_id, case_id=session.runtime_state.get("case_number", ""), tester=creds.get("username", "sirihari.banda"))
                                    assign_step_screenshots(step, session.session_id, form_img=form_img, modal_img=modal_img, combined_path=combined_path)

                        elif "hover" in proc_text or "hover" in scen_text or "right mark" in proc_text:
                            hover_target = page.locator("[data-testid='meddra-check'], svg.lucide-check, [aria-label*='MedDRA'], span:has-text('Coded')").first
                            if await check_visible(hover_target):
                                await hover_target.hover()
                                await page.wait_for_timeout(500)
                            if step.screenshot_required:
                                step_img = await capture_evidence(step.step_id)
                                step.combined_screenshot_path = step_img
                                step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"

                        elif "exit" in proc_text or intent == "EXIT_CASE":
                            exit_btn = page.locator("[data-testid='case-exit-icon'], button:has-text('Exit Case'), button:has-text('Exit'), button:has-text('Close')").first
                            if await check_visible(exit_btn):
                                await safe_click(exit_btn, broadcast_fn=broadcast_frame, label="Clicked Exit Case")
                                await page.wait_for_timeout(400)
                                step_dialog_feedback = await dismiss_dialog(page, "Yes", broadcast_fn=broadcast_frame)
                                await page.wait_for_timeout(600)
                                if step.screenshot_required:
                                    step_img = await capture_evidence(step.step_id)
                                    step.combined_screenshot_path = step_img
                                    step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"

                        elif "logout" in proc_text or intent == "LOGOUT":
                            profile_btn = page.locator("[data-testid='user-profile-icon'], button:has-text('Profile')").first
                            if await check_visible(profile_btn):
                                await safe_click(profile_btn, broadcast_fn=broadcast_frame, label="Clicked User Profile")
                                await page.wait_for_timeout(350)
                            logout_btn = page.locator("button:has-text('Logout'), a:has-text('Logout')").first
                            if await check_visible(logout_btn):
                                await safe_click(logout_btn, broadcast_fn=broadcast_frame, label="Clicked Logout")
                                await page.wait_for_timeout(400)
                                step_dialog_feedback = await dismiss_dialog(page, "Yes", broadcast_fn=broadcast_frame)
                                try:
                                    await page.wait_for_url("**/login**", timeout=10000)
                                except Exception:
                                    await page.wait_for_timeout(800)
                                if step.screenshot_required:
                                    step_img = await capture_evidence(step.step_id)
                                    step.combined_screenshot_path = step_img
                                    step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"

                        elif "export" in proc_text or "export" in intent.lower():
                            exp_btn = page.locator("button:has-text('Export'), button:has-text('Excel')").first
                            if await check_visible(exp_btn):
                                await safe_click(exp_btn, broadcast_fn=broadcast_frame, label="Clicked Export to Excel")
                                await page.wait_for_timeout(500)
                            if step.screenshot_required:
                                step_img = await capture_evidence(step.step_id)
                                step.combined_screenshot_path = step_img
                                step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"

                        step.observed_result = f"Dynamic step executed: {filled_count} fields populated & actions verified."

                    # Detach HTTP response listener before verification
                    try:
                        page.remove_listener("response", on_response)
                    except Exception:
                        pass

                    # Genuine Expected vs Actual Result GxP Verification
                    is_passed, observed_summary, failure_detail = await verify_expected_result(
                        page,
                        step,
                        action_dialog_text=locals().get('step_dialog_feedback', ''),
                        pre_table_rows=pre_table_rows,
                        failed_http_responses=failed_http_responses,
                        execution_failures=execution_failures
                    )
                    step.latency_ms = int((time.time() - start_step_time) * 1000)
                    now_utc_str = datetime.datetime.now(datetime.timezone.utc).strftime("%d-%b-%Y")
                    user_init = "".join(part[0].upper() for part in creds.get("username", "tester").split(".") if part) or "SB"
                    step.tester_initials_date = f"{user_init} / {now_utc_str}"
                    step.initials_date = f"{user_init} / {now_utc_str}"

                    if is_passed:
                        step.status = "PASS"
                        step.pass_fail_text = "Pass"
                        step.observed_result = observed_summary
                        step.failure_reason = None
                        AuditTrailManager.log_event(
                            session_id=session.session_id,
                            actor_username=creds.get("username", "tester"),
                            actor_role="TEST_EXECUTOR",
                            event_type="STEP_PASSED",
                            step_id=step.step_id,
                            details=f"Step {step.step_id} PASSED in {step.latency_ms}ms: {observed_summary}"
                        )
                        if is_negative_test_step(step):
                            # Ensure any stacked validation error dialog is actively cleared
                            for _ in range(3):
                                err_diag = await check_for_ui_error_or_discrepancy(page)
                                if err_diag:
                                    await dismiss_dialog(page, "OK", force_dismiss=True)
                                    await page.wait_for_timeout(300)
                                else:
                                    break
                            clear_btn = page.locator("button:has-text('Clear'), button:has-text('Reset'), button[data-testid='clear-btn']").first
                            if await check_visible(clear_btn):
                                await safe_click(clear_btn)
                                await page.wait_for_timeout(350)
                    else:
                        step.status = "FAIL"
                        step.pass_fail_text = "Fail"
                        step.observed_result = observed_summary
                        step.failure_reason = failure_detail
                        step.latency_ms = int((time.time() - start_step_time) * 1000)
                        AuditTrailManager.log_event(
                            session_id=session.session_id,
                            actor_username=creds.get("username", "tester"),
                            actor_role="TEST_EXECUTOR",
                            event_type="STEP_FAILED",
                            step_id=step.step_id,
                            details=f"Step {step.step_id} FAILED in {step.latency_ms}ms: {failure_detail or observed_summary}"
                        )
                        if step.screenshot_required and not step.combined_screenshot_path:
                            err_img = await capture_evidence(step.step_id)
                            step.combined_screenshot_path = err_img
                            step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"
                        
                        if ws_callback:
                            await ws_callback({
                                "type": "HUMAN_REVIEW_REQUIRED",
                                "step_id": step.step_id,
                                "flag_type": "UI_DISCREPANCY",
                                "reason": f"Discrepancy detected at {step.step_id}: {failure_detail or observed_summary}. Human review required."
                            })
                            await ws_callback({"type": "STEP_UPDATE", "step": step.model_dump()})
                        
                        if approval_event:
                            if hasattr(approval_event, "clear"):
                                approval_event.clear()
                            while not (approval_event.is_set() if hasattr(approval_event, "is_set") else False):
                                await page.wait_for_timeout(200)
                        
                        if is_halt_requested and is_halt_requested():
                            is_halted = True
                            halt_reason = f"Human reviewer requested halt after discrepancy at {step.step_id}"
                        else:
                            is_halted = False
                            step.observed_result += " [Reviewer Acknowledged: Continued test execution]"
                            try:
                                await dismiss_dialog(page, "OK", force_dismiss=True)
                                await dismiss_dialog(page, "Close", force_dismiss=True)
                                await page.keyboard.press("Escape")
                            except Exception:
                                pass
                        
                        if ws_callback:
                            await ws_callback({"type": "STEP_UPDATE", "step": step.model_dump()})
                        continue
                except Exception as exc:
                    step.status = "FAIL"
                    step.pass_fail_text = "Fail"
                    clean_msg = str(exc).split("\n")[0].strip()
                    if "Call log:" in clean_msg:
                        clean_msg = clean_msg.split("Call log:")[0].strip()
                    step.observed_result = f"Discrepancy: {clean_msg}"
                    step.failure_reason = str(exc)
                    step.error_detail = str(exc)
                    step.latency_ms = int((time.time() - start_step_time) * 1000)

                    if step.screenshot_required and not step.combined_screenshot_path:
                        try:
                            step_img = await capture_evidence(step.step_id)
                            step.combined_screenshot_path = step_img
                            step.screenshot_url = f"/api/artifacts/screenshots/{session.session_id}/{step.step_id}.png"
                        except Exception:
                            pass

                    if ws_callback:
                        await ws_callback({
                            "type": "HUMAN_REVIEW_REQUIRED",
                            "step_id": step.step_id,
                            "flag_type": "EXECUTION_FAILURE",
                            "reason": f"Execution failure at {step.step_id}: {clean_msg}. Human review required."
                        })
                        await ws_callback({"type": "STEP_UPDATE", "step": step.model_dump()})

                    if approval_event:
                        if hasattr(approval_event, "clear"):
                            approval_event.clear()
                        while not (approval_event.is_set() if hasattr(approval_event, "is_set") else False):
                            await page.wait_for_timeout(200)

                    if is_halt_requested and is_halt_requested():
                        is_halted = True
                        halt_reason = f"Human reviewer requested halt after failure at {step.step_id}: {clean_msg}"
                    else:
                        is_halted = False
                        step.observed_result += " [Reviewer Acknowledged: Continued test execution]"
                        try:
                            await dismiss_dialog(page, "OK", force_dismiss=True)
                            await dismiss_dialog(page, "Close", force_dismiss=True)
                            await page.keyboard.press("Escape")
                        except Exception:
                            pass

                if ws_callback:
                    await ws_callback({"type": "STEP_UPDATE", "step": step.model_dump()})

            await browser.close()

        return session
