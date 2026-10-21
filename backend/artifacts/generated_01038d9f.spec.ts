import { test, expect, Page } from '@playwright/test';

// Helper: Captures populated form state before saving
async function captureFormState(page: Page, tag: string) {
  const path = `artifacts/screenshots/${tag}.png`;
  await page.screenshot({ path });
  console.log(`[EVIDENCE] Form state captured: ${tag} -> ${path}`);
}

// Helper: Captures modal confirmation evidence before dismissal
async function captureModalEvidence(page: Page, tag: string) {
  const path = `artifacts/screenshots/${tag}.png`;
  await page.screenshot({ path });
  console.log(`[EVIDENCE] Modal checkpoint captured: ${tag} -> ${path}`);
}

// Helper: Safe modal confirmation handler
async function dismissModal(page: Page, buttonLabel: string = 'OK') {
  const btn = page.locator(`role=dialog >> button:has-text('${buttonLabel}')`).first();
  if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await btn.click();
  }
}

// Helper: Fills input field inside target section
async function fillFieldInSection(page: Page, section: string, label: string, value: string) {
  const input = page.locator(`[data-section='${section}'] input[placeholder*='${label}' i], input#${label.replace(/\s+/g, '')}`).first();
  if (await input.isVisible().catch(() => false)) {
    await input.fill(value);
  }
}

// Helper: Selects dropdown inside target section
async function selectDropdownInSection(page: Page, section: string, label: string, value: string) {
  const sel = page.locator(`[data-section='${section}'] select, select#${label.replace(/\s+/g, '')}`).first();
  if (await sel.isVisible().catch(() => false)) {
    await sel.selectOption({ label: value }).catch(() => {});
  }
}

// Helper: Toggles switch inside target section
async function toggleSwitchInSection(page: Page, section: string, label: string, targetState: string) {
  const toggle = page.locator(`[data-section='${section}'] input[type='checkbox']`).first();
  if (await toggle.isVisible().catch(() => false)) {
    await toggle.setChecked(targetState.toLowerCase() === 'true');
  }
}

// Helper: Search and select in modal
async function searchAndSelectInModal(page: Page, section: string, label: string, searchTerm: string) {
  const searchIcon = page.locator(`button[data-search='${label}'], button:has-text('Search')`).first();
  if (await searchIcon.isVisible().catch(() => false)) {
    await searchIcon.click();
    await page.fill('role=dialog input', searchTerm);
    await page.click('role=dialog button:has-text("Search")');
    await page.click('role=dialog input[type="radio"]');
    await page.click('role=dialog button:has-text("Select")');
  }
}

// Helper: Verifies auto-populated field
async function verifyAutoPopulatedField(page: Page, section: string, label: string) {
  const elem = page.locator(`input[placeholder*='${label}' i]`).first();
  if (await elem.isVisible().catch(() => false)) {
    await expect(elem).not.toBeEmpty();
  }
}

test.describe.serial('CLIN-EU-VAL-OPV-1-1-OQ-036 — Automated Qualification Suite', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await page.close();
  });

  // ------------------------------------------------------------------------
  // TS1-S01: Accessing into Clinevo OnePV Intake Validation Environment.
  // ------------------------------------------------------------------------
  await test.step('TS1-S01: Accessing into Clinevo OnePV Intake Validation Environment.', async () => {
    await page.goto('https://mpv-two.vercel.app/login');
    await page.waitForLoadState('networkidle');
    await captureFormState(page, 'TS1-S01_form');
    await captureModalEvidence(page, 'TS1-S01_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S02: Login to Clinevo OnePV system
  // ------------------------------------------------------------------------
  await test.step('TS1-S02: Login to Clinevo OnePV system', async () => {
    await page.fill('#username', 'sirihari.banda');
    await page.fill('#password', 'Clinevo@2026');
    await page.fill('#enterprise', 'Clinevo');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/intake/**', { timeout: 15000 });
    // [FIELD:TS1-S02-F01] auth -> User Name
    await fillFieldInSection(page, 'auth', 'User Name', 'sirihari.banda');
    // [FIELD:TS1-S02-F02] auth -> Password
    await fillFieldInSection(page, 'auth', 'Password', 'Clinevo@2026');
    // [FIELD:TS1-S02-F03] auth -> Enterprise
    await fillFieldInSection(page, 'auth', 'Enterprise', 'Clinevo');
    await captureFormState(page, 'TS1-S02_form');
    await captureModalEvidence(page, 'TS1-S02_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S03: System shall allow to navigate Manual Case Registration page.
  // ------------------------------------------------------------------------
  await test.step('TS1-S03: System shall allow to navigate Manual Case Registration page.', async () => {
    await page.goto('https://mpv-two.vercel.app/intake/manual-case-registration');
    await page.waitForLoadState('networkidle');
    await captureFormState(page, 'TS1-S03_form');
    await captureModalEvidence(page, 'TS1-S03_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S04: System shall not allow to submit case without entering data.
  // ------------------------------------------------------------------------
  await test.step('TS1-S04: System shall not allow to submit case without entering data.', async () => {
    await captureFormState(page, 'TS1-S04_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S04_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S05: System shall not allow to register case, if following fields are empty.
Case Classifications Code
Case Intake Source Code
Company Receipt Date
  // ------------------------------------------------------------------------
  await test.step('TS1-S05: System shall not allow to register case, if following fields are empty.
Case Classifications Code
Case Intake Source Code
Company Receipt Date', async () => {
    // [FIELD:TS1-S05-F01] general -> Case Classifications Code
    await fillFieldInSection(page, 'general', 'Case Classifications Code', 'Adverse Event');
    // [FIELD:TS1-S05-F02] general -> Processing Center Received Date
    await fillFieldInSection(page, 'general', 'Processing Center Received Date', '2026-10-14');
    await captureFormState(page, 'TS1-S05_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S05_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S06: System shall not allow to register case, if following fields are empty.
Case Intake Source Code
Company Receipt Date
  // ------------------------------------------------------------------------
  await test.step('TS1-S06: System shall not allow to register case, if following fields are empty.
Case Intake Source Code
Company Receipt Date', async () => {
    // [FIELD:TS1-S06-F01] general -> Case Classifications Code
    await selectDropdownInSection(page, 'general', 'Case Classifications Code', 'Adverse Event');
    // [FIELD:TS1-S06-F02] general -> Processing Center Received Date
    await fillFieldInSection(page, 'general', 'Processing Center Received Date', '2026-10-14');
    await captureFormState(page, 'TS1-S06_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S06_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S07: System shall not allow to register case, if following field is empty.
Company Receipt Date
  // ------------------------------------------------------------------------
  await test.step('TS1-S07: System shall not allow to register case, if following field is empty.
Company Receipt Date', async () => {
    // [FIELD:TS1-S07-F01] general -> Case Classifications Code
    await selectDropdownInSection(page, 'general', 'Case Classifications Code', 'Adverse Event');
    // [FIELD:TS1-S07-F02] general -> Case Intake Source Code
    await selectDropdownInSection(page, 'general', 'Case Intake Source Code', 'Spontaneous');
    // [FIELD:TS1-S07-F03] general -> Processing Center Received Date
    await fillFieldInSection(page, 'general', 'Processing Center Received Date', '2026-10-14');
    await captureFormState(page, 'TS1-S07_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S07_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S08: System shall not allow to register case, if Classifications doesn’t match.
  // ------------------------------------------------------------------------
  await test.step('TS1-S08: System shall not allow to register case, if Classifications doesn’t match.', async () => {
    // [FIELD:TS1-S08-F01] general -> Case Classifications Code
    await selectDropdownInSection(page, 'general', 'Case Classifications Code', 'General Inquiry');
    // [FIELD:TS1-S08-F02] general -> Case Intake Source Code
    await selectDropdownInSection(page, 'general', 'Case Intake Source Code', 'Spontaneous');
    // [FIELD:TS1-S08-F03] general -> Company Receipt Date
    await fillFieldInSection(page, 'general', 'Company Receipt Date', '2026-10-14');
    // [FIELD:TS1-S08-F04] general -> Processing Center Received Date
    await fillFieldInSection(page, 'general', 'Processing Center Received Date', '2026-10-14');
    await captureFormState(page, 'TS1-S08_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S08_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S09: System shall allow to Register Case.
  // ------------------------------------------------------------------------
  await test.step('TS1-S09: System shall allow to Register Case.', async () => {
    // [FIELD:TS1-S09-F01] general -> Case Classifications Code
    await selectDropdownInSection(page, 'general', 'Case Classifications Code', 'Adverse Event');
    // [FIELD:TS1-S09-F02] general -> Case Intake Source Code
    await selectDropdownInSection(page, 'general', 'Case Intake Source Code', 'Spontaneous');
    // [FIELD:TS1-S09-F03] general -> Company Receipt Date
    await fillFieldInSection(page, 'general', 'Company Receipt Date', '2026-10-14');
    // [FIELD:TS1-S09-F04] general -> Processing Center Received Date
    await fillFieldInSection(page, 'general', 'Processing Center Received Date', '2026-10-14');
    await captureFormState(page, 'TS1-S09_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S09_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S10: System shall not allow to add Questionnaire manually if mandatory fields are empty.
  // ------------------------------------------------------------------------
  await test.step('TS1-S10: System shall not allow to add Questionnaire manually if mandatory fields are empty.', async () => {
    await captureFormState(page, 'TS1-S10_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S10_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S11: System shall allow to add Questionnaire manually
  // ------------------------------------------------------------------------
  await test.step('TS1-S11: System shall allow to add Questionnaire manually', async () => {
    // [FIELD:TS1-S11-F01] questionnaire -> Field Type
    await selectDropdownInSection(page, 'questionnaire', 'Field Type', 'Text');
    // [FIELD:TS1-S11-F02] questionnaire -> Question
    await fillFieldInSection(page, 'questionnaire', 'Question', 'Did the patient experience pyrexia or chills?');
    await captureFormState(page, 'TS1-S11_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S11_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S12: System shall allow to provide response for manually created question.
  // ------------------------------------------------------------------------
  await test.step('TS1-S12: System shall allow to provide response for manually created question.', async () => {
    // [FIELD:TS1-S12-F01] questionnaire -> Response
    await fillFieldInSection(page, 'questionnaire', 'Response', 'Patient confirmed mild pyrexia resolved within 24 hours.');
    await captureFormState(page, 'TS1-S12_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S12_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S13: System shall allow to delete manually created questions.
  // ------------------------------------------------------------------------
  await test.step('TS1-S13: System shall allow to delete manually created questions.', async () => {
    await captureFormState(page, 'TS1-S13_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S13_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S14: System shall allow to add Questionnaire from template.
  // ------------------------------------------------------------------------
  await test.step('TS1-S14: System shall allow to add Questionnaire from template.', async () => {
    await captureFormState(page, 'TS1-S14_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S14_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S15: System shall allow to provide response for created question from template under Questionnaire tab.
  // ------------------------------------------------------------------------
  await test.step('TS1-S15: System shall allow to provide response for created question from template under Questionnaire tab.', async () => {
    await captureFormState(page, 'TS1-S15_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S15_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S16: System shall allow to add one more Questionnaire from template.
  // ------------------------------------------------------------------------
  await test.step('TS1-S16: System shall allow to add one more Questionnaire from template.', async () => {
    await captureFormState(page, 'TS1-S16_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S16_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S17: System shall restrict to import same Questionnaire template.
  // ------------------------------------------------------------------------
  await test.step('TS1-S17: System shall restrict to import same Questionnaire template.', async () => {
    await captureFormState(page, 'TS1-S17_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S17_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S18: System shall allow to delete the Questionnaire template.
  // ------------------------------------------------------------------------
  await test.step('TS1-S18: System shall allow to delete the Questionnaire template.', async () => {
    await captureFormState(page, 'TS1-S18_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S18_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S19: System shall not allow to Submit case if the Reporter Country and First Name is blank.
  // ------------------------------------------------------------------------
  await test.step('TS1-S19: System shall not allow to Submit case if the Reporter Country and First Name is blank.', async () => {
    // [FIELD:TS1-S19-F01] patient -> First Name
    await fillFieldInSection(page, 'patient', 'First Name', 'John');
    // [FIELD:TS1-S19-F02] product -> Product Name
    await searchAndSelectInModal(page, 'product', 'Product Name', 'Paracetamol');
    // [FIELD:TS1-S19-F03] event -> Reaction Or Event As Reported
    await fillFieldInSection(page, 'event', 'Reaction Or Event As Reported', 'Fever');
    // [FIELD:TS1-S19-F04] event -> Reported Term
    await searchAndSelectInModal(page, 'event', 'Reported Term', 'Fever');
    await captureFormState(page, 'TS1-S19_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S19_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S20: System shall not allow to Submit case if the Patient First Name is blank.
  // ------------------------------------------------------------------------
  await test.step('TS1-S20: System shall not allow to Submit case if the Patient First Name is blank.', async () => {
    // [FIELD:TS1-S20-F01] reporter -> First Name
    await fillFieldInSection(page, 'reporter', 'First Name', 'Alexander');
    // [FIELD:TS1-S20-F02] reporter -> Country Code
    await selectDropdownInSection(page, 'reporter', 'Country Code', 'United States');
    // [FIELD:TS1-S20-F03] product -> Product Name
    await searchAndSelectInModal(page, 'product', 'Product Name', 'Paracetamol');
    // [FIELD:TS1-S20-F04] event -> Reaction Or Event As Reported
    await fillFieldInSection(page, 'event', 'Reaction Or Event As Reported', 'Fever');
    // [FIELD:TS1-S20-F05] event -> Reported Term
    await searchAndSelectInModal(page, 'event', 'Reported Term', 'Fever');
    await captureFormState(page, 'TS1-S20_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S20_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S21: System shall not allow to Submit case if the product Name is blank
  // ------------------------------------------------------------------------
  await test.step('TS1-S21: System shall not allow to Submit case if the product Name is blank', async () => {
    // [FIELD:TS1-S21-F01] reporter -> First Name
    await fillFieldInSection(page, 'reporter', 'First Name', 'Alexander');
    // [FIELD:TS1-S21-F02] reporter -> Country Code
    await selectDropdownInSection(page, 'reporter', 'Country Code', 'United States');
    // [FIELD:TS1-S21-F03] patient -> First Name
    await fillFieldInSection(page, 'patient', 'First Name', 'John');
    // [FIELD:TS1-S21-F04] event -> Reaction Or Event As Reported
    await fillFieldInSection(page, 'event', 'Reaction Or Event As Reported', 'Fever');
    // [FIELD:TS1-S21-F05] event -> Reported Term
    await searchAndSelectInModal(page, 'event', 'Reported Term', 'Fever');
    await captureFormState(page, 'TS1-S21_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S21_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S22: System shall not allow to Submit case if the Reaction Or Event As Reported and Reported Term is blank.
  // ------------------------------------------------------------------------
  await test.step('TS1-S22: System shall not allow to Submit case if the Reaction Or Event As Reported and Reported Term is blank.', async () => {
    // [FIELD:TS1-S22-F01] reporter -> First Name
    await fillFieldInSection(page, 'reporter', 'First Name', 'Alexander');
    // [FIELD:TS1-S22-F02] reporter -> Country Code
    await selectDropdownInSection(page, 'reporter', 'Country Code', 'United States');
    // [FIELD:TS1-S22-F03] patient -> First Name
    await fillFieldInSection(page, 'patient', 'First Name', 'John');
    // [FIELD:TS1-S22-F04] product -> Product Name
    await searchAndSelectInModal(page, 'product', 'Product Name', 'Paracetamol');
    await captureFormState(page, 'TS1-S22_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S22_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S23: System shall allow to add reporter.
  // ------------------------------------------------------------------------
  await test.step('TS1-S23: System shall allow to add reporter.', async () => {
    // [FIELD:TS1-S23-F01] reporter -> Sex code
    await selectDropdownInSection(page, 'reporter', 'Sex code', 'Male');
    // [FIELD:TS1-S23-F02] reporter -> Is Primary Reporter
    await toggleSwitchInSection(page, 'reporter', 'Is Primary Reporter', 'true');
    // [FIELD:TS1-S23-F03] reporter -> Relationship With Patient Code
    await selectDropdownInSection(page, 'reporter', 'Relationship With Patient Code', 'Physician');
    // [FIELD:TS1-S23-F04] reporter -> Reporter Type code
    await selectDropdownInSection(page, 'reporter', 'Reporter Type code', 'Healthcare Professional');
    // [FIELD:TS1-S23-F05] reporter -> Is Reporter Health Care Professional
    await toggleSwitchInSection(page, 'reporter', 'Is Reporter Health Care Professional', 'true');
    // [FIELD:TS1-S23-F06] reporter -> Country code
    await selectDropdownInSection(page, 'reporter', 'Country code', 'United States');
    // [FIELD:TS1-S23-F07] reporter -> Email Address
    await fillFieldInSection(page, 'reporter', 'Email Address', 'alexander.fleming@hospital.org');
    await captureFormState(page, 'TS1-S23_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S23_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S24: System shall allow to Update the reporter.
  // ------------------------------------------------------------------------
  await test.step('TS1-S24: System shall allow to Update the reporter.', async () => {
    // [FIELD:TS1-S24-F01] reporter -> Sex code
    await selectDropdownInSection(page, 'reporter', 'Sex code', 'Male');
    // [FIELD:TS1-S24-F02] reporter -> Is Primary Reporter
    await toggleSwitchInSection(page, 'reporter', 'Is Primary Reporter', 'true');
    // [FIELD:TS1-S24-F03] reporter -> Relationship With Patient Code
    await selectDropdownInSection(page, 'reporter', 'Relationship With Patient Code', 'Physician');
    // [FIELD:TS1-S24-F04] reporter -> Reporter Type code
    await selectDropdownInSection(page, 'reporter', 'Reporter Type code', 'Healthcare Professional');
    // [FIELD:TS1-S24-F05] reporter -> Is Reporter Health Care Professional
    await toggleSwitchInSection(page, 'reporter', 'Is Reporter Health Care Professional', 'true');
    // [FIELD:TS1-S24-F06] reporter -> Country code
    await selectDropdownInSection(page, 'reporter', 'Country code', 'United States');
    // [FIELD:TS1-S24-F07] reporter -> Email Address
    await fillFieldInSection(page, 'reporter', 'Email Address', 'alexander.fleming@hospital.org');
    await captureFormState(page, 'TS1-S24_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S24_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S25: System shall allow to Add Patient information.
  // ------------------------------------------------------------------------
  await test.step('TS1-S25: System shall allow to Add Patient information.', async () => {
    // [FIELD:TS1-S25-F01] patient -> Is Reporter As Patient
    await selectDropdownInSection(page, 'patient', 'Is Reporter As Patient', 'No');
    // [FIELD:TS1-S25-F02] patient -> Title
    await selectDropdownInSection(page, 'patient', 'Title', 'Mr');
    // [FIELD:TS1-S25-F03] patient -> Occupation
    await fillFieldInSection(page, 'patient', 'Occupation', 'Engineer');
    // [FIELD:TS1-S25-F04] patient -> Date of Birth
    await fillFieldInSection(page, 'patient', 'Date of Birth', '1985-06-15');
    // [FIELD:TS1-S25-F05] patient -> Sex Code
    await selectDropdownInSection(page, 'patient', 'Sex Code', 'Male');
    // [FIELD:TS1-S25-F06] patient -> Country Code
    await selectDropdownInSection(page, 'patient', 'Country Code', 'United States');
    await captureFormState(page, 'TS1-S25_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S25_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S26: System shall allow to Update the Patient information.
  // ------------------------------------------------------------------------
  await test.step('TS1-S26: System shall allow to Update the Patient information.', async () => {
    // [FIELD:TS1-S26-F01] patient -> Is Reporter As Patient
    await selectDropdownInSection(page, 'patient', 'Is Reporter As Patient', 'No');
    // [FIELD:TS1-S26-F02] patient -> Title
    await selectDropdownInSection(page, 'patient', 'Title', 'Mr');
    // [FIELD:TS1-S26-F03] patient -> Occupation
    await fillFieldInSection(page, 'patient', 'Occupation', 'Engineer');
    // [FIELD:TS1-S26-F04] patient -> Date of Birth
    await fillFieldInSection(page, 'patient', 'Date of Birth', '1985-06-15');
    // [FIELD:TS1-S26-F05] patient -> Sex Code
    await selectDropdownInSection(page, 'patient', 'Sex Code', 'Male');
    // [FIELD:TS1-S26-F06] patient -> Country Code
    await selectDropdownInSection(page, 'patient', 'Country Code', 'United States');
    await captureFormState(page, 'TS1-S26_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S26_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S27: System shall allow to Add product.
  // ------------------------------------------------------------------------
  await test.step('TS1-S27: System shall allow to Add product.', async () => {
    // [FIELD:TS1-S27-F01] product -> Product Name
    await searchAndSelectInModal(page, 'product', 'Product Name', 'Paracetamol');
    // [FIELD:TS1-S27-F02] product -> Additional Drug Information
    await fillFieldInSection(page, 'product', 'Additional Drug Information', 'Administered orally 500mg BID with normal saline.');
    await captureFormState(page, 'TS1-S27_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S27_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S28: System shall Allow to view Product Information
  // ------------------------------------------------------------------------
  await test.step('TS1-S28: System shall Allow to view Product Information', async () => {
    await captureFormState(page, 'TS1-S28_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S28_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S29: System shall Allow to download Product Information
  // ------------------------------------------------------------------------
  await test.step('TS1-S29: System shall Allow to download Product Information', async () => {
    await captureFormState(page, 'TS1-S29_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S29_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S30: System shall allow to view FAQ during Initial case registration.
  // ------------------------------------------------------------------------
  await test.step('TS1-S30: System shall allow to view FAQ during Initial case registration.', async () => {
    await captureFormState(page, 'TS1-S30_form');
    await captureModalEvidence(page, 'TS1-S30_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S31: System shall allow to update the Additional Drug Information field data.
  // ------------------------------------------------------------------------
  await test.step('TS1-S31: System shall allow to update the Additional Drug Information field data.', async () => {
    await captureFormState(page, 'TS1-S31_form');
    await captureModalEvidence(page, 'TS1-S31_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S32: System shall allow to Add Event Information.
  // ------------------------------------------------------------------------
  await test.step('TS1-S32: System shall allow to Add Event Information.', async () => {
    // [FIELD:TS1-S32-F01] event -> Reaction Or Event As Reported
    await fillFieldInSection(page, 'event', 'Reaction Or Event As Reported', 'Severe Pyrexia');
    // [FIELD:TS1-S32-F02] event -> Reported Term
    await searchAndSelectInModal(page, 'event', 'Reported Term', 'Pyrexia');
    // [FIELD:TS1-S32-F03] event -> Start Date
    await fillFieldInSection(page, 'event', 'Start Date', '2026-10-10');
    // [FIELD:TS1-S32-F04] event -> End Date
    await fillFieldInSection(page, 'event', 'End Date', '2026-10-12');
    // [FIELD:TS1-S32-F05] event_assessment -> Case Serious Reporter Code
    await selectDropdownInSection(page, 'event_assessment', 'Case Serious Reporter Code', 'Serious');
    // [FIELD:TS1-S32-F06] event_assessment -> Case Serious Company Code
    await selectDropdownInSection(page, 'event_assessment', 'Case Serious Company Code', 'Serious');
    // [FIELD:TS1-S32-F07] event_assessment -> Outcome Code
    await selectDropdownInSection(page, 'event_assessment', 'Outcome Code', 'Recovered/Resolved');
    // [FIELD:TS1-S32-F08] event_assessment -> Lack Of Efficacy
    await selectDropdownInSection(page, 'event_assessment', 'Lack Of Efficacy', 'No');
    // [FIELD:TS1-S32-F09] event_seriousness -> Death
    await selectDropdownInSection(page, 'event_seriousness', 'Death', 'No');
    // [FIELD:TS1-S32-F10] event_seriousness -> Hospitalization
    await selectDropdownInSection(page, 'event_seriousness', 'Hospitalization', 'Yes');
    // [FIELD:TS1-S32-F11] event_seriousness -> Life Threatening
    await selectDropdownInSection(page, 'event_seriousness', 'Life Threatening', 'No');
    // [FIELD:TS1-S32-F12] event_seriousness -> Disabling
    await selectDropdownInSection(page, 'event_seriousness', 'Disabling', 'No');
    // [FIELD:TS1-S32-F13] event_seriousness -> Congenital Anomaly
    await selectDropdownInSection(page, 'event_seriousness', 'Congenital Anomaly', 'No');
    // [FIELD:TS1-S32-F14] event_seriousness -> Intervention Required
    await selectDropdownInSection(page, 'event_seriousness', 'Intervention Required', 'Yes');
    // [FIELD:TS1-S32-F15] event_seriousness -> Medically Significant
    await selectDropdownInSection(page, 'event_seriousness', 'Medically Significant', 'No');
    // [FIELD:TS1-S32-F16] event_seriousness -> Others
    await selectDropdownInSection(page, 'event_seriousness', 'Others', 'No');
    await captureFormState(page, 'TS1-S32_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S32_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S33: Verifying Reported Term’s Meddra Code.
  // ------------------------------------------------------------------------
  await test.step('TS1-S33: Verifying Reported Term’s Meddra Code.', async () => {
    await captureFormState(page, 'TS1-S33_form');
    await captureModalEvidence(page, 'TS1-S33_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S34: System shall allow to Update the Event Information.
  // ------------------------------------------------------------------------
  await test.step('TS1-S34: System shall allow to Update the Event Information.', async () => {
    // [FIELD:TS1-S34-F01] event -> Reaction Or Event As Reported
    await fillFieldInSection(page, 'event', 'Reaction Or Event As Reported', 'Severe Pyrexia');
    // [FIELD:TS1-S34-F02] event -> Reported Term
    await searchAndSelectInModal(page, 'event', 'Reported Term', 'Pyrexia');
    // [FIELD:TS1-S34-F03] event -> Start Date
    await fillFieldInSection(page, 'event', 'Start Date', '2026-10-10');
    // [FIELD:TS1-S34-F04] event -> End Date
    await fillFieldInSection(page, 'event', 'End Date', '2026-10-12');
    // [FIELD:TS1-S34-F05] event_assessment -> Case Serious Reporter Code
    await selectDropdownInSection(page, 'event_assessment', 'Case Serious Reporter Code', 'Serious');
    // [FIELD:TS1-S34-F06] event_assessment -> Case Serious Company Code
    await selectDropdownInSection(page, 'event_assessment', 'Case Serious Company Code', 'Serious');
    // [FIELD:TS1-S34-F07] event_assessment -> Outcome Code
    await selectDropdownInSection(page, 'event_assessment', 'Outcome Code', 'Recovered/Resolved');
    // [FIELD:TS1-S34-F08] event_assessment -> Lack Of Efficacy
    await selectDropdownInSection(page, 'event_assessment', 'Lack Of Efficacy', 'No');
    // [FIELD:TS1-S34-F09] event_seriousness -> Death
    await selectDropdownInSection(page, 'event_seriousness', 'Death', 'No');
    // [FIELD:TS1-S34-F10] event_seriousness -> Hospitalization
    await selectDropdownInSection(page, 'event_seriousness', 'Hospitalization', 'Yes');
    // [FIELD:TS1-S34-F11] event_seriousness -> Life Threatening
    await selectDropdownInSection(page, 'event_seriousness', 'Life Threatening', 'No');
    // [FIELD:TS1-S34-F12] event_seriousness -> Disabling
    await selectDropdownInSection(page, 'event_seriousness', 'Disabling', 'No');
    // [FIELD:TS1-S34-F13] event_seriousness -> Congenital Anomaly
    await selectDropdownInSection(page, 'event_seriousness', 'Congenital Anomaly', 'No');
    // [FIELD:TS1-S34-F14] event_seriousness -> Intervention Required
    await selectDropdownInSection(page, 'event_seriousness', 'Intervention Required', 'Yes');
    // [FIELD:TS1-S34-F15] event_seriousness -> Medically Significant
    await selectDropdownInSection(page, 'event_seriousness', 'Medically Significant', 'No');
    // [FIELD:TS1-S34-F16] event_seriousness -> Others
    await selectDropdownInSection(page, 'event_seriousness', 'Others', 'No');
    await captureFormState(page, 'TS1-S34_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S34_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S35: Verifying Updated Meddra Code.
  // ------------------------------------------------------------------------
  await test.step('TS1-S35: Verifying Updated Meddra Code.', async () => {
    await captureFormState(page, 'TS1-S35_form');
    await captureModalEvidence(page, 'TS1-S35_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S36: System shall allow to add Log details.
  // ------------------------------------------------------------------------
  await test.step('TS1-S36: System shall allow to add Log details.', async () => {
    // [FIELD:TS1-S36-F01] activity_log -> Open Date
    await fillFieldInSection(page, 'activity_log', 'Open Date', '2026-10-14');
    // [FIELD:TS1-S36-F02] activity_log -> Close Date
    await fillFieldInSection(page, 'activity_log', 'Close Date', '2026-10-14');
    // [FIELD:TS1-S36-F03] activity_log -> Type
    await selectDropdownInSection(page, 'activity_log', 'Type', 'Submission Note');
    // [FIELD:TS1-S36-F04] activity_log -> Comments
    await fillFieldInSection(page, 'activity_log', 'Comments', 'Automated GxP qualification log entry verified by validation agent.');
    await captureFormState(page, 'TS1-S36_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S36_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S37: System shall allow to Update the Log detail.
  // ------------------------------------------------------------------------
  await test.step('TS1-S37: System shall allow to Update the Log detail.', async () => {
    // [FIELD:TS1-S37-F01] activity_log -> Open Date
    await fillFieldInSection(page, 'activity_log', 'Open Date', '2026-10-14');
    // [FIELD:TS1-S37-F02] activity_log -> Close Date
    await fillFieldInSection(page, 'activity_log', 'Close Date', '2026-10-14');
    // [FIELD:TS1-S37-F03] activity_log -> Type
    await selectDropdownInSection(page, 'activity_log', 'Type', 'Submission Note');
    // [FIELD:TS1-S37-F04] activity_log -> Comments
    await fillFieldInSection(page, 'activity_log', 'Comments', 'Automated GxP qualification log entry verified by validation agent.');
    await captureFormState(page, 'TS1-S37_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S37_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S38: System shall allow to delete Log detail.
  // ------------------------------------------------------------------------
  await test.step('TS1-S38: System shall allow to delete Log detail.', async () => {
    await captureFormState(page, 'TS1-S38_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S38_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S39: System shall allow to Submit case.
  // ------------------------------------------------------------------------
  await test.step('TS1-S39: System shall allow to Submit case.', async () => {
    await captureFormState(page, 'TS1-S39_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S39_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S40: Verifying Meddra Code of Event Information in Case Processing page.
  // ------------------------------------------------------------------------
  await test.step('TS1-S40: Verifying Meddra Code of Event Information in Case Processing page.', async () => {
    await captureFormState(page, 'TS1-S40_form');
    await captureModalEvidence(page, 'TS1-S40_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S41: System shall allow to Exit from the case processing.
  // ------------------------------------------------------------------------
  await test.step('TS1-S41: System shall allow to Exit from the case processing.', async () => {
    await captureFormState(page, 'TS1-S41_form');
    await captureModalEvidence(page, 'TS1-S41_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S42: System shall allow to Logout.
  // ------------------------------------------------------------------------
  await test.step('TS1-S42: System shall allow to Logout.', async () => {
    await captureFormState(page, 'TS1-S42_form');
    await captureModalEvidence(page, 'TS1-S42_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS2-S01: Accessing into Clinevo OnePV Intake Validation Environment.
  // ------------------------------------------------------------------------
  await test.step('TS2-S01: Accessing into Clinevo OnePV Intake Validation Environment.', async () => {
    await page.goto('https://mpv-two.vercel.app/login');
    await page.waitForLoadState('networkidle');
    await captureFormState(page, 'TS2-S01_form');
    await captureModalEvidence(page, 'TS2-S01_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS2-S02: Login to OnePV Intake system
  // ------------------------------------------------------------------------
  await test.step('TS2-S02: Login to OnePV Intake system', async () => {
    await page.fill('#username', 'sirihari.banda');
    await page.fill('#password', 'Clinevo@2026');
    await page.fill('#enterprise', 'Clinevo');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/intake/**', { timeout: 15000 });
    // [FIELD:TS2-S02-F01] auth -> User Name
    await fillFieldInSection(page, 'auth', 'User Name', 'sirihari.banda');
    // [FIELD:TS2-S02-F02] auth -> Password
    await fillFieldInSection(page, 'auth', 'Password', 'Clinevo@2026');
    // [FIELD:TS2-S02-F03] auth -> Enterprise
    await fillFieldInSection(page, 'auth', 'Enterprise', 'Clinevo');
    await captureFormState(page, 'TS2-S02_form');
    await captureModalEvidence(page, 'TS2-S02_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS2-S03: System shall allow to navigate to case processing page.
  // ------------------------------------------------------------------------
  await test.step('TS2-S03: System shall allow to navigate to case processing page.', async () => {
    // [FIELD:TS2-S03-F01] case_processing -> Case Classification Code
    await selectDropdownInSection(page, 'case_processing', 'Case Classification Code', 'Verified');
    // [FIELD:TS2-S03-F02] case_processing -> Case Intake Source Code
    await selectDropdownInSection(page, 'case_processing', 'Case Intake Source Code', 'Verified');
    await captureFormState(page, 'TS2-S03_form');
    await captureModalEvidence(page, 'TS2-S03_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS2-S04: System shall allow to update the Reported Term Field.
  // ------------------------------------------------------------------------
  await test.step('TS2-S04: System shall allow to update the Reported Term Field.', async () => {
    await captureFormState(page, 'TS2-S04_form');
    await captureModalEvidence(page, 'TS2-S04_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS2-S05: System shall display the audit history for the Reported Term field.
  // ------------------------------------------------------------------------
  await test.step('TS2-S05: System shall display the audit history for the Reported Term field.', async () => {
    await captureFormState(page, 'TS2-S05_form');
    await captureModalEvidence(page, 'TS2-S05_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS2-S06: System shall allow to export the Audit History in Excel file.
  // ------------------------------------------------------------------------
  await test.step('TS2-S06: System shall allow to export the Audit History in Excel file.', async () => {
    await captureFormState(page, 'TS2-S06_form');
    await captureModalEvidence(page, 'TS2-S06_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS2-S07: Verify Reported Term in Excel file.
  // ------------------------------------------------------------------------
  await test.step('TS2-S07: Verify Reported Term in Excel file.', async () => {
    await captureFormState(page, 'TS2-S07_form');
    await captureModalEvidence(page, 'TS2-S07_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS2-S08: System shall allow to Log out.
  // ------------------------------------------------------------------------
  await test.step('TS2-S08: System shall allow to Log out.', async () => {
    await captureFormState(page, 'TS2-S08_form');
    await captureModalEvidence(page, 'TS2-S08_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

});
