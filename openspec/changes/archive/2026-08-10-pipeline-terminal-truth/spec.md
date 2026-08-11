# Pipeline Terminal Truth — Spec

Delta covering three capabilities: MODIFIED `api-publish-wiring` (REQ-PUBLISH-02 gains write-back), MODIFIED `pipeline-persistence-writes` (REQ-PERSIST-03 rejection now terminates; ADDED empty-candidates honesty), MODIFIED `api-ideas-scripts-brain-get` (REQ-API-06 0-row approve distinguishable). Behavior is specified; implementation is design's job.

Locked decisions baked in: no migration (write-back on the existing `videos` row, status stays CHECK-compatible `approved`); rejection terminates at the distinct terminal state `term_rejected` and is FINAL per run (re-approval requires a new run); empty candidates surface an honest "no candidates" error, never `IntegrityError`; 0-row approve is a distinct non-202 error.

## Requirements

### Capability: `api-publish-wiring` (MODIFIED — extends REQ-PUBLISH-02)

#### Requirement: REQ-PTT-01 — Publish write-back persists on the videos row

**User Story**: As an operator, I want a successful publish to persist where it happened, so the `videos` row is the source of truth and the post id survives a backend restart.

**Motivo**: `node_publish` returns `published_post_id` to state only (`publish.py:115-117`); `insert_video` hardcodes `pending` (`daos.py:134`) and nothing ever UPDATEs `instagram_post_id`/`published_at` (columns exist, `models.py:158-159`; `publish_approval_status` CHECK only allows `pending|approved|rejected`).

The system MUST, on a successful publish (post id obtained per REQ-PUBLISH-02), persist `instagram_post_id` and `published_at` on the `videos` row identified by `video_id` in state, leaving `publish_approval_status` as `approved` (existing CHECK value — no new status value, no migration). On publish failure the row MUST remain unchanged (never a partial write). When `video_id` is absent from state (replay/resume), `node_publish` MUST NOT crash and MUST NOT perform any write-back (no fabricated post id ever persisted).

#### Scenario: PTT-01-1 — success persists both fields

- GIVEN a `videos` row for the tenant and `video_id` + `published_post_id` in state, publisher returns a real post id
- WHEN `node_publish` succeeds
- THEN the row's `instagram_post_id` equals the returned id and `published_at` is set
- AND `publish_approval_status` is `approved`, verifiable via psql/SQLite read-back

#### Scenario: PTT-01-2 — publish failure leaves the row untouched

- GIVEN a publisher failure or missing token (existing honest errors)
- WHEN `node_publish` raises
- THEN the row keeps NULL `instagram_post_id`/`published_at` and prior status — no partial write

#### Scenario: PTT-01-3 — no video_id on replay/resume is safe

- GIVEN state without `video_id` (replay/legacy checkpoint)
- WHEN `node_publish` runs and succeeds
- THEN no UPDATE is issued and no crash occurs — no false write-back

### Capability: `pipeline-persistence-writes` (MODIFIED — extends REQ-PERSIST-03; ADDED)

#### Requirement: REQ-PTT-02 — Honest rejection terminal terminates the run

**User Story**: As an operator, I want an explicit rejection to end the run honestly, so a rejected idea is never silently promoted to scriptwriting and no LLM work is spent on a dead run.

**Motivo**: Edges are unconditional (`graph.py:55-59`); a rejection resume (`graph_execution.py:180/213`) still walks into scriptwriting/publish, making PERSIST-03-2 unreachable.

The system MUST, when idea approval is `rejected` or publish approval is `rejected`, route the run to the distinct terminal state `term_rejected` (END, EstadoV3-compatible) instead of the next node. Rejection MUST be final for that run — no checkpoint resume may re-enter scriptwriting/publish; a re-approval requires a new run. The rejected candidate MUST remain visible in the DB (`approval_status='rejected'`) for a future run. A legal `approved` resume MUST reach scriptwriting unchanged (PERSIST-03-1/API-06-1 preserved).

#### Scenario: PTT-02-1 — rejected idea: terminal, no script, no LLM spend

- GIVEN a run paused at `human_approval_idea` and `POST ideas/approve {status: "rejected"}`
- WHEN the resume resolves
- THEN the run ends at `term_rejected` and no `scripts` row is created (PERSIST-03-2 now reachable)
- AND the scriptwriting crew is never invoked and the idea's `approval_status` is `rejected` in the DB

#### Scenario: PTT-02-2 — rejected publish: terminal, no write-back

- GIVEN a run paused at `human_approval_publish` and `POST publish/approve {status: "rejected"}`
- WHEN the resume resolves
- THEN the run ends at `term_rejected`, the publisher is never invoked, and no write-back occurs (REQ-PTT-01 not fired)

#### Scenario: PTT-02-3 — legal approval still reaches scriptwriting

- GIVEN an existing pending `ideas` row approved with `status: "approved"` (real id)
- WHEN the resume resolves
- THEN the run proceeds to scriptwriting as today — the approved path is unchanged

#### Requirement: REQ-PTT-03 — Empty-candidates honesty

**User Story**: As an operator, I want zero viable candidates to be a visible, actionable error — not a crash — so I can retry with another niche.

**Motivo**: `selected_idea={}` when `ideas` is empty (`ideation.py:33`) feeds a NULL FK into `insert_script` (`scriptwriting.py:32`) → `IntegrityError` (`models.py` FK), invisible to the frontend.

The system MUST, when no idea passes the 5/50 filter (empty candidates), terminate the run with an honest, visible "no candidates" error state — MUST NOT raise `IntegrityError` and MUST NOT pause for approval. The error state MUST be distinguishable (defined, uniform API behavior) so the frontend can surface it and force a retry with another niche. The valid path MUST be unaffected.

#### Scenario: PTT-03-1 — empty set surfaces an honest no-candidates error

- GIVEN the ideation crew returns zero ideas passing the 5/50 filter
- WHEN `node_ideation` runs
- THEN the run terminates in a visible "no candidates" error state (never `IntegrityError`, never paused)
- AND no `ideas`/`scripts`/`videos` rows are written for that run

#### Scenario: PTT-03-2 — valid candidates proceed unchanged

- GIVEN at least one idea passes the 5/50 filter
- WHEN `node_ideation` runs
- THEN the pipeline proceeds to `human_approval_idea` exactly as today

### Capability: `api-ideas-scripts-brain-get` (MODIFIED — extends REQ-API-06)

#### Requirement: REQ-PTT-04 — Honest 0-row approve

**User Story**: As an operator, I want the frontend to tell a real commit apart from a no-op, so approving a stale/unknown idea is never mistaken for progress.

**Motivo**: `approve_idea` returns `202` even when `update_idea_approval` affected 0 rows (`graph_execution.py:168-174`), and `status` is a free string (`graph_execution.py:117-119`).

The system MUST return a distinct non-`202` error (404 or 409, per design — never 202) when `ideas/approve` matches no row (unknown or stale `idea_id`), and MUST NOT resume the graph for a 0-row approve. A valid `idea_id` MUST keep returning 202 and committing (`approval_status`) as today. `status` MUST be restricted to the allowlist `approved|rejected`; anything else MUST be rejected without commit or resume. The change is non-breaking/additive for the frontend: valid approvals behave exactly as before.

#### Scenario: PTT-04-1 — valid id keeps 202/commit

- GIVEN an existing pending `ideas` row
- WHEN `POST ideas/approve {idea_id, status: "approved"}` resolves
- THEN the response is 202 and the row's `approval_status` becomes `approved` (unchanged contract)

#### Scenario: PTT-04-2 — unknown/stale id is a distinct non-202

- GIVEN a valid-format `idea_id` matching no row (or a stale id)
- WHEN `POST ideas/approve` resolves
- THEN the response is 404 or 409 (never 202) and the graph is NOT resumed

#### Scenario: PTT-04-3 — invalid status rejected

- GIVEN `status` outside `{approved, rejected}`
- WHEN `POST ideas/approve` resolves
- THEN the request is rejected (4xx validation), no commit and no resume occur

## Capability flags

| Capability | Flag | Kind |
|------------|------|------|
| `api-publish-wiring` | update | REQ-PTT-01 extends REQ-PUBLISH-02 |
| `pipeline-persistence-writes` | update | REQ-PTT-02 extends REQ-PERSIST-03; REQ-PTT-03 added |
| `api-ideas-scripts-brain-get` | update | REQ-PTT-04 extends REQ-API-06 |

## Traceability

| Requirement | Scenarios | Anchor |
|-------------|-----------|--------|
| REQ-PTT-01 | PTT-01-1, PTT-01-2, PTT-01-3 | `api-publish-wiring` REQ-PUBLISH-02 (+ `pipeline-persistence-writes` REQ-PERSIST-02 videos clause) |
| REQ-PTT-02 | PTT-02-1, PTT-02-2, PTT-02-3 | `pipeline-persistence-writes` REQ-PERSIST-03 (PERSIST-03-2 reachable) |
| REQ-PTT-03 | PTT-03-1, PTT-03-2 | `pipeline-persistence-writes` (ADDED) |
| REQ-PTT-04 | PTT-04-1, PTT-04-2, PTT-04-3 | `api-ideas-scripts-brain-get` REQ-API-06 |

## Risks / notes

- **e2e 202-assertion vs REQ-PTT-04 (spec-level, not covered by locked decisions)**: `test_full_pipeline.py:70-71` posts non-UUID `"idea-e2e-001"` (0-row) and asserts 202 — under REQ-PTT-04 that becomes non-202. The resume semantics stay green, but the e2e status assertions MUST be updated in the same change (use a real persisted idea id or assert the new honest code).
- **Status value discipline**: SQLite has no CHECK; tests must assert `approved` (never `published`) so prod CHECK (`001_init_schema.sql:132-133`) keeps passing (locked decision #1).
- **Reject-vs-pending signal**: resume payload `{"idea_approved": bool}` conflates "rejected" with "not yet" — the spec defines the observable terminal (`term_rejected`); the disambiguating payload key is design's call.
- **Error-surface wire shape**: "no candidates" and `term_rejected` visibility (SSE event vs `graph_error`) is design's open item — spec fixes state/behavior, not wire format; zero-token constraint means tests fake crews/HTTP.