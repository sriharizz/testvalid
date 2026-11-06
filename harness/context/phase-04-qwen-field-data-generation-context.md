# Phase 04 Context — Qwen Synthetic Field-Data Generation

## Authorization and boundary

- User explicitly authorized Phase 4 on 2026-11-05. D-022 supersedes D-021: Qwen returns compact, source-grounded action intents and field values; Python validates/compiles intents; Playwright alone executes.
- Allowed intent kinds: `navigate_screen`, `open_section`, `fill_section`, and `click_control`. Intents reference retrieved screen/section keys and source steps; click text must appear in its cited source step. Qwen never returns locators or executable code.
- Synthetic values use `qwen_synthetic`; explicit values and intentional blanks preserve their own provenance. No browser execution, Save or Submit was performed in this follow-up.
- No app record was saved/submitted and no browser action was executed in this phase.

## Implemented

- Pydantic schemas, canonical input adapter, section-first catalog retrieval, compact prompt builder, Qwen provider adapter integration, output validator and generation service.
- Validator rejects unknown or mismatched targets/fields, disabled or non-entry controls, duplicate field references, unsupported source references, and invalid value provenance. Searchable option values are runtime-search intents, not invented dropdown options.
- One provider call per request. Invalid output becomes `NEEDS_REVIEW`; no repair call. Real patient data, credentials, cookies, tokens and secrets are blocked from model prompts.
- The previous large Phase 4 action-planner implementation and planner tests were removed. This follow-up adds only a compact, typed semantic intent field to the field-data response; the phase card, Master Spec, decision log and repository agent rules reflect D-022.

## Verification and live sample

- Focused Phase 4 and Phase 3 suite: `& '.\\venv\\Scripts\\python.exe' -m pytest backend/tests/unit/test_data_generation_phase4.py backend/tests/unit/test_ui_catalog_phase3.py -q --tb=short` — 23 passed.
- Full backend suite: `& '.\\venv\\Scripts\\python.exe' -m pytest backend/tests/ -q --tb=short` — 63 passed in 39.11s.
- Live synthetic Reporter sample through Groq `qwen/qwen3.8-27b`: 18 Reporter cards retrieved; response validated `ready`; returned Manual Case Registration screen + Reporter section, `First Name(English)=Synthetic`, and Country Code search term `United States`, both `qwen_synthetic` (Country Code uses runtime search). Provider usage: 3,773 prompt + 332 completion = 4,105 total. This is one smoke sample, not broad reliability evidence. No Playwright actions were executed.
- Model-matched tokenizer is not configured. This live measurement is provider-reported only and the service blocks normal dispatch without an injected tokenizer unless provider-only evaluation is explicitly enabled.

## Limits and next gate

- The OnePV development catalog has incomplete coverage. Its records are candidates without validated locator recipes; therefore screen/section IDs and labels alone do not guarantee a unique, actionable live locator.
- Searchable dropdowns still need a deterministic runtime query and exactly one enabled match. Missing, disabled, ambiguous or unknown targets remain `NEEDS_REVIEW`.
- `Product Name (English)` is marked disabled in the current catalog and must not be filled until that observation is reviewed.
- The five-case evaluation used the existing five human-written examples in one batch. A first attempt returned HTTP 400 before model output because the JSON-mode prompt omitted an explicit JSON instruction; the request was corrected and two successful one-call evaluations were saved. Latest usage: 1,431 prompt + 2,324 completion = 3,755 total provider-reported tokens; no model-matched tokenizer is configured. All five passed automated schema/reference/omission validation. Manual review found case 5 listed Patient before Reporter despite the source naming Reporter first; this persisted after adding a generic source-order instruction. Treat that case as NEEDS_REVIEW; current automated validation does not prove semantic action order.
- Latest raw request, retrieved prompt context, raw completion, hydrated output and usage: `backend/artifacts/qwen_evaluations/phase4-human-batch-20261105T094354Z.json` (ignored local artifact). Earlier failed and successful attempts remain in the same directory.
- Phase 4 follow-up remains partial and awaits human review. Do not begin Phase 5 until explicitly authorized.
