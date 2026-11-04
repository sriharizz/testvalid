# Phase 1 handoff context — canonical schemas and source-preserving ingestion

**Status:** Generalization/lossless-ingestion remediation complete; Phase 1 human approval pending. Phase 2 is not authorized.

## 2026-11-04 generalization and lossless-ingestion remediation

- Centralized extensible DOCX label mappings in `backend/app/services/ingestion/field_labels.py`; `extract_docx` accepts per-call alias extensions. Alias normalization is only for lookup and never changes segment/source text.
- Removed the ten-row header search cap; explicit metadata can be read across preceding rows. Added explicit colon-labeled paragraph mapping and broadened source-backed identifier candidates to multiple separator formats.
- Added a separate `DerivedInterpretation` schema with source references, method, confidence and review status. Phase 1 creates no semantic interpretations or executable actions.
- Unknown layouts/labels remain source-backed as unmapped and trigger review. Authored section directives, notes, repetition, unusual wording and multiple/conflicting expected results are retained; no ambiguity-word filtering exists.
- Fixtures cover custom labels, a late header, distributed metadata, paragraph mapping, unseen dotted identifiers, unknown structure, exact authored bytes and source-segment accounting.
- A targeted compatibility search found the existing route in `backend/main.py` still calls `backend/extractor.py`; that legacy parser contains fixed document defaults, section/keyword heuristics, regex splitting and text normalization. It was not changed because changing its output path would affect the established API workflow and Phase 1 does not authorize API integration. Per the updated binding instructions, future canonical ingestion must not use this parser; an explicitly authorized compatibility integration must replace/bridge it before the existing upload workflow can claim these Phase 1 guarantees.

## Implemented boundary

- `backend/app/domain/protocol.py` defines source/document identity, source reference, provenance, canonical test-set/test-case/step/checkpoint, ambiguity/conflict, unmapped-content and quality-report types. It intentionally contains no generated executable action model.
- `backend/app/schemas/protocol.py` defines the Phase 1 authored input shape.
- `backend/app/services/ingestion/author_input_adapter.py` adapts JSON bytes/strings, mappings and plain authored prose without interpreting prose. Exact bytes are retained when supplied; mappings are hashed from stable canonical JSON serialization and disclose that basis in provenance. Unknown fields are preserved as unmapped content with JSON pointers.
- `backend/app/services/ingestion/docx_extractor.py` retains source bytes/hash and ordered paragraphs, tables, headers, footers, cell coordinates, numbering, nested/merged-cell structure and explicit metadata/step layouts. Only explicit table labels are mapped. Unsupported text boxes/altChunk and other unmapped content are retained/flagged.
- `backend/app/services/ingestion/quality_gate.py` marks unresolved source identity conflicts `BLOCKED` and missing identifiers, instructions, expectations, provenance issues or unmapped content for review as applicable.

## Observed source limitation

The supplied OQ and PQ files each contain blank `Test Case #` metadata and a table with ordered procedure/expected-result rows. Extraction observes OQ as 2 test sets with one table-level case each and 42 and 8 ordered rows; PQ as 1 set with one table-level case and 18 ordered rows. It does not treat each step as a separate case without source evidence. The Master Spec/build-card scenario totals (42 + 8 and 18) therefore are not established as distinct cases by these source tables. The document owner must confirm where those scenario identities/groupings are stated before later planning or execution.

The OQ filename identity conflicts with the shared document header identity. The PQ filename/header identifiers match under generalized filename parsing; it remains `NEEDS_REVIEW` due missing case identity and unmapped source content. OQ is `BLOCKED` on its unresolved identity conflict.

## Verification

- `python -m pytest backend/tests/unit -q` — initial Phase 1 final run: 20 passed; current remediation run: 26 passed.
- Read-only sample extraction summary: OQ sets `[1,1]`, step rows `[42,8]`, `BLOCKED`; PQ sets `[1]`, step rows `[18]`, `NEEDS_REVIEW`. All 2,103 OQ and 1,035 PQ source segments were accounted for as mapped/metadata or unmapped/unsupported.
- Targeted legacy compatibility search: `rg -n -i "(strip|replace|remove|discard|ignore|noise|ambigu).{0,100}(text|instruction|procedure|expected|section|keyword|phrase)|(text|instruction|procedure|expected|section|keyword|phrase).{0,100}(strip|replace|remove|discard|ignore|noise|ambigu)|(if|elif).{0,60}(appropriate|relevant|details|some|below|select).{0,60}(text|procedure|instruction)" backend -g '*.py'` — confirmed the existing `backend/main.py` route invokes `backend/extractor.py`; the legacy extractor trims/splits procedure text, normalizes nonbreaking spaces, uses section/keyword heuristics and contains sample-specific defaults. No legacy change was made in this Phase 1 remediation.
- `git diff --check` — exit 0/no output; new files are untracked, so explicit trailing-whitespace scan was also run on authored Phase 1 Python files/tests and was clean.
- Legacy root-level live/later-phase modules were not run. No lint/type-check/security scan command is configured in this phase scope.

## Boundaries and next handoff

No frontend, FastAPI route, dependency, migration or deployment changes were made. Ingestion is not wired into current routes. Phase 1 does not implement discovery, catalog/Mini-RAG, planning, compilation, action generation, execution, healing, evidence or reporting. Wait for human Phase 1 review and separate Phase 2 authorization before any subsequent phase.
