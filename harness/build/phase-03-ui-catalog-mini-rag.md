# Phase 03 — UI Catalog Persistence and One Primary Mini-RAG

## Authorization and input exception

- Phase 3 is explicitly authorized by the user on 2026-11-05.
- The user identified the Phase 2 discovery-engine output as unreliable because the workflow changed. Do not treat backend/artifacts/ui_discovery_live.json as a validated catalog source.
- Use the separately curated catalog/ui/application_catalog.json and catalog/ui/discovery_manifest.json as the Phase 3 seed. Preserve their source bytes and record their observed coverage limits.
- This is an explicit Phase 3 input exception; Phase 2 remains incomplete and unapproved. Do not mark Phase 2 approved.

## Objective

Persist versioned UI catalog snapshots and retrieve a small, scoped set of screen, section, field and option metadata for later Planning. Evaluate the lightweight retriever on representative queries before proposing heavier retrieval infrastructure.

## In scope

- Define typed catalog scope, snapshots and records.
- Import a source catalog and optional discovery manifest without rewriting source bytes.
- Persist immutable snapshots with source hashes and stable record identities.
- Filter by application, environment, build, role, locale, catalog version and snapshot.
- Retain navigation and coverage metadata, including undiscovered branches.
- Implement lightweight CPU lexical retrieval with relevance scores, source references, deduplication and an explicit no-match/review result.
- Preserve complete local option sets and return bounded candidates only when a target option is provided; require runtime search for searchable inventories without full local values.
- Provide tokenizer-injected context budgeting that measures complete items and only splits at scenario, checkpoint or catalog-card boundaries. Never truncate source text.
- Keep imported records at candidate lifecycle status unless the source explicitly supplies a stronger status; never promote candidates to validated or approved.

## Out of scope

- Qwen model calls, protocol planning, fixture resolution, Playwright execution, healing or final PASS/FAIL.
- Upload/API/frontend integration or a new HTTP contract.
- Embeddings, a vector database or external services.
- Claiming cross-product accuracy from the OnePV seed. The data model and retrieval filters must remain product-neutral.
- Treating missing build, role or locale metadata as a wildcard when a request supplies those values.

## Dependencies and risks

- Python standard library plus existing project dependencies.
- The current seed is OnePV development only. Application build, role and locale were not observed and remain unknown.
- The seed has no saved screenshots or deterministic locator recipes; imported records remain candidates.
- No Qwen model or tokenizer configuration is present in the backend. Token counting therefore requires an injected model-specific counter; tests use an explicitly labeled fake counter.
- The existing upload serving path still uses the legacy extractor. This phase does not wire canonical ingestion into that contract.

## Acceptance

- Source catalog and manifest bytes are preserved and verified by SHA-256 after persistence.
- Reimporting identical inputs is idempotent; changed source or catalog version yields a distinct snapshot.
- Stable records preserve screen, nested section path, field kind, required/enabled markers, option references and source references without inventing locator recipes.
- Wrong application/environment/build/role/locale/version/snapshot is excluded; ambiguous multi-scope retrieval requests the missing scope.
- Duplicate cards appear once in retrieved context.
- Representative natural-language queries retrieve expected screen/section/field mappings; irrelevant queries return needs_review.
- Long searchable dropdowns stay local as metadata and require runtime lookup; a supplied static option is resolved only by exact unique match, otherwise suggestions remain unselected.
- Token budgeting uses an injected counter, respects configured reserves, packs only complete approved boundary units and raises on an oversized indivisible unit.
- Phase-specific and required prior backend regression tests pass; git diff --check passes.

## Stop condition

Update Phase 3 status, build log and context with observed results. Do not start Phase 4. Stop and await explicit approval.
