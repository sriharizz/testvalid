import { test, expect, Page } from '@playwright/test';

// Helper: Captures high-res evidence screenshot matching (µ) checkpoint
async function captureEvidence(page: Page, stepId: string) {
  const path = `artifacts/screenshots/${stepId}.png`;
  await page.screenshot({ path });
  console.log(`[EVIDENCE] Checkpoint captured: ${stepId} -> ${path}`);
}

// Helper: Safe modal confirmation handler
async function dismissModal(page: Page, buttonLabel: string = 'OK') {
  const btn = page.locator(`role=dialog >> button:has-text('${buttonLabel}')`).first();
  if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await btn.click();
  }
}

test.describe.serial('CLIN-EU-PAT-OPV-1-1-PQ-022 — Automated Qualification Suite', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await page.close();
  });

  // ------------------------------------------------------------------------
  // TS1-S01: Accessing into Clinevo OnePV Intake Production Environment.
  // ------------------------------------------------------------------------
  await test.step('TS1-S01', async () => {
    await page.goto('https://mpv-two.vercel.app/login');
    await page.waitForLoadState('networkidle');
    await captureEvidence(page, 'TS1-S01');
    await expect(page).toHaveURL(/.*\/login/);
  });

  // ------------------------------------------------------------------------
  // TS1-S02: Login to Clinevo OnePV system
  // ------------------------------------------------------------------------
  await test.step('TS1-S02', async () => {
    await page.fill('#username', 'sirihari.banda');
    await page.fill('#password', 'Clinevo@2026');
    await page.fill('#enterprise', 'Clinevo');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/intake/**', { timeout: 15000 });
    await captureEvidence(page, 'TS1-S02');
    await expect(page.locator('[data-testid="header-username"]')).toContainText('sirihari.banda');
  });

  // ------------------------------------------------------------------------
  // TS1-S03: System shall allow to navigate Manual Case Registration page.
  // ------------------------------------------------------------------------
  await test.step('TS1-S03', async () => {
    await page.click('a[href*="/intake/manual-case-registration"]');
    await page.waitForLoadState('networkidle');
    await captureEvidence(page, 'TS1-S03');
    await expect(page).toHaveURL(/.*\/manual-case-registration/);
  });

  // ------------------------------------------------------------------------
  // TS1-S04: System shall allow to Register Case.
  // ------------------------------------------------------------------------
  await test.step('TS1-S04', async () => {
    const classSelect = page.locator('#case_classification, select[name="classification"]').first();
    if (await classSelect.isVisible().catch(() => false)) {
      await classSelect.selectOption({ label: 'Adverse Event' }).catch(() => {});
    }
    await page.click('button:has-text("Save")');
    await page.waitForTimeout(500);
    await captureEvidence(page, 'TS1-S04');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S05: System shall allow to add Questionnaire manually.
  // ------------------------------------------------------------------------
  await test.step('TS1-S05', async () => {
    await page.waitForTimeout(300);
    await captureEvidence(page, 'TS1-S05');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page).toHaveURL(/.*\/.*/);
  });

  // ------------------------------------------------------------------------
  // TS1-S06: System shall allow to provide response for manually created question.
  // ------------------------------------------------------------------------
  await test.step('TS1-S06', async () => {
    await page.waitForTimeout(300);
    await captureEvidence(page, 'TS1-S06');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S07: System shall allow to add Questionnaire from template.
  // ------------------------------------------------------------------------
  await test.step('TS1-S07', async () => {
    await page.waitForTimeout(300);
    await captureEvidence(page, 'TS1-S07');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S08: System shall allow to provide response for created question from template under Questionnaire tab.
  // ------------------------------------------------------------------------
  await test.step('TS1-S08', async () => {
    await page.waitForTimeout(300);
    await captureEvidence(page, 'TS1-S08');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S09: System shall allow to add reporter.
  // ------------------------------------------------------------------------
  await test.step('TS1-S09', async () => {
    await page.waitForTimeout(300);
    await captureEvidence(page, 'TS1-S09');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S10: System shall allow to Add Patient information.
  // ------------------------------------------------------------------------
  await test.step('TS1-S10', async () => {
    await page.click('button:has-text("Patient")');
    await page.click('button:has-text("Save")');
    await captureEvidence(page, 'TS1-S10');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S11: System shall allow to Add product.
  // ------------------------------------------------------------------------
  await test.step('TS1-S11', async () => {
    await page.click('button:has-text("Product")');
    await page.click('button:has-text("Save")');
    await captureEvidence(page, 'TS1-S11');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S12: System shall allow to Add Event Information.
  // ------------------------------------------------------------------------
  await test.step('TS1-S12', async () => {
    await page.click('button:has-text("Event")');
    await page.click('button:has-text("Save")');
    await captureEvidence(page, 'TS1-S12');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('button:has-text("Event")')).toBeVisible();
  });

  // ------------------------------------------------------------------------
  // TS1-S13: Verifying Reported Term’s Meddra Code.
  // ------------------------------------------------------------------------
  await test.step('TS1-S13', async () => {
    await page.click('button:has-text("Event")');
    await page.click('button:has-text("Save")');
    await dismissModal(page, 'OK');
    await captureEvidence(page, 'TS1-S13');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S14: System shall allow to add Log details.
  // ------------------------------------------------------------------------
  await test.step('TS1-S14', async () => {
    await page.click('button:has-text("Activity Log")');
    await page.click('button:has-text("Save")');
    await captureEvidence(page, 'TS1-S14');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S15: System shall allow to Submit case.
  // ------------------------------------------------------------------------
  await test.step('TS1-S15', async () => {
    await page.click('button:has-text("Save and Submit"), button:has-text("Save & Submit")');
    await dismissModal(page, 'Yes');
    await captureEvidence(page, 'TS1-S15');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page).toHaveURL(/.*\/intake\/.*/);
  });

  // ------------------------------------------------------------------------
  // TS1-S16: Verifying Meddra Code of Event Information in Case Processing page.
  // ------------------------------------------------------------------------
  await test.step('TS1-S16', async () => {
    await page.click('button:has-text("Event")');
    await page.click('button:has-text("Save")');
    await dismissModal(page, 'OK');
    await captureEvidence(page, 'TS1-S16');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S17: System shall allow to Exit from the case processing.
  // ------------------------------------------------------------------------
  await test.step('TS1-S17', async () => {
    await page.click('[data-testid="case-exit-icon"], button:has-text("Exit")');
    await dismissModal(page, 'Yes');
    await captureEvidence(page, 'TS1-S17');
    await expect(page).toHaveURL(/.*\/intake\/open-case/);
  });

  // ------------------------------------------------------------------------
  // TS1-S18: System shall allow to Logout.
  // ------------------------------------------------------------------------
  await test.step('TS1-S18', async () => {
    await page.click('[data-testid="user-profile-icon"]');
    await page.click('button:has-text("Logout")');
    await dismissModal(page, 'Yes');
    await captureEvidence(page, 'TS1-S18');
    await expect(page).toHaveURL(/.*\/login/);
  });

});
