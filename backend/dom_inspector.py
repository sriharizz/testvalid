import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "https://mpv-two.vercel.app"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = ARTIFACTS_DIR / "dom_map.json"

async def inspect_element_collection(page, selector):
    elements = await page.query_selector_all(selector)
    results = []
    for el in elements:
        try:
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            el_id = await el.get_attribute("id") or ""
            name = await el.get_attribute("name") or ""
            placeholder = await el.get_attribute("placeholder") or ""
            data_testid = await el.get_attribute("data-testid") or ""
            el_type = await el.get_attribute("type") or ""
            role = await el.get_attribute("role") or ""
            aria_label = await el.get_attribute("aria-label") or ""
            text = (await el.inner_text()).strip() if tag in ["button", "a", "span", "h1", "h2", "h3", "h4", "label"] else ""
            
            # Find associated label text if applicable
            label_text = ""
            if el_id:
                label_el = await page.query_selector(f"label[for='{el_id}']")
                if label_el:
                    label_text = (await label_el.inner_text()).strip()

            results.append({
                "tag": tag,
                "id": el_id,
                "name": name,
                "type": el_type,
                "placeholder": placeholder,
                "data_testid": data_testid,
                "role": role,
                "aria_label": aria_label,
                "text": text[:60] if text else "",
                "label": label_text[:60] if label_text else ""
            })
        except Exception:
            continue
    return results

async def main():
    print(f"[*] Starting Live DOM Inspection against {BASE_URL}/login ...")
    dom_map = {
        "target_url": BASE_URL,
        "discovered_at": None,
        "login_page": {},
        "header_shell": {},
        "sidebar_nav": {},
        "manual_case_registration": {},
        "open_case": {},
        "audit_history": {},
        "modals": {}
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 768})
        page = await context.new_page()

        # 1. Login Page Inspection
        print("[1/5] Navigating to /login ...")
        await page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1000)

        login_inputs = await inspect_element_collection(page, "input, select, textarea")
        login_buttons = await inspect_element_collection(page, "button, a")
        dom_map["login_page"] = {
            "inputs": login_inputs,
            "buttons": login_buttons,
            "key_selectors": {
                "username_input": "#username",
                "password_input": "#password",
                "enterprise_input": "#enterprise",
                "login_button": "button[type='submit']",
                "simulation_bar": "[data-testid='simulation-control-bar']"
            }
        }
        print(f"    Discovered {len(login_inputs)} inputs and {len(login_buttons)} buttons/links on Login Page.")

        # 2. Perform Login with sirihari.banda / Clinevo@2026 / Clinevo
        print("[2/5] Executing login to inspect authenticated shell ...")
        await page.fill("#username", "sirihari.banda")
        await page.fill("#password", "Clinevo@2026")
        await page.fill("#enterprise", "Clinevo")
        await page.click("button[type='submit']")
        await page.wait_for_url("**/intake/**", timeout=15000)
        await page.wait_for_timeout(1500)

        # 3. Inspect Header & Shell
        header_username = await page.query_selector("[data-testid='header-username']")
        header_timestamp = await page.query_selector("[data-testid='header-timestamp']")
        case_exit = await page.query_selector("[data-testid='case-exit-icon']")
        user_profile = await page.query_selector("[data-testid='user-profile-icon']")
        sim_bar = await page.query_selector("[data-testid='simulation-control-bar']")

        dom_map["header_shell"] = {
            "header_username_selector": "[data-testid='header-username']",
            "header_username_found": bool(header_username),
            "header_timestamp_selector": "[data-testid='header-timestamp']",
            "header_timestamp_found": bool(header_timestamp),
            "case_exit_selector": "[data-testid='case-exit-icon']",
            "case_exit_found": bool(case_exit),
            "user_profile_selector": "[data-testid='user-profile-icon']",
            "user_profile_found": bool(user_profile),
            "simulation_bar_selector": "[data-testid='simulation-control-bar']",
            "simulation_bar_found": bool(sim_bar)
        }
        print(f"    Header selectors verified: username={bool(header_username)}, timestamp={bool(header_timestamp)}, exit={bool(case_exit)}")

        # Inspect Sidebar
        sidebar_links = await inspect_element_collection(page, "aside nav a, aside nav button")
        dom_map["sidebar_nav"] = {
            "links": sidebar_links,
            "key_selectors": {
                "manual_case_link": "a[href*='/intake/manual-case-registration']",
                "open_case_link": "a[href*='/intake/open-case']",
                "audit_history_link": "a[href*='/reports/audit-history']"
            }
        }
        print(f"    Sidebar discovered: {len(sidebar_links)} navigation elements.")

        # 4. Inspect Manual Case Registration Page
        print("[3/5] Inspecting /intake/manual-case-registration ...")
        current_url = page.url
        if "/manual-case-registration" not in current_url:
            await page.goto(f"{BASE_URL}/intake/manual-case-registration", wait_until="networkidle")
            await page.wait_for_timeout(1000)

        mcr_inputs = await inspect_element_collection(page, "input, select, textarea")
        mcr_buttons = await inspect_element_collection(page, "button")
        mcr_sections = await inspect_element_collection(page, "h2, h3, h4, [role='tab']")

        dom_map["manual_case_registration"] = {
            "url": page.url,
            "inputs": mcr_inputs,
            "buttons": mcr_buttons,
            "sections": mcr_sections,
            "key_selectors": {
                "case_classification": "#case_classification, select[name='classification'], select[name='caseClassification']",
                "case_description": "#case_description, textarea[name='description']",
                "save_button": "button:has-text('Save'), button:text-is('Save')",
                "submit_button": "button:has-text('Submit'), button:text-is('Submit')",
                "save_and_submit_button": "button:has-text('Save and Submit'), button:has-text('Save & Submit')",
                "reset_button": "button:has-text('Reset')",
                "activity_log_tab": "button:has-text('Activity Log')",
                "patient_tab": "button:has-text('Patient')",
                "product_tab": "button:has-text('Product')",
                "event_tab": "button:has-text('Event')",
                "reporter_tab": "button:has-text('Reporter')"
            }
        }
        print(f"    Manual Case Registration: {len(mcr_inputs)} inputs, {len(mcr_buttons)} buttons.")

        # 5. Inspect Open Case Page
        print("[4/5] Inspecting /intake/open-case ...")
        await page.goto(f"{BASE_URL}/intake/open-case", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        oc_inputs = await inspect_element_collection(page, "input, select, textarea")
        oc_buttons = await inspect_element_collection(page, "button, a")
        dom_map["open_case"] = {
            "url": page.url,
            "inputs": oc_inputs,
            "buttons": oc_buttons,
            "key_selectors": {
                "search_input": "input[type='search'], input[placeholder*='Search']",
                "case_table": "table, [role='table']",
                "case_rows": "table tbody tr, [role='row']"
            }
        }
        print(f"    Open Case: {len(oc_inputs)} inputs, {len(oc_buttons)} buttons/links.")

        # 6. Inspect Audit History Page
        print("[5/5] Inspecting /reports/audit-history ...")
        await page.goto(f"{BASE_URL}/reports/audit-history", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        ah_inputs = await inspect_element_collection(page, "input, select, textarea")
        ah_buttons = await inspect_element_collection(page, "button, a")
        dom_map["audit_history"] = {
            "url": page.url,
            "inputs": ah_inputs,
            "buttons": ah_buttons,
            "key_selectors": {
                "search_input": "input[placeholder*='Search']",
                "export_button": "button:has-text('Export'), button:has-text('Excel')",
                "history_table": "table, [role='table']"
            }
        }
        print(f"    Audit History: {len(ah_inputs)} inputs, {len(ah_buttons)} buttons/links.")

        # Record simulation mode storage key
        sim_key = await page.evaluate("() => localStorage.getItem('onepv_sim_mode')")
        dom_map["simulation_mode"] = {
            "storage_key": "onepv_sim_mode",
            "url_query_param": "simMode",
            "current_mode": sim_key or "PASS",
            "supported_modes": ["PASS", "FAIL", "BLOCKED"]
        }

        # Timestamp
        import datetime
        dom_map["discovered_at"] = datetime.datetime.now().isoformat()

        # Save to JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dom_map, f, indent=2)

        print(f"[OK] Live DOM map successfully saved to {OUTPUT_FILE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
