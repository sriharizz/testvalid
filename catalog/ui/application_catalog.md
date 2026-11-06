# OnePV UI Catalogue (initial discovery)

**Environment:** Development — `https://dev.one-aipv.com`  
**Observed:** 2026-11-04  
**Status:** Initial, read-only UI map. Dynamic lists and conditional variants are not fully inventoried.

## Scope

The initial Intake group contains **Manual Case Registration**, **Open Case**, and **Case Revision Search**. At the user's request, this pass also covers **Case Deletion** and the Reports menu pages **Case Explorer**, **Audit History**, and **General Line Listing**.

## Manual Case Registration

The selected form type was **Adverse Event**. The visible selector offered Adverse Event, General Inquiry, Medical Inquiry, MI with AE, Product Quality Complaint, PQC with AE, and PQC with MI. Only the selected Adverse Event form was inspected; other variants were not switched.

Sections map as follows:

| Section | Fields observed |
|---|---|
| General Info | Case Classifications Code (dropdown, required marker); Case Intake Source Code (dropdown, required marker); Company Receipt Date (date, required marker); Processing Center Received Date (date); Questionnaire subsection (Add Questions disabled) |
| Reporter | Title, First Name(English) (required marker), Sex Code, Is Primary Reporter (switch), Relationship With Patient Code, Reporter Type Code, Is Reporter Health Care Professional (switch), Address1(English), Address2(English), City(English), State(English), Country Code (required marker), Zipcode, Fax, Contact Number, Email Address |
| Patient | Patient Initials, Is Reporter As Patient, Title, First Name(English) (required marker), Last Name(English), Occupation(English), Sex Code, Date of Birth, Address1(English), Address2(English), State(English), Country Code, Zipcode, Contact Number, Email Address |
| Product | Product Name(English) (required marker, textbox disabled), Generic Name(English) (textbox disabled), Formulation Code (dropdown), Additional Drug Information(English) |
| Event Information > Event Information | Reaction Or Event As Reported(English) and Reported Term(English) (both required markers), Start Date, Start Date UE, End Date, End Date Ue |
| Event Information > Assesment | Case Serious Reporter Code, Case Serious Company Code, Outcome Code, Lack Of Efficacy |
| Event Information > Seriousness | Death, Hospitalization, Life Threatening, Disabling, Congenital Anomaly, Intervention Required, Medically Significant, Others |
| Log > Activity Log | Search box and empty table (0 of 0); table headers Open Date, Close Date, Type, Comments, Action |

The form showed **57 section fields**, plus the form-type selector and Activity Log search box (**59 controls total**): 25 dropdowns (including form type), 26 text/date inputs, 5 textareas, 2 switches, and 1 search box. Repeated labels remain scoped to their section. Nine required asterisks were visible; this is a UI marker observation, not verified backend validation.

## Other screens

| Screen | Section and fields |
|---|---|
| Open Case | Case Intake Search: Case Number, Case Intake Reference Number, Product Name, Case Classifications Code, Case Status Code, Case Intake Source Code, First Name, Last Name, Email Address, Company Receipt Date From/To, Country Code, Contact Number |
| Case Revision Search | Case Number |
| Case Deletion | Case Intake Delete Search: Case Number, Case Intake Source Code, Webintake Submit switch |
| Case Explorer | Case Explorer Box Search: Workflow Name, Product Name, Country Code, Case Serious Company Code, Case Status Code, Case Intake Source Code, Company Receipt Date From/To, Case Close Date |
| Audit History | Case Number |
| General Line Listing | Page-level search, per-column search boxes for Name/Description/SQL Text/Created On/Created By User/Updated By User; Search Filters dialog with Column, Operator, Value |

Search, Save, Submit, Add, Reset, lookup, and delete actions were not used to alter or query application records. General Line Listing showed nine saved definitions; only the UI structure and row count are retained. Saved query content and user names are omitted.

## Other form variant dropdowns

The selector offered seven form types. Beyond Adverse Event, the first four options were inspected for dropdowns only. Fields are section-scoped and share deduplicated option sets:

| Variant | Dropdown map |
|---|---|
| General Inquiry | General Info (2), Reporter (5), Product (1), Medical Information (1): 9 total |
| Medical Inquiry | General Info (2), Reporter (5), Product (1), Medical Information (1): 9 total |
| MI with AE | Adverse Event dropdown set plus Medical Information > Found Answer: 25 total |
| Product Quality Complaint | General Info (2), Reporter (5), Product (1), Product Complaint Details (3): 11 total |

Product Quality Complaint adds Product Complaint Classification Code (12 options), Product Complaint Category Code (8), and Status Code (3). General Inquiry and Medical Inquiry add Found Answer (Un-select / No / Yes). The remaining PQC with AE and PQC with MI variants are not yet inspected. Alternate text fields were not recatalogued.

## Option inventory and runtime search

All **25 dropdown controls** on the selected Adverse Event form were opened and closed without selecting values. The inspected dropdowns across the alternate forms also exposed a Search textbox. The form-type dropdown has seven variants. Adverse Event, General Inquiry, Medical Inquiry, MI with AE, and Product Quality Complaint were inspected; PQC with AE and PQC with MI remain uninspected. The Country Code controls in Reporter and Patient expose a Search textbox and showed 258 options. Formulation Code exposes a Search textbox and showed 706 options. Their complete values are intentionally omitted; Playwright can search the exact value supplied by a test case at runtime.

For these custom dropdowns, the execution pattern is: open the scoped field, fill its visible Search textbox, select only one exact matching option, and verify the selected label. Treat no match or multiple matches as unresolved. Playwright's locator.fill() supports input controls, while locator.selectOption() applies only to native HTML select elements (see https://playwright.dev/docs/api/class-locator). Compact observed lists remain stored as option sets. No business dropdown value was selected; form-type choices were temporary inspection state and the selector was restored to Adverse Event.

## Limits and evidence

This map describes the UI state observed during this session, not server validation or hidden conditional branches. Dropdowns only were inspected for General Inquiry, Medical Inquiry, MI with AE, and Product Quality Complaint. PQC with AE and PQC with MI remain uninspected. No searches were run and no case data was entered.

Browser/computer interaction was stopped by the user with the physical Escape key before screenshot evidence could be saved. The evidence folder contains a note documenting that gap; no screenshot files are claimed as captured. See `discovery_manifest.json` for coverage and action details.

