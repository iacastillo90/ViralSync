# pipeline-persistence-writes Specification

## Purpose

Real pipeline persistence: every graph run writes real ideas/scripts/videos rows via async DAOs, `approve_idea` performs a real DB commit, graph state survives backend restarts through a Postgres checkpointer, and product data (including `product_image_url`) flows ingest → state → DB.

The tables and async ORM already existed (migrations 001-003); the hole was that nothing wrote (8 tenants, 0 rows). Adds migration 004 (`products` table + `Product` ORM, DDL-as-truth), async write DAOs, async graph nodes that persist, a real approve UPDATE, and a Postgres-backed checkpointer (`thread_id = tenant_id`). MemorySaver sessions are deliberately not migrated (non-goal).

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

#### Scenario: PERSIST-03-1 — approval commits

- GIVEN a pending `ideas` row with a real UUID
- WHEN `POST /api/v1/tenants/{tid}/ideas/approve` `{idea_id, status: "approved"}`
- THEN the row's `approval_status` becomes `approved` (asserted via psql/SQLite)
- AND the graph resumes at the idea checkpoint

#### Scenario: PERSIST-03-2 — rejection commits too

- GIVEN the same endpoint with `status: "rejected"`
- WHEN it runs
- THEN the row's `approval_status` becomes `rejected` and no idea is promoted to scriptwriting

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

### Requirement: REQ-PERSIST-05 — product data flows ingest → state → DB (data wiring only)

**User Story**: As a user, I want the `product_image_url` captured at product-ingest to reach graph state and persist, so the render path can later switch to IMAGE_TO_VIDEO.

**Motivo**: `product_image_url` exists in `AgencyState` (`graph.py:30`) but nothing populates it; the frontend never forwards the ingest result. LLM-composed video metadata (title/narrative) is explicitly OUT of scope — reserved extension point.

The system MUST accept `product_image_url` on `/graph/run`, place it in graph state, and persist it with the `products` row; the pipeline MUST continue normally when it is absent.

#### Scenario: PERSIST-05-1 — image URL persists with the product

- GIVEN a product-ingest response with `product_image_url`
- WHEN `/graph/run` starts and the product is persisted
- THEN the `products` row stores the URL and state carries it downstream

#### Scenario: PERSIST-05-2 — no product: graceful TEXT_TO_VIDEO

- GIVEN no product ingested (`product_image_url` empty)
- WHEN the graph runs
- THEN the pipeline completes without error on the text-to-video path