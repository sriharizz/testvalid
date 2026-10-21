import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://mpv-two.vercel.app/login", wait_until="networkidle")
            await page.fill("#username", "sirihari.banda")
            await page.fill("#password", "Clinevo@2026")
            await page.fill("#enterprise", "Clinevo")
            await page.click("button[type='submit']")
            await page.wait_for_url("**/intake/**", timeout=20000)
            
            # Select classification & fill fields
            await page.select_option("#caseClassificationCode", label="Adverse Event")
            await page.select_option("#caseIntakeSourceCode", label="Spontaneous")
            await page.fill("#companyReceiptDate", "2026-10-14")
            await page.fill("#processingCenterReceivedDate", "2026-10-14")
            await page.fill("#reporterFirstName", "John")
            await page.fill("#reporterLastName", "Doe")
            await page.select_option("#countryCode", index=1)
            
            # Click Save
            save_btn = page.locator("button[data-testid='top-save-btn'], button:has-text('Save')").first
            await save_btn.click()
            await page.wait_for_timeout(1000)
            
            # Take screenshot of saved state
            await page.screenshot(path="artifacts/screenshots/test_saved_case.png")
            print("Saved screenshot to artifacts/screenshots/test_saved_case.png")
            
            # Check for any alerts, modals or dialogs
            modal_text = await page.locator(".modal, [role='dialog'], .swal2-popup, .toast, .chakra-modal__content, div:has-text('Success'), div:has-text('saved'), div:has-text('Case')").all_text_contents()
            print("Potential modal texts:", [t.strip().replace('\n', ' ') for t in modal_text if t.strip()][:5])
            
        except Exception as e:
            print("Error:", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
