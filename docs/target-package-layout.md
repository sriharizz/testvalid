# Proposed Target Package Layout

**Conceptual architecture only.** This records responsibility boundaries for later phases. It creates no package directories and does not authorize implementation. Introduce a package/module only in the phase that implements it, after explicit phase authorization. It follows Master Spec Sections 20.1 and 24, adapted to the current `backend/` and `frontend/` repository layout.

```text
backend/
  app/
    api/                 # FastAPI routes; preserve existing contracts unless a human approves a versioned change
    core/                # configuration, logging, security, environment and action policy
    domain/              # canonical protocol, UI catalog, plan, run and evidence entities
    schemas/             # strict Pydantic API/model schemas
    services/
      ingestion/         # DOCX extraction, authored input adapter, quality gates
      discovery/         # authorized read-only live UI traversal; emits observations/coverage/candidates
      catalog/           # validates, versions and persists eligible UI metadata
      retrieval/         # one scoped UI Mini-RAG; reads catalog for planning
      planning/          # Qwen adapter, prompt assembly, fixtures and typed plan proposal/validation
      compilation/       # validates/translates plans to allow-listed Python action DSL
      execution/         # Playwright session, locator resolution and dispatch of validated DSL only
      healing/           # on-demand locator candidates and controlled promotion
      verification/      # deterministic typed assertions and outcome resolution
      evidence/          # checkpoint capture, manifests, hashes and integrity interfaces
      reporting/         # approved DOCX template and evidence report population
      caching/           # scoped extraction, UI metadata and plan blueprint caches
    infrastructure/      # relational/object storage, Qwen client and secret-provider adapters
    workers/             # background discovery/planning/execution orchestration
  tests/
    unit/
    integration/
    fixtures/
frontend/
  src/
    ...                  # retain current UI components and workflow; add API adapter only as needed
```

## Layout decisions

- Keep the existing frontend experience and Vite app. Preserve current HTTP/WebSocket contracts by default. Change a contract only with explicit human approval, versioning, a compatibility window and rollback plan; avoid a visual redesign.
- Keep the new backend application isolated under `backend/app/` while the legacy files remain available for rollback and parity review. Do not delete or relocate legacy modules during the early phases.
- Keep domain models independent from FastAPI and persistence. Put external storage, Qwen, identity and secret integrations behind infrastructure interfaces. Execution secrets come from an approved backend runtime provider, never browser request payloads or source defaults.
- Keep mode boundaries explicit: Discovery observes; Catalog governs lifecycle/persistence; Mini-RAG retrieves; Planning proposes; Compilation validates/translates; Execution runs validated actions.
- Keep one UI catalog and one primary Mini-RAG. Do not add a vector database, workflow engine or separate requirements RAG without a measured, approved need.
- Do not create any packages/directories during Phase 0. Each package/module is introduced only by its implementing phase after explicit authorization.
- Decide durable storage, migrations, deployment topology and auth adapter only after the Phase 0 open decisions are resolved.

