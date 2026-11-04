# Phase 1 ingestion and preservation rules

This document describes the current, small structural mapping surface. It is not a claim that arbitrary DOCX content can be automatically interpreted. The complete source bytes remain the recovery source; every extracted segment is also accounted for in the canonical result.

## DOCX field-label mapping

Default aliases are centralized in `backend/app/services/ingestion/field_labels.py`, grouped by canonical field (`case_id`, `title`, `procedure`, `expected`, `step_id`, `test_set_id`, `test_set_title`). Add controlled aliases by passing `label_aliases={canonical_field: ["additional label"]}` to `extract_docx`. Extensions add aliases to the defaults. Normalization (case folding, punctuation-to-space and whitespace collapse) is used only to match labels; the source segment and original DOCX bytes are unchanged.

The extractor searches table rows without a fixed row limit. It maps a data row only when explicit procedure and expected-result labels are present, plus an explicit case-ID column or case metadata labels in rows before the header. Case metadata can be distributed across those rows. Paragraph fields are mapped only from explicit colon-labeled fields; a case identifier establishes paragraph case context before other fields are grouped. Standalone labels without a case context, unmatched labels, directives, notes and unknown structures stay unmapped and require review.

## Document identifier candidates

- Explicit `Protocol ID`, `Document ID`, number/identifier labels preserve their stated value as a candidate; the normalized comparison key is separate.
- Unlabeled filename/header/footer candidates use a general token rule: at least three alphanumeric components separated by hyphen, period or slash, with a digit in the final component. Filename separators can delimit a prefix from such a token. This rule is a candidate recognizer, not an allowlist or proof of document identity.
- Labeled values in other formats remain in the exact source segment and are surfaced for review. Extend the general parser only with evidence and tests; never add document-specific identifiers or sample-specific conditions.
- Multiple distinct candidates remain conflicts and block controlled use. A single candidate does not establish authenticity or approval.

## Lossless and uncertainty rules

- Never filter natural-language content by keywords, phrases, regexes or ambiguity-word lists. Trimming/checking whitespace is permitted only to detect an empty field; stored source text remains unchanged.
- Preserve section directives, navigation context, notes, repetition, unfamiliar wording, conflicting expectations and intentional blanks as original source segments.
- Original bytes and source hash remain available on the canonical document. Mapped fields point back to source references. Unrecognized structures remain unmapped/unsupported with a review reason.
- Extraction does not produce semantic interpretations or executable actions. Any later proposed interpretation uses the separate `DerivedInterpretation` schema with source refs, method, confidence where available and review status.

## Existing legacy path

`backend/main.py` currently invokes `backend/extractor.py` for the served workflow. A bounded compatibility review found document-specific defaults, regex-based splitting, section/keyword heuristics and text normalization in that legacy parser. It was left unchanged to preserve the existing serving contract in Phase 1. New canonical ingestion must not call it; replace or bridge it only in an explicitly authorized compatibility phase.
