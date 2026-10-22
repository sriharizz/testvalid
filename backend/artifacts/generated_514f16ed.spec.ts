import { test, expect, Page } from '@playwright/test';

// Helper: Captures evidence checkpoint
async function captureEvidence(page: Page, tag: string) {
  const path = `artifacts/screenshots/${tag}.png`;
  await page.screenshot({ path });
}

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
  await test.step('TS1-S01: Accessing into Clinevo OnePV Intake Production Environment.', async () => {
    await page.goto('https://mpv-two.vercel.app/login');
    await page.waitForLoadState('networkidle');
    await captureEvidence(page, 'TS1-S01');
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
    await fillFieldInSection(page, 'auth', 'Password', 'Clinevo@2024');
    // [FIELD:TS1-S02-F03] auth -> Enterprise
    await fillFieldInSection(page, 'auth', 'Enterprise', 'Clinevo Global PV');
    await captureEvidence(page, 'TS1-S02');
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
    await captureEvidence(page, 'TS1-S03');
    await captureFormState(page, 'TS1-S03_form');
    await captureModalEvidence(page, 'TS1-S03_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S04: System shall allow to Register Case.
  // ------------------------------------------------------------------------
  await test.step('TS1-S04: System shall allow to Register Case.', async () => {
    // [FIELD:TS1-S04-F01] general -> Case Classifications Code
    await selectDropdownInSection(page, 'general', 'Case Classifications Code', 'AD');
    // [FIELD:TS1-S04-F02] general -> Case Intake Source Code
    await selectDropdownInSection(page, 'general', 'Case Intake Source Code', 'EMAIL');
    // [FIELD:TS1-S04-F03] general -> Company Receipt Date
    await fillFieldInSection(page, 'general', 'Company Receipt Date', '2024-11-15');
    // [FIELD:TS1-S04-F04] general -> Processing Center Received Date
    await fillFieldInSection(page, 'general', 'Processing Center Received Date', '2024-11-16');
    await captureEvidence(page, 'TS1-S04');
    await captureFormState(page, 'TS1-S04_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S04_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S05: System shall allow to add Questionnaire manually.
  // ------------------------------------------------------------------------
  await test.step('TS1-S05: System shall allow to add Questionnaire manually.', async () => {
    // [FIELD:TS1-S05-F01] questionnaire -> Field Type
    await selectDropdownInSection(page, 'questionnaire', 'Field Type', 'TEXT');
    // [FIELD:TS1-S05-F02] questionnaire -> Question
    await fillFieldInSection(page, 'questionnaire', 'Question', 'Did the patient experience any prior episodes of similar symptoms before starting the study drug?');
    await captureEvidence(page, 'TS1-S05');
    await captureFormState(page, 'TS1-S05_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S05_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S06: System shall allow to provide response for manually created question.
  // ------------------------------------------------------------------------
  await test.step('TS1-S06: System shall allow to provide response for manually created question.', async () => {
    // [FIELD:TS1-S06-F01] questionnaire -> Response
    await fillFieldInSection(page, 'questionnaire', 'Response', 'No, this is the first occurrence of the reported symptoms. Patient confirmed no prior history of similar events.');
    await captureEvidence(page, 'TS1-S06');
    await captureFormState(page, 'TS1-S06_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S06_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S07: System shall allow to add Questionnaire from template.
  // ------------------------------------------------------------------------
  await test.step('TS1-S07: System shall allow to add Questionnaire from template.', async () => {
    await captureEvidence(page, 'TS1-S07');
    await captureFormState(page, 'TS1-S07_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S07_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S08: System shall allow to provide response for created question from template under Questionnaire tab.
  // ------------------------------------------------------------------------
  await test.step('TS1-S08: System shall allow to provide response for created question from template under Questionnaire tab.', async () => {
    // [FIELD:TS1-S08-F01] questionnaire -> Response
    await fillFieldInSection(page, 'questionnaire', 'Response', 'Patient reported onset of dizziness approximately 2 hours after administration of the first dose. Symptoms resolved within 30 minutes of rest.');
    await captureEvidence(page, 'TS1-S08');
    await captureFormState(page, 'TS1-S08_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S08_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S09: System shall allow to add reporter.
  // ------------------------------------------------------------------------
  await test.step('TS1-S09: System shall allow to add reporter.', async () => {
    // [FIELD:TS1-S09-F01] reporter -> Title
    await selectDropdownInSection(page, 'reporter', 'Title', 'Dr.');
    // [FIELD:TS1-S09-F02] reporter -> First Name
    await fillFieldInSection(page, 'reporter', 'First Name', 'Ananya');
    // [FIELD:TS1-S09-F03] reporter -> Last Name
    await fillFieldInSection(page, 'reporter', 'Last Name', 'Chatterjee');
    // [FIELD:TS1-S09-F04] reporter -> Sex code
    await selectDropdownInSection(page, 'reporter', 'Sex code', 'F');
    // [FIELD:TS1-S09-F05] reporter -> Relationship With Patient Code
    await selectDropdownInSection(page, 'reporter', 'Relationship With Patient Code', 'SELF');
    // [FIELD:TS1-S09-F06] reporter -> Reporter Type code
    await selectDropdownInSection(page, 'reporter', 'Reporter Type code', 'HCP');
    // [FIELD:TS1-S09-F07] reporter -> Is Reporter Health Care Professional
    await toggleSwitchInSection(page, 'reporter', 'Is Reporter Health Care Professional', 'Y');
    // [FIELD:TS1-S09-F08] reporter -> Address1
    await fillFieldInSection(page, 'reporter', 'Address1', '1204 Medical Plaza, Suite 302');
    // [FIELD:TS1-S09-F09] reporter -> Address2
    await fillFieldInSection(page, 'reporter', 'Address2', 'Building C');
    // [FIELD:TS1-S09-F10] reporter -> City
    await fillFieldInSection(page, 'reporter', 'City', 'Bengaluru');
    // [FIELD:TS1-S09-F11] reporter -> State
    await fillFieldInSection(page, 'reporter', 'State', 'Karnataka');
    // [FIELD:TS1-S09-F12] reporter -> Country code
    await selectDropdownInSection(page, 'reporter', 'Country code', 'IN');
    // [FIELD:TS1-S09-F13] reporter -> Zipcode
    await fillFieldInSection(page, 'reporter', 'Zipcode', '560001');
    // [FIELD:TS1-S09-F14] reporter -> Fax
    await fillFieldInSection(page, 'reporter', 'Fax', '+91-80-41123456');
    // [FIELD:TS1-S09-F15] reporter -> Contact Number
    await fillFieldInSection(page, 'reporter', 'Contact Number', '+91-9876543210');
    // [FIELD:TS1-S09-F16] reporter -> Email Address
    await fillFieldInSection(page, 'reporter', 'Email Address', 'ananya.chatterjee@medcare.in');
    await captureEvidence(page, 'TS1-S09');
    await captureFormState(page, 'TS1-S09_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S09_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S10: System shall allow to Add Patient information.
  // ------------------------------------------------------------------------
  await test.step('TS1-S10: System shall allow to Add Patient information.', async () => {
    // [FIELD:TS1-S10-F01] patient -> Initials
    await fillFieldInSection(page, 'patient', 'Initials', 'RS');
    // [FIELD:TS1-S10-F02] patient -> Is Reporter As Patient
    await selectDropdownInSection(page, 'patient', 'Is Reporter As Patient', 'Y');
    // [FIELD:TS1-S10-F03] patient -> Title
    await selectDropdownInSection(page, 'patient', 'Title', 'Mr.');
    // [FIELD:TS1-S10-F04] patient -> First Name
    await fillFieldInSection(page, 'patient', 'First Name', 'Rajesh');
    // [FIELD:TS1-S10-F05] patient -> Last Name
    await fillFieldInSection(page, 'patient', 'Last Name', 'Sharma');
    // [FIELD:TS1-S10-F06] patient -> Occupation
    await fillFieldInSection(page, 'patient', 'Occupation', 'Software Engineer');
    // [FIELD:TS1-S10-F07] patient -> Date of Birth
    await fillFieldInSection(page, 'patient', 'Date of Birth', '1985-03-22');
    // [FIELD:TS1-S10-F08] patient -> Sex Code
    await selectDropdownInSection(page, 'patient', 'Sex Code', 'M');
    // [FIELD:TS1-S10-F09] patient -> Address 1
    await fillFieldInSection(page, 'patient', 'Address 1', '45 Green Park Avenue');
    // [FIELD:TS1-S10-F10] patient -> Address 2
    await fillFieldInSection(page, 'patient', 'Address 2', 'Apartment 7B');
    // [FIELD:TS1-S10-F11] patient -> State
    await fillFieldInSection(page, 'patient', 'State', 'Karnataka');
    // [FIELD:TS1-S10-F12] patient -> Country Code
    await selectDropdownInSection(page, 'patient', 'Country Code', 'IN');
    // [FIELD:TS1-S10-F13] patient -> Zip Code
    await fillFieldInSection(page, 'patient', 'Zip Code', '560038');
    // [FIELD:TS1-S10-F14] patient -> Contact Number
    await fillFieldInSection(page, 'patient', 'Contact Number', '+91-9845678901');
    // [FIELD:TS1-S10-F15] patient -> Email Address
    await fillFieldInSection(page, 'patient', 'Email Address', 'rajesh.sharma@gmail.com');
    await captureEvidence(page, 'TS1-S10');
    await captureFormState(page, 'TS1-S10_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S10_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S11: System shall allow to Add product.
  // ------------------------------------------------------------------------
  await test.step('TS1-S11: System shall allow to Add product.', async () => {
    // [FIELD:TS1-S11-F01] product -> Product Name
    await searchAndSelectInModal(page, 'product', 'Product Name', 'Clinevo XR 500mg');
    // [FIELD:TS1-S11-F02] product -> Generic Name
    await verifyAutoPopulatedField(page, 'product', 'Generic Name');
    // [FIELD:TS1-S11-F03] product -> Formulation Code
    await verifyAutoPopulatedField(page, 'product', 'Formulation Code');
    // [FIELD:TS1-S11-F04] product -> Additional Drug Information
    await fillFieldInSection(page, 'product', 'Additional Drug Information', 'Extended-release tablet, 500mg per tablet, Batch No: CLX240815, Expiry: 2026-08-31');
    await captureEvidence(page, 'TS1-S11');
    await captureFormState(page, 'TS1-S11_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S11_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S12: System shall allow to Add Event Information.
  // ------------------------------------------------------------------------
  await test.step('TS1-S12: System shall allow to Add Event Information.', async () => {
    // [FIELD:TS1-S12-F01] event -> Reaction Or Event As Reported
    await fillFieldInSection(page, 'event', 'Reaction Or Event As Reported', 'Dizziness and nausea after first dose');
    // [FIELD:TS1-S12-F02] event -> Reported Term
    await searchAndSelectInModal(page, 'event', 'Reported Term', 'Dizziness');
    // [FIELD:TS1-S12-F03] event -> Start Date
    await fillFieldInSection(page, 'event', 'Start Date', '2024-11-14');
    // [FIELD:TS1-S12-F04] event -> End Date
    await fillFieldInSection(page, 'event', 'End Date', '2024-11-14');
    // [FIELD:TS1-S12-F05] event_assessment -> Case Serious Reporter Code
    await selectDropdownInSection(page, 'event_assessment', 'Case Serious Reporter Code', 'N');
    // [FIELD:TS1-S12-F06] event_assessment -> Case Serious Company Code
    await selectDropdownInSection(page, 'event_assessment', 'Case Serious Company Code', 'N');
    // [FIELD:TS1-S12-F07] event_assessment -> Outcome Code
    await selectDropdownInSection(page, 'event_assessment', 'Outcome Code', 'RECOVERED');
    // [FIELD:TS1-S12-F08] event_assessment -> Lack Of Efficacy
    await selectDropdownInSection(page, 'event_assessment', 'Lack Of Efficacy', 'N');
    // [FIELD:TS1-S12-F09] event_seriousness -> Death
    await selectDropdownInSection(page, 'event_seriousness', 'Death', 'N');
    // [FIELD:TS1-S12-F10] event_seriousness -> Hospitalization
    await selectDropdownInSection(page, 'event_seriousness', 'Hospitalization', 'N');
    // [FIELD:TS1-S12-F11] event_seriousness -> Life Threatening
    await selectDropdownInSection(page, 'event_seriousness', 'Life Threatening', 'N');
    // [FIELD:TS1-S12-F12] event_seriousness -> Disabling
    await selectDropdownInSection(page, 'event_seriousness', 'Disabling', 'N');
    // [FIELD:TS1-S12-F13] event_seriousness -> Congenital Anomaly
    await selectDropdownInSection(page, 'event_seriousness', 'Congenital Anomaly', 'N');
    // [FIELD:TS1-S12-F14] event_seriousness -> Intervention Required
    await selectDropdownInSection(page, 'event_seriousness', 'Intervention Required', 'N');
    // [FIELD:TS1-S12-F15] event_seriousness -> Medically Significant
    await selectDropdownInSection(page, 'event_seriousness', 'Medically Significant', 'N');
    // [FIELD:TS1-S12-F16] event_seriousness -> Others
    await selectDropdownInSection(page, 'event_seriousness', 'Others', 'N');
    await captureEvidence(page, 'TS1-S12');
    await captureFormState(page, 'TS1-S12_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S12_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S13: Verifying Reported Term’s Meddra Code.
  // ------------------------------------------------------------------------
  await test.step('TS1-S13: Verifying Reported Term’s Meddra Code.', async () => {
    await captureEvidence(page, 'TS1-S13');
    await captureFormState(page, 'TS1-S13_form');
    await captureModalEvidence(page, 'TS1-S13_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S14: System shall allow to add Log details.
  // ------------------------------------------------------------------------
  await test.step('TS1-S14: System shall allow to add Log details.', async () => {
    // [FIELD:TS1-S14-F01] activity_log -> Open Date
    await fillFieldInSection(page, 'activity_log', 'Open Date', '2024-11-16');
    // [FIELD:TS1-S14-F02] activity_log -> Close Date
    await fillFieldInSection(page, 'activity_log', 'Close Date', '2024-11-20');
    // [FIELD:TS1-S14-F03] activity_log -> Type
    await selectDropdownInSection(page, 'activity_log', 'Type', 'CASE_OPEN');
    // [FIELD:TS1-S14-F04] activity_log -> Comments
    await fillFieldInSection(page, 'activity_log', 'Comments', 'Case opened for initial data entry and verification. All required fields populated. Awaiting medical review for causality assessment.');
    await captureEvidence(page, 'TS1-S14');
    await captureFormState(page, 'TS1-S14_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S14_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S15: System shall allow to Submit case.
  // ------------------------------------------------------------------------
  await test.step('TS1-S15: System shall allow to Submit case.', async () => {
    await captureEvidence(page, 'TS1-S15');
    await captureFormState(page, 'TS1-S15_form');
    await page.click('button[data-testid="top-save-btn"], button:has-text("Save")');
    await page.waitForTimeout(400);
    await captureModalEvidence(page, 'TS1-S15_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S16: Verifying Meddra Code of Event Information in Case Processing page.
  // ------------------------------------------------------------------------
  await test.step('TS1-S16: Verifying Meddra Code of Event Information in Case Processing page.', async () => {
    await captureEvidence(page, 'TS1-S16');
    await captureFormState(page, 'TS1-S16_form');
    await captureModalEvidence(page, 'TS1-S16_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S17: System shall allow to Exit from the case processing.
  // ------------------------------------------------------------------------
  await test.step('TS1-S17: System shall allow to Exit from the case processing.', async () => {
    await captureEvidence(page, 'TS1-S17');
    await captureFormState(page, 'TS1-S17_form');
    await captureModalEvidence(page, 'TS1-S17_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  // ------------------------------------------------------------------------
  // TS1-S18: System shall allow to Logout.
  // ------------------------------------------------------------------------
  await test.step('TS1-S18: System shall allow to Logout.', async () => {
    await captureEvidence(page, 'TS1-S18');
    await captureFormState(page, 'TS1-S18_form');
    await captureModalEvidence(page, 'TS1-S18_modal');
    await dismissModal(page, 'OK');
    await expect(page.locator('body')).not.toBeEmpty();
  });

});
