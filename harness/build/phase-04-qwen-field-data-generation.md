# Phase 4 — Qwen Synthetic Field-Data Generation

## Objective

Use the unchanged canonical procedure plus section-first UI Mini-RAG context to return compact, source-grounded action intents and a synthetic field-value map for deterministic Python compilation. Qwen does not author executable actions, assertions, evidence plans or verdicts.

## In scope

- Configurable Groq/Qwen-compatible client with sanitized errors and provider token usage.
- Typed output containing source-step action intents, retrieved screen/section targets, catalog field IDs/labels, values, provenance, runtime-search mode and unresolved reasons.
- Clearly fictional Qwen-generated test values for requested or required enabled controls; exact source values and intentional blanks remain preserved.
- Deterministic checks for target/card identity, section paths, enabled/data-entry controls, field duplication, source references, provenance and dropdown runtime resolution.
- Compact prompt containing the original procedure and only relevant scoped UI cards; action intents use short retrieved target keys and source-step references.
- One provider request per generation. Invalid output becomes `NEEDS_REVIEW`; no repair request.
- Unit tests for named sections, source preservation, synthetic values, explicit values, blanks, disabled/unknown/optional fields, searchable dropdowns, malformed output, sensitivity gates and provider token accounting.
- One paced live evaluation using a synthetic author-input case and measured provider token counts.

## Out of scope

- Playwright navigation, field filling, Save/Submit, browser actions, compiler, final verdicts, evidence capture, Qwen healing, API/frontend migration, production mutation and UI discovery.
- Any use of real patient data or credentials in prompts.

## Acceptance criteria

- Qwen action intents use only the allow-listed semantic kinds, cite included source steps and retrieved screen/section keys, and contain no locators or executable code. Click target text must appear in its cited source step.
- Qwen field values contain only retrieved field keys and values; assertions, evidence plans and verdict fields are rejected.
- All targets and fields reference retrieved cards; section paths match the catalog.
- Generated values are tagged `qwen_synthetic`; explicit source values and intentional blanks retain their separate provenance.
- Disabled, unknown or unrequested optional controls are rejected or marked `NEEDS_REVIEW`.
- Searchable dropdowns return runtime-search intent; deterministic Playwright must still resolve one unique live option.
- Provider token usage is recorded when returned. No character-based token estimates.
- Phase 4 and Phase 3 focused tests pass; full backend regression and `git diff --check` pass.

## Constraints and risks

- The current catalog is OnePV Development-only, has incomplete coverage and candidate records without validated locator recipes. It cannot guarantee Playwright navigation/fill success by itself.
- Product Name (English) is currently marked disabled in the catalog; output for it must be review-gated until that observation is verified.
- Action intents are proposals for Phase 5 compilation; they are not executed during Phase 4.
- Qwen's synthetic values are not proof of realistic or valid application data. Controlled dropdown values require runtime unique-match checks.
- Do not execute generated values in Playwright during Phase 4.
