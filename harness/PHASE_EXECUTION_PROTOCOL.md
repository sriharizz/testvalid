# Phase Execution Protocol

## Purpose
Keep coding-agent execution consistent across models, IDEs and fresh conversations. This protocol supplements (does not replace) `AGENTS.md` and the Master Spec.

## Before starting a phase
1. Confirm repository root, active branch/worktree and clean/known working-tree state. Never overwrite unrelated user changes.
2. Read `AGENTS.md`, this protocol, `harness/PROJECT_STATUS.md`, the relevant decision-log entries and the requested `harness/build/phase-NN-*.md`.
3. Read only the referenced Master Spec sections and exact repository contracts/files needed for this phase.
4. Confirm the previous phase is marked **Approved** in `PROJECT_STATUS.md`. Phase 0 must be approved before Phase 1. If approval is missing, stop and ask for it; do not infer approval from task completion.
5. State the phase objective, allowed scope, intended files, acceptance criteria and verification commands before editing.

## During execution
- Stay inside the phase's in-scope items and files. If an unavoidable change crosses scope, explain why and request approval before making it.
- Prefer small, coherent changes with focused tests. Avoid speculative abstractions and unnecessary dependencies.
- Preserve user changes. Do not use destructive commands (`rm -rf`, broad reset/checkout/clean, migration reset, force push) without explicit approval.
- Do not install new production dependencies, run production mutations, change secrets, deploy or modify external services without explicit approval.
- Use targeted repository searches. Do not recursively print or read the entire repository.
- Keep logs free of credentials, tokens, PHI/PII and unnecessary personal data.
- Do not make up outputs. If a command cannot be run, record it as skipped and explain the blocker.
- For any phase that reads/transforms user-authored or document content, preserve original bytes/text and provenance; do not filter by keywords, phrases, regex or ambiguity-word lists. Account for each source segment and keep derived interpretation separate. Include unfamiliar-content fixtures where that phase handles ingestion.

## Verification protocol
1. Identify the smallest meaningful failing test/check first where practical (red).
2. Implement the minimum change to satisfy it (green).
3. Refactor only within the approved scope and rerun tests.
4. Run phase-specific tests and all required earlier-phase regression tests.
5. Run relevant static checks (format, lint, type checking, security scan) only when present or approved; do not invent project commands.
6. Record exact command, exit status, test counts and relevant output. Separate observed results from expected results.
7. Confirm `git diff --check` and inspect the scoped diff for accidental or generated-file changes.

## Phase completion and handoff
Update:
- `harness/PROJECT_STATUS.md`: phase status, date, actual outcome and approval state.
- `harness/BUILD_LOG.md`: exact verification evidence and changed files.
- `harness/DECISION_LOG.md`: only material decisions/supersessions, with rationale and approval source.
- `harness/context/phase-NN-<slug>-context.md`: material discoveries and unresolved information needed by future phases. Do not copy transcripts or routine output.

Report:
1. Phase/status.
2. Scope and changed files.
3. Tests/checks actually run with actual results.
4. Tests not run and why.
5. Acceptance criteria met/not met.
6. Security, privacy, evidence and recovery considerations.
7. Deviations, limitations and unresolved decisions.
8. Updated tracking paths.
9. Explicit stop: **awaiting human approval for the next phase**.

## Resuming with a different AI agent
The new agent must read only:
1. Root `AGENTS.md`.
2. `harness/PHASE_EXECUTION_PROTOCOL.md`.
3. `harness/PROJECT_STATUS.md`.
4. Relevant `harness/DECISION_LOG.md` entries.
5. Last approved phase context file and build-log entry.
6. The next phase card and its referenced Master Spec sections.
7. Exact source files/contracts needed by that phase.

Do not rely on previous chat history or ask the user to repeat already-recorded decisions. Verify approvals using the status/decision records, not conversational assumptions.

## Authority and ambiguity
- Current explicit user instruction can authorize a phase or change the design.
- A phase card does not authorize future phases.
- A code agent cannot self-approve a phase.
- If the Master Spec, a phase card, user approval or current repository contract conflict, stop the dependent work, record the conflict and ask for one precise decision.
