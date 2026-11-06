# Phase 03 Context — UI Catalog Persistence and One Primary Mini-RAG

## Authorization and phase boundary

- Authorized by the user's 2026-11-05 instruction to move to Phase 3 because the Phase 2 discovery approach/output was unreliable.
- Phase 2 remains incomplete and unapproved. The independent, manually curated UI catalog is the Phase 3 seed; the Phase 2 live discovery artifact is excluded.
- Phase 3 is limited to persistence and retrieval. No Qwen planning, upload serving integration or browser execution is included.

## Implementation

- The source catalog and optional manifest are stored byte-for-byte with SHA-256 checks and an append-only snapshot identity scoped by application/environment/build/role/locale/version.
- Each snapshot has stable screen, section and control records. Field cards retain nested section paths, control type, required/enabled observations, option references and JSON-pointer source references. Existing UI IDs are descriptive metadata only; locator recipes are not fabricated.
- Imported mappings remain lifecycle candidate with source observation observed; locator uniqueness/behavior is not validated.
- Navigation graph, coverage data and complete local option sets stay in the snapshot. Dynamic searchable option sets are not expanded into prompt candidates and require runtime lookup.
- Retrieval uses word and character n-gram TF-IDF, exact metadata scoping, deduplication and a relevance threshold. Retrieval misses return needs_review.
- Context cards can be packed with a required injected model tokenizer. The packer never truncates content and accepts only scenario, checkpoint or catalog-card split boundaries.
- The initial versioned seed is stored under catalog/ui/store/.

## Evaluation

- Five representative queries cover Reporter first name, Case Deletion case number, Audit History case number, Product Quality Complaint status, and Medical Inquiry's Found Answer.
- The expected card appeared in the top five for all five queries; measured MRR was 1.000.
- This is a small deterministic smoke evaluation, not evidence of broad paraphrase coverage or superiority to structured lookup. Extend the evaluation with real protocol wording and additional products before choosing a more complex retriever.

## Known limitations

- The seed covers OnePV development only; build/role/locale are unknown.
- PQC with AE and PQC with MI remain uninspected; alternate text fields were not recatalogued for all inspected variants.
- Screenshots were not saved. Catalog mappings are candidates, not validated/approved locator metadata.
- The project has no configured Qwen tokenizer; production budgeting must supply the exact runtime tokenizer/configuration.
- Upload ingestion remains disconnected from the serving workflow. Phase 4 planning and later execution are separate authorized phases.
