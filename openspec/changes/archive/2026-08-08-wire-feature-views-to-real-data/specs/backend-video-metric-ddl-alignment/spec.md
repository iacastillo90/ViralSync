# Delta for backend-video-metric-ddl-alignment

**id**: `backend-video-metric-ddl-alignment`
**status**: approved
**title**: Align VideoMetric ORM to migration 002 DDL and restore `/metrics` to 200

## Summary

The `VideoMetric` ORM class currently declares columns that do not exist in the real schema, making every query against Postgres raise `UndefinedColumn` and surface as HTTP 503. This delta aligns the ORM exactly to migration 002 and locks the alignment with a column-level read-back test so drift cannot recur.

## Preamble (verified in code)

- Migration `002_add_video_metrics_and_fix_leads.sql` declares: `video_metrics (id, tenant_id, video_id, views_72h BIGINT NOT NULL DEFAULT 0, likes BIGINT DEFAULT 0, comments BIGINT DEFAULT 0, shares BIGINT DEFAULT 0, ratio_relativo NUMERIC(6,3) NOT NULL DEFAULT 1.000, classification TEXT NOT NULL CHECK (IN ('ROJO','AMARILLO','VERDE')), action_taken TEXT, captured_at TIMESTAMPTZ NOT NULL DEFAULT now())`.
- `db/models.py:90-105` (`VideoMetric`) instead declares: `published_at, views, followers_at_posting, leads_generated, completion_rate, engagement_rate, classification, action_taken, created_at` — seven of them missing from the DDL.
- `routers/metrics.py:29-45` and `:69-126` select those phantom columns, hence 503.
- `agency/tests/unit/test_fastapi_endpoints.py:53` currently tolerates `(200, 503)` — the 503 branch must become a failure after this change.

## ADDED Requirements

### Requirement: REQ-VID-1 — ORM VideoMetric matches migration 002 exactly

The `VideoMetric` model MUST declare exactly the columns of migration 002 — `id, tenant_id, video_id, views_72h, likes, comments, shares, ratio_relativo, classification, action_taken, captured_at` — with DDL-consistent nullability/defaults (`views_72h` NOT NULL default 0, `ratio_relativo` NOT NULL default 1.000, `classification` NOT NULL, `captured_at` NOT NULL), and MUST NOT declare `published_at, views, followers_at_posting, leads_generated, completion_rate, engagement_rate, created_at` or any other column absent from 002.

#### Scenario: VID-01-01 — Column-level read-back assertion

- GIVEN the `VideoMetric` model imported from `backend.db.models`
- WHEN its `__table__.columns` keys are collected
- THEN the set equals `{id, tenant_id, video_id, views_72h, likes, comments, shares, ratio_relativo, classification, action_taken, captured_at}` AND none of `{published_at, views, followers_at_posting, leads_generated, completion_rate, engagement_rate, created_at}` is present

#### Scenario: VID-01-02 — pytest regression: SELECT over the model works

- GIVEN pytest with `FORCE_SQLITE` and `init_test_db` (create_all)
- WHEN a row is inserted via the ORM using only the aligned columns and a `select(VideoMetric)` is executed
- THEN the query succeeds without `UndefinedColumn` and returns exactly the stored fields

### Requirement: REQ-VID-2 — /metrics endpoints no longer 503 on a healthy DB

With migration 002 applied, `GET /api/v1/tenants/{tid}/metrics` MUST return `200` (flat array per REQ-API-4) and `GET /api/v1/tenants/{tid}/metrics/72h` MUST return a 2xx aggregate / `{"status": "no_data"}` — neither may return 503 when the DB is reachable; both queries MUST select only the aligned columns.

#### Scenario: VID-02-01 — Postgres-real curl 200

- GIVEN Postgres with migration 002 applied (11 tables present)
- WHEN `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/tenants/<uuid>/metrics -H "X-Tenant-ID: <uuid>"`
- THEN the code is `200` (a health check exhibiting the previous behavior would have returned `503`)

#### Scenario: VID-02-02 — pytest asserts 200, not 503

- GIVEN the updated `test_get_metrics_endpoint` in the backend test suite
- WHEN the test asserts the response
- THEN `503` is no longer an accepted status — only `200` (empty list or aligned rows)

## Acceptance Criteria

- [ ] `pytest agency/tests` green; the metrics endpoint test no longer tolerates 503
- [ ] `curl` over real Postgres returns 200 for `/metrics` (and `/metrics/72h`)
- [ ] ORM/DDL drift is impossible to reintroduce silently (read-back test)

## Notes on proof

- New test: `agency/tests/unit/test_video_metric_orm_alignment.py` (column-set assertion + insert/select regression).
- Modified test: `agency/tests/unit/test_fastapi_endpoints.py::test_get_metrics_endpoint` (drop `503` from the accepted set).
- Live check: dev backend + Postgres with 002 applied; the four curl commands in REQ-API-4/VID-02-01.