# api-ideas-scripts-brain-get Specification

## Purpose

Backend tenant-scoped GET endpoints for ideas/scripts/brain, real metrics shape, dev auth guard, real idea-approval commits, honest publish approval.

Adds three tenant-scoped GET endpoints (`/ideas`, `/scripts`, `/brain`) with honest 200-empty behavior; defines the real metrics GET shape (which previously 503'd); fixes the dev auth guard so real tenant UUIDs work without a JWT in dev while production stays fail-closed; and makes approve/publish POSTs honest — `ideas/approve` performs a real `approval_status` UPDATE (reversing the earlier 202 no-op), `publish/approve` never fabricates identities, and neither endpoint invents DB writes it did not perform.

- All routers mount under `_TENANT_GUARD = [Depends(verify_tenant_access)]` via `include_router` (`main.py:70-77`); new GET routers follow the same pattern.
- `verify_tenant_access` (`security/auth.py:114-137`) 403s unless `current_user["tenant_id"] == url tenant`. `get_current_user` (`auth.py:91-98`) with no Bearer token returns a hardcoded `{"tenant_id": "default_tenant"}` in dev — the source of the 403 on real UUIDs. `TenantContextMiddleware` already resolves the dev tenant (X-Tenant-ID header, else URL path) into `request.state.tenant_id`.
- Approve endpoints exist: `routers/graph_execution.py:67-129` (`POST /{tid}/ideas/approve`, `POST /{tid}/publish/approve`), currently 200 and fabricating `published_post_id`.
- `GET /{tid}/metrics` (`routers/metrics.py:29-45`) currently 503s; the response-shape contract below rides on the ORM alignment (see `backend-video-metric-ddl-alignment`).

## Requirements

### Requirement: REQ-API-1 — GET /api/v1/tenants/{tenant_id}/ideas

The system MUST respond `200` to `GET /api/v1/tenants/{tenant_id}/ideas` (guarded by the systemic `_TENANT_GUARD`), returning a JSON array of Idea objects queried from the `ideas` table, shaped by DDL 001 (`id, tenant_id, niche_id, texto, gancho, entendible_nino_5_anos, interesa_50_de_100, universalidad, intensidad, claridad, shareability, distribucion, alineacion, rum_score, rum_threshold_id, passes_threshold, approval_status, origen_reintento_de, created_at`). MUST return `200 []` when the tenant has zero rows, `503` only on DB failure, and MUST NEVER return fabricated rows.

#### Scenario: API-GET-1 — Postgres-real curl 200 (empty tenant)

- GIVEN a dev backend (`AGENCY_ENV=dev`) connected to Postgres with migrations 001+002 applied and a real tenant UUID with zero ideas
- WHEN `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/tenants/<uuid>/ideas -H "X-Tenant-ID: <uuid>"`
- THEN the response code is `200` and the body is `[]`

#### Scenario: API-GET-2 — Rows return the DDL shape

- GIVEN one `ideas` row exists for the tenant
- WHEN `GET /api/v1/tenants/{tid}/ideas` resolves
- THEN the HTTP status is `200` and every item has exactly the DDL 001 fields (asserted key-by-key in pytest)

#### Scenario: API-GET-3 — pytest: dev real-UUID 200, prod 401

- GIVEN pytest running with `backend.main.app` via httpx ASGITransport
- WHEN no Authorization header is sent and `AGENCY_ENV=dev`
- THEN `GET /api/v1/tenants/<uuid>/ideas` returns `200` (empty list on the test DB)
- AND with `AGENCY_ENV=production` the same call without a JWT returns `401`

#### Scenario: API-GET-4 — Cross-tenant stays fail-closed

- GIVEN a valid JWT minted for tenant B
- WHEN `GET /api/v1/tenants/A/ideas` is called with it
- THEN the response is `403`

### Requirement: REQ-API-2 — GET /api/v1/tenants/{tenant_id}/scripts

The system MUST respond `200` to `GET /api/v1/tenants/{tenant_id}/scripts`, returning an array shaped per DDL 001 scripts table (`id, tenant_id, idea_id, gancho_0_5s, contexto_5_30s, moraleja_30_50s, cta_50_60s, keyword, created_at`), `200 []` when empty, `503` only on DB failure, never fabricated.

#### Scenario: API-02-1 — Postgres-real curl 200

- GIVEN tenant UUID with scripts rows
- WHEN `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/tenants/<uuid>/scripts -H "X-Tenant-ID: <uuid>"`
- THEN the code is `200` with the DDL script fields per item
- AND with zero rows the body is `[]`

#### Scenario: API-02-2 — pytest dev-guard + DB error

- GIVEN the default pytest environment (FORCE_SQLITE, `AGENCY_ENV=dev`)
- WHEN `GET /api/v1/tenants/<uuid>/scripts` runs without a JWT
- THEN the status is `200` and the body is a list
- GIVEN the DB layer raises
- WHEN the same GET runs
- THEN the status is `503`

### Requirement: REQ-API-3 — GET /api/v1/tenants/{tenant_id}/brain

The system MUST respond `200` to `GET /api/v1/tenants/{tenant_id}/brain` with an object shaped `{"tenant_id": ..., "status": "no_data", "chunks": []}` when the tenant has no brain data. There is no `brain` table in migrations; the endpoint MUST NOT invent embeddings/vector counts and MUST NOT return a 404 for a real tenant.

#### Scenario: API-03-1 — honest empty object

- GIVEN a real tenant UUID
- WHEN `curl http://localhost:8000/api/v1/tenants/<uuid>/brain -H "X-Tenant-ID: <uuid>"`
- THEN the code is `200` and the body contains `"chunks": []` and a truthful `status` (`no_data`/`ok`) — never a hardcoded count

#### Scenario: API-03-2 — pytest shape gate

- GIVEN pytest running in dev mode
- WHEN the endpoint is hit without a JWT
- THEN the response is `200` and `body["chunks"]` is a list
- AND no literal such as `1240` appears in the response

### Requirement: REQ-API-4 — GET /api/v1/tenants/{tenant_id}/metrics returns the real flat shape

The `/metrics` GET MUST return `200` with a flat array `[{"video_id", "views_72h", "likes", "comments", "shares", "ratio_relativo", "classification", "action_taken", "captured_at"}]` (per migration 002 columns), an empty `[]` when no rows, and MUST NOT return the legacy nested `metrics_72h` payload or a `503` against Postgres with 002 applied. `/metrics/72h` MUST keep aggregating from the same aligned columns and never 503 on a healthy DB.

#### Scenario: API-04-1 — Postgres-real curl 200 (no more 503)

- GIVEN Postgres with migration 002 applied
- WHEN `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/tenants/<uuid>/metrics -H "X-Tenant-ID: <uuid>"`
- THEN the code is `200` (never `503`) and the body is the flat list above (empty when no rows)

#### Scenario: API-04-2 — pytest asserts the flat contract

- GIVEN pytest with SQLite and one `video_metrics` row for the tenant
- WHEN `GET /api/v1/tenants/{uuid}/metrics`
- THEN `200` and `body[0]` has exactly the flat fields (`views_72h`, `ratio_relativo`, ...) and no `metrics_72h` key

### Requirement: REQ-API-05 — Dev auth guard resolves the requested tenant; prod stays strict

The system MUST, when `AGENCY_ENV` is `dev`/`development` and no JWT is present, bind the current user to the tenant of the request (the X-Tenant-ID header or the URL tenant resolved by the middleware) instead of the hardcoded `default_tenant`, so `verify_tenant_access` passes for real UUIDs. In any non-dev environment the fallback MUST NOT exist: a missing or invalid JWT MUST return `401`, and a cross-tenant user MUST still get `403`.

#### Scenario: API-05-1 — dev real-UUID GET returns 200

- GIVEN `AGENCY_ENV=dev`, no Authorization header, real tenant UUID in URL
- WHEN `GET /api/v1/tenants/<uuid>/ideas`
- THEN HTTP `200` (the dev fallback bound the user to `<uuid>`)

#### Scenario: API-05-2 — prod without JWT returns 401

- GIVEN `AGENCY_ENV=production`
- WHEN the same GET is issued without Authorization
- THEN the response is `401` (never a succeeded fallback)

#### Scenario: API-05-3 — dev cross-tenant still 403

- GIVEN `AGENCY_ENV=dev` and request X-Tenant-ID = B while URL tenant = A
- WHEN the GET runs
- THEN the response is `403`

### Requirement: REQ-API-06 — Approve/publish: real commits; no fabricated ids

(Previously: both approve endpoints returned `202` queued-intent no-ops writing nothing — the semantic this change reverses for idea approval, per `pipeline-persistence-writes` REQ-PERSIST-03.)

`POST /api/v1/tenants/{tid}/ideas/approve` MUST perform a real `ideas.approval_status` UPDATE (per REQ-PERSIST-03) and return `202 Accepted` with the existing SSE checkpoint/resume contract. `POST /api/v1/tenants/{tid}/publish/approve` MUST NOT fabricate `published_post_id`/`ig_reel_*`; it MUST only resume publish when valid tokens exist in state, and MUST surface an honest error otherwise. Neither endpoint MAY invent identifiers.

#### Scenario: API-06-1 — approve commits for real

- GIVEN a pending `ideas` row
- WHEN `POST /api/v1/tenants/{tid}/ideas/approve` `{idea_id, status: "approved"}`
- THEN the response signals the committed approval (202 accepted + resume, per existing SSE contract)
- AND the row's `approval_status` is `approved` in the DB (no-op removed)

#### Scenario: API-06-2 — publish approval without tokens is honest

- GIVEN no IG credentials in state
- WHEN `POST /api/v1/tenants/{tid}/publish/approve`
- THEN the response contains no `published_post_id`, `ig_reel_*`, or any fabricated resource
- AND publish does not pretend to run (honest queued/error state)

## Acceptance Criteria

- [ ] `curl` on all four GETs returns 200 over real Postgres (ideas/scripts/brain/metrics; metrics no longer 503)
- [ ] `pytest` suite green with added dev-200/prod-401 and flat-metrics tests
- [ ] No mock/fabricated row is returned by any new endpoint
- [ ] Approve/publish are honest: `ideas/approve` commits `approval_status` (`202` + resume); `publish/approve` fabricates no identifiers

## Notes on proof

- New pytest: `agency/tests/unit/test_api_ideas_scripts_brain.py` (httpx ASGITransport, dev 200 + prod 401 scenarios); the existing `test_get_metrics_endpoint` in `test_fastapi_endpoints.py` must be tightened so `503` is no longer an accepted response.
- Manual proof in dev with Postgres: the four curl commands above.