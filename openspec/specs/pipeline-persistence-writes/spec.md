# pipeline-persistence-writes Specification

## Purpose

Real pipeline persistence: every graph run writes real ideas/scripts/videos rows via async DAOs, `approve_idea` performs a real DB commit, graph state survives backend restarts through a Postgres checkpointer, and product data (including `product_image_url`) flows ingest → state → DB.

The tables and async ORM already existed (migrations 001-003); the hole was that nothing wrote (8 tenants, 0 rows). Adds migration 004 (`products` table + `Product` ORM, DDL-as-truth), async write DAOs, async graph nodes that persist, a real approve UPDATE, and a Postgres-backed checkpointer (`thread_id = tenant_id`). Rejections now terminate the run at the distinct terminal state `term_rejected` (never re-entering scriptwriting/publish), and empty ideation candidates surface an honest, visible "no candidates" error instead of an `IntegrityError`. Product data now persists a stable `products.object_key` (not the 7-day presigned URL) and re-signs it to a working URL on every read, so the presigned expiry cannot kill the flow. MemorySaver sessions are deliberately not migrated (non-goal).

## Requirements

### Requirement: REQ-PERSIST-01 — Migration 004 + Product ORM

**User Story**: As an operator, I want a `products` table and a matching `Product` ORM so product data (name, description, `product_image_url`) is persisted per tenant.

**Motivo**: No `products` table exists in migrations 001-003; `product_image_url` is produced by product-ingest but never stored.

The system MUST add migration `004_*.sql` creating `products` (tenant FK, name, description, `product_image_url`, created_at) and a `Product` ORM model mapping exactly those columns (following the DDL-as-truth convention in `models.py`).

#### Scenario: PERSIST-01-1 — products table exists after 004

- GIVEN Postgres with migrations 001-003 applied
- WHEN migration 004 applies
- THEN a `products` table exists with `tenant_id` FK and `product_image_url` column

#### Scenario: PERSIST-01-2 — ORM/DDL column parity

- GIVEN the `Product` model imported
- WHEN its `__table__.columns` keys are collected
- THEN the set matches the 004 DDL exactly (column read-back test, per `backend-video-metric-ddl-alignment` pattern)

### Requirement: REQ-PERSIST-02 — Graph run writes real ideas/scripts/videos rows

**User Story**: As a user, I want each graph run to persist candidates, the approved script, and the video record via async DAOs, so `GET /ideas` and `GET /scripts` show real rows instead of `[]`.

**Motivo**: Tables and async ORM exist and are functional; nothing writes (8 tenants, 0 rows). Nodes only update in-memory state (`ideation.py:14-33`, `scriptwriting.py:15-30`).

The system MUST write, via async DAOs on the existing session: an `ideas` row per generated candidate; a `scripts` row (FK to the approved idea) once the script is generated; and a `videos` row (FK to the script) capturing raw/edited URIs and publish status.

#### Scenario: PERSIST-02-1 — rows land in the real tables

- GIVEN a completed graph run for a tenant
- WHEN the run finishes
- THEN `ideas` has one row per candidate, `scripts` has one row referencing the approved idea, and `videos` has one row referencing the script
- AND the rows are visible via `psql` and via the existing GETs

#### Scenario: PERSIST-02-2 — write failure is honest

- GIVEN a DAO write raises (DB error)
- WHEN the node runs
- THEN the node fails honestly with the error surfaced in logs (no silent state-only success)

### Requirement: REQ-PERSIST-03 — approve_idea is a real DB commit

**User Story**: As a user, I want clicking Aprobar to set `approval_status` on the idea row, so the DB, the graph, and the UI agree.

**Motivo**: `approve_idea` (`graph_execution.py:67-102`) is an honest no-op — it broadcasts SSE and resumes the graph but never persists. This reverses that semantics (see REQ-API-06 MODIFIED).

The system MUST, on `POST /{tenant_id}/ideas/approve` with `status=approved|rejected`, update the matching `ideas.approval_status` row and resume the graph from its checkpoint.

When idea approval is `rejected` or publish approval is `rejected`, the system MUST route the run to the distinct terminal state `term_rejected` (END, EstadoV3-compatible) instead of the next node. Rejection MUST be final for that run — no checkpoint resume may re-enter scriptwriting/publish; a re-approval requires a new run. The rejected candidate MUST remain visible in the DB (`approval_status='rejected'`) for a future run. A legal `approved` resume MUST reach scriptwriting unchanged.

#### Scenario: PERSIST-03-1 — approval commits

- GIVEN a pending `ideas` row with a real UUID
- WHEN `POST /api/v1/tenants/{tid}/ideas/approve` `{idea_id, status: "approved"}`
- THEN the row's `approval_status` becomes `approved` (asserted via psql/SQLite)
- AND the graph resumes at the idea checkpoint

#### Scenario: PERSIST-03-2 — rejection commits too

- GIVEN the same endpoint with `status: "rejected"`
- WHEN it runs
- THEN the row's `approval_status` becomes `rejected` and the run ends at `term_rejected` — no idea is promoted to scriptwriting (now reachable)

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

### Requirement: REQ-PTT-03 — Empty-candidates honesty

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

### Requirement: REQ-PERSIST-04 — Postgres checkpointer (state survives restart)

**User Story**: As an operator, I want graph state persisted in Postgres (via `langgraph-checkpoint-postgres`, its own table), so an interrupted run resumes after a backend restart.

**Motivo**: `graph_execution.py:12,20-21` uses a global `MemorySaver`; all state is lost on restart. MemorySaver sessions are deliberately not migrated (non-goal).

The system MUST compile the graph with a Postgres-backed checkpointer keyed by `thread_id = tenant_id`; a paused run MUST be resumable from the same thread after a backend restart.

#### Scenario: PERSIST-04-1 — resume after restart

- GIVEN a run paused at `human_approval_idea`
- WHEN the backend restarts and the same thread_id resumes
- THEN execution continues from the checkpoint with prior state intact

#### Scenario: PERSIST-04-2 — old in-memory sessions discarded

- GIVEN pre-change MemorySaver history
- WHEN the saver is swapped to Postgres
- THEN no migration of those sessions is attempted (documented, non-goal)

### Requirement: REQ-PERSIST-05 — product data persists `object_key` and re-signs on read

**User Story**: As a user, I want my product image reference to survive — a stable `object_key` persisted, re-signed to a working URL on every read — so the 7-day presigned URL expiry cannot kill the flow (RISK-04, RESILIENCE-008).

**Motivo**: `product_image_url` persisted a 7-day presigned URL that dies; the LLM prompt and downstream consumers receive dead URLs. Migration 005 (additive, nullable `products.object_key`) plus re-sign-on-read keeps every URL real.

The system MUST persist `products.object_key` (not the presigned URL) via migration `005_*.sql` (additive nullable column, fresh volumes via `initdb.d`; documented manual `psql` apply for existing dev DBs). `upsert_product` MUST store `object_key`. Read paths MUST re-sign via `presigned_get_object`, honoring `MINIO_PUBLIC_ENDPOINT`, and the API MUST keep returning a working signed URL. Legacy rows with `object_key` NULL MUST fall back to the stored `product_image_url`. The LLM prompt (`video_prompt_crew`) MUST receive working URL text. The pipeline MUST continue normally when no product is ingested.

(Previously: REQ-PERSIST-05 wired the 7-day presigned `product_image_url` from ingest into graph state and the `products` row; nothing was ever re-signed.)

#### Scenario: PERSIST-05-1 (updated) — product persists object_key

- GIVEN a product-ingest response with an image
- WHEN the product is upserted (`/graph/run` or ingest)
- THEN the `products` row stores `object_key` — not the presigned URL

#### Scenario: PERSIST-05-2 (unchanged) — no product: graceful TEXT_TO_VIDEO

- GIVEN no product ingested
- WHEN the graph runs
- THEN the pipeline completes without error on the text-to-video path

#### Scenario: SH-05-3 — read re-signs a working URL

- GIVEN a `products` row with `object_key`
- WHEN the product is read (API response / downstream consumer)
- THEN the URL is freshly presigned (`X-Amz-Signature=`), honoring `MINIO_PUBLIC_ENDPOINT`

#### Scenario: SH-05-4 — legacy rows fall back to stored URL

- GIVEN a pre-005 row with `object_key` NULL and a stored `product_image_url`
- WHEN it is read
- THEN the stored URL is used as fallback — no break, no fabrication

#### Scenario: SH-05-5 — LLM prompt receives working URL text

- GIVEN `video_prompt_crew` runs with a product image
- WHEN the storyboard/prompt is built
- THEN the prompt contains a working (re-signed) URL text, never the expired one