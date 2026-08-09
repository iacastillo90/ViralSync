# Design: Wire Feature Views to Real Data

Change `wire-feature-views-to-real-data`. Maps proposal approach and the three delta specs (`api-ideas-scripts-brain-get`, `backend-video-metric-ddl-alignment`, `frontend-feature-views-real-data`) into two chained PR slices: **Slice 1 backend** (fix the data layer + new GETs + dev-auth guard + honest approvals) and **Slice 2 frontend** (wire the five views + dashboard cards to those GETs). No mocks, no fabricated rows; honest loading/error/empty is the target UX.

## Architecture Decisions

### D1 — Dev-auth binding mechanics (`backend/security/auth.py:91-98`)

| Option | Tradeoff | Decision |
|---|---|---|
| **Bind dev fallback to the requested tenant** (`request.state.tenant_id`, already resolved by `TenantContextMiddleware` auth.py:177-184 from X-Tenant-ID header → URL path) | Smallest diff, keeps `verify_tenant_access` (auth.py:114-137) byte-identical; fail-closed preserved | **Chosen** |
| Dev full bypass of the guard | Opens prod-style behavior risk; rejected (proposal Q1 option B) | Rejected |
| Keep 403 + ship a dev JWT-maker script | Extra tooling, spec demands dev 200 | Rejected |

Change `get_current_user` (`auth.py:91-98`) to accept `request: Request` and, only when `AGENCY_ENV == "dev"` and no Bearer credentials, return `{"sub": "usr_dev_001", "tenant_id": getattr(request.state, "tenant_id", None), "role": "admin"}` instead of the hardcoded `"default_tenant"` (auth.py:95). `verify_tenant_access` and the production branch (auth.py:96) stay untouched. `AGENCY_ENV` is a **module constant loaded at import** (auth.py:22) — tests MUST `monkeypatch.setattr(backend.security.auth, "AGENCY_ENV", "prod")`, never only `os.environ`. Mechanical before/after:

| Scenario | Env | Auth | X-Tenant-ID | URL | Before | After |
|---|---|---|---|---|---|---|
| GET real UUID, no JWT, header=UUID | dev | none | UUID | UUID | 403 (default_tenant≠UUID) | **200** |
| GET real UUID, no JWT, no header | dev | none | — | UUID | 403 | **200** (URL fallback) |
| Header=tenant B, URL=A | dev | none | B | A | 403 | 403 |
| JWT of B, URL=A | any | Bearer B | — | A | 403 | 403 (unchanged) |
| No/ invalid JWT | prod | none | any | UUID | 401 | 401 (unchanged) |

### D2 — VideoMetric ORM ↔ migration 002 (drift-proof)

| Option | Tradeoff | Decision |
|---|---|---|
| Replace phantom columns with exactly 002 (`views_72h, likes, comments, shares, ratio_relativo, classification, action_taken, captured_at`; drop `published_at, views, followers_at_posting, leads_generated, completion_rate, engagement_rate, created_at`), following the `Lead` docstring precedent (`models.py:68-73`) | / | **Chosen** |
| Leave ORM, use raw SQL selects | Duplication + future drift; rejected | Rejected |
| Lock alignment with a column-set read-back test | **Chosen** (REQ-VID-01-01/02) | |

### D3 — `Idea` ORM also aligned to DDL 001 (required discovery)

`Idea` (`models.py:39-48`) declares `niche/score_rum(→rum)/status/created_at` but DDL 001 `ideas` (`001_init_schema.sql:70-100`) has `niche_id, gancho, … rum_score, rum_threshold_id, passes_threshold, approval, override_reintento_de`. Any `select(Idea)` against Postgres with the current ORM raises `UndefinedColumn` (same mechanism as the metrics 503). REQ-API-1 demands 200 + DDL-001-shaped rows, so the `Idea` ORM MUST be re-aligned to DDL 001 (spec authors missed this — it is required for the Postgres curl 200). `Script` (`models.py:51-62`) already matches DDL 001 scripts exactly — no change.

### D4 — `/metrics` flat shape + `/metrics/72h` aggregate

`GET /tenants/{tid}/metrics` returns a flat array (per REQ-API-4):
```
[{"video_id","views_72h","likes","comments","shares","ratio_relativo","classification","action_taken","captured_at"}]
```
No `metrics_72h` nested key (delete `published_at` projection too). Consumers synced: `MetricClassificationCard.jsx:35,39`, `page.js:397-407` switch `item.metrics_72h.views` → `item.views_72h`, `item.metrics_72h.ratio` → `item.ratio_relativo`.

`/metrics/72h` (lean: retains `status: success|no_data` for `test_enterprise_phases_0_to_5.py:67`) aggregates the aligned columns over the **last 72h window filtered by `captured_at`** (002 has no `published_at`): `{status, tenant_id, window_hours:72, metrics:{total_views, total_likes, total_comments, total_shares, avg_ratio_relativo, videos_analyzed, classification_distribution:{ROJO:n,AMARILLO:n,VERDE:n}}}`; returns `{"status":"no_data", …}` when the window is empty — never fabricated (`metrics.py:69-126` rewritten).

### D5 — Brain GET contract: fabricated-free object

`GET /tenants/{tid}/brain` returns `{"tenant_id", "status", "persona", "collection_stats": null, "chunks": [], "collection": "marketing_brain"}`. `persona` = parsed `niches.personaje_marca_json` (first row for the tenant; the real home of brand-attrs — DDL 001 `niches`), else `null`; `status` = `"ok"` when persona found, `"no_data"` otherwise. **No Qdrant call, no invented counts** (REQ-API-3 scenario „1240“ gate). Requires a minimal `Niche` ORM class (only columns present in 001: `id, tenant_id, niche, micronicho, ppp, personaje_marca_json`).

### D6 — Shared hook (proposal Q3 → recommended)

| Option | Tradeoff | Decision |
|---|---|---|
| **`useTenantResource(endpoint, tenantId)`** — ~25-line wrapper of `fetchWithTenant` returning `{data, loading, error}`, AbortController guard, ignore-AbortError (the InboundLeadsView pattern `InboundLeadsView.jsx:17-33` extracted) | One abstraction for 5 views + dashboard; spec „simple shared hook acceptable" | **Chosen** |
| Duplicate per-view effect | 6 copies of the same mount-effect; drift risk | Rejected |

Returns the raw parsed payload; array-views require `Array.isArray`, brain uses the object.

## Backend Slice — Endpoints

| Endpoint | Router | Guard | Empty | Notes |
|---|---|---|---|---|
| `GET /api/v1/tenants/{tenant_id}/ideas` | new `backend/routers/ideas.py` | `_TENANT_GUARD` (main.py:70) | `200 []` | `select(Idea)`, project all DDL-001 keys (REQ-API-1); 503 only on DB error; never fabricated |
| `GET /api/v1/tenants/{tenant_id}/scripts` | new `backend/routers/scripts.py` (mirror `leads.py:67-102` pattern) | `_TENANT_GUARD` | `200 []` | `select(Script)`, DDL-001 keys |
| `GET /api/v1/tenants/{tenant_id}/brain` | new `backend/routers/brain.py` | `_TENANT_GUARD` | `200 {status:"no_data",chunks:[]}` | D5; niche persona query |
| `GET /api/v1/tenants/{tenant_id}/metrics` | `backend/routers/metrics.py:29-66` | `_TENANT_GUARD` | `200 []` | D4 flat shape (fixes the ORM/DDL 503) |
| `GET /api/v1/tenants/{tenant_id}/metrics/72h` | `metrics.py:69-126` | `_TENANT_GUARD` | `200 {"status":"no_data"}` | D4 aggregate over aligned columns |

Mount in `main.py`: import the three new routers (after line 30) and `app.include_router(xxx_router, dependencies=_TENANT_GUARD)` after line 77, matching `leads_router`/`metrics_router`.

### Publish/approval provenance — honest 202 no-ops (`graph_execution.py:67-129`)

- `POST /{tid}/ideas/approve` → adds `status_code=202`, keeps the SSE `idea_checkpoint` broadcast + background `_resume_graph`, body `{"status":"accepted","kind":"idea_approval","queued":true}` (echo only real `idea_id`, never fabricate one).
- `POST /{tid}/publish/approve` → deletes the invented `ig_reel_…_99812` (line 102), body `{"status":"accepted","kind":"publish_approval","queued":true}`, SSE without `published_post_id`.
- **No DB writes, no new rows** (REQ-API-06); the frontend maps these via `/scripts` GET since no `/videos` GET exists → publish approval card shows the latest script's `keyword`/CTA as the honest provenance.

## Frontend Slice — Views

| File | Fetches | States |
|---|---|---|
| `features/Ideation/views/IdeaApprovalView.jsx` | `useTenantResource("ideas", tenantId)` | Cargando… / empty „No hay ideas pendientes" / error box; Aprobar/Rechazar POSTs real `{idea_id: idea.id}` →1:1 `202` → „encolado / queued" chip + disabled buttons; buttons hidden when empty |
| `features/Scriptwriting/views/ScriptInspectorView.jsx` | `useTenantResource("scripts", tenantId)` | same tri-state, `Script4BlockReader` renders `data[0]`; empty „Sin guiones todavía" |
| `features/RAGBrain/views/BrainManagementView.jsx` | `useTenantResource("brain", tenantId)` | persona/chunks/collection_stats from object; no data → „Cerebro sin datos aún" (replaces „1,240 Chunks" and hardcoded brand attrs) |
| `features/VideoPreview/views/PublishApprovalView.jsx` | `useTenantResource("scripts", tenantId)` | provenance from script; URI card → honest queued/empty; POST publish/approve, 202 chip |
| `features/Metrics72h/views/MetricsDashboardView.jsx` + `components/MetricClassificationCard.jsx` | `useTenantResource("metrics", tenantId)` | flat fields (`views_72h`/`ratio_relativo`) — crash-proof (no `metrics_72h` deref) |
| `src/app/page.js` (dashboard) | `useTenantResource` for ideas/scripts/metrics | idea/publish cards: real first pending item + approval flow with real id, empty → disabled buttons + empty text; metric tab flat shape + empty guard |

## File Changes

| File | Action | Slice |
|---|---|---|
| `agency/backend/db/models.py` | Modify | 1 — `VideoMetric`→002, `Idea`→001, add minimal `Niche` |
| `agency/backend/routers/ideas.py`, `scripts.py`, `brain.py` | Create | 1 |
| `agency/backend/routers/metrics.py` | Modify | 1 (flat + 72h per D4) |
| `agency/backend/routers/graph_execution.py` | Modify | 1 (202 no-ops) |
| `agency/backend/security/auth.py` | Modify | 1 (D1: `get_current_user` binds requested tenant) |
| `agency/backend/main.py` | Modify | 1 (mount 3 routers, `_TENANT_GUARD`) |
| `agency/tests/unit/test_video_metric_orm_alignment.py` | Create | 1 (column read-back + insert/select) |
| `agency/tests/unit/test_api_ideas_scripts_brain.py` | Create | 1 (dev-200/prod-401, cross-tenant 403, brain shape, 202 no-write) |
| `agency/tests/unit/test_fastapi_endpoints.py` | Modify | 1 (tighten `test_get_metrics_endpoint` → `init_test_db`, 200-only) |
| `agency/tests/e2e/test_full_pipeline.py` | Modify | 1 (202 asserts, `published_post_id` absence) |
| `agency/frontend/src/hooks/useTenantResource.js` | Create | 2 |
| 5 views + `MetricClassificationCard.jsx` + `src/app/page.js` | Modify | 2 |
| `agency/tests/unit/test_frontend_infra.py` | Modify | 2 (grep gates) |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit (ORM) | `VideoMetric` columns == 002 set; none of the 7 phantom columns | `test_video_metric_orm_alignment.py` key-set assert + `select` regression after insert (REQ-VID) |
| Integration (backend) | dev real-UUID GET 200; prod no-JWT 401 (monkeypatch `backend.security.auth.AGENCY_ENV`, *module constant*); cross-tenant 403; approve 202 with no DB delta; metrics flat keys/no 503 | httpx `ASGITransport` in `test_api_ideas_scripts_brain.py` + tightened `test_fastapi_endpoints.py` |
| E2E (backend) | 202 approve, no `ig_…` id | `test_full_pipeline.py` updated |
| Structure (frontend) | mock literal `0` matches; anchored demo literals `0`; hook + endpoint wiring present | extended `test_frontend_infra.py` |

Verify commands: backend `cd agency && AGENCY_ENV=dev .venv/bin/python -m pytest tests/` (venv: `agency/.venv`); frontend `cd agency/frontend && npm run build` exit 0 + the two greps + pytest above. No JS test runner exists (package.json scripts: dev/build/start/lint only) — browser sanity check optional.

## Threat Matrix

| Boundary | Applicability | Design response |
|---|---|---|
| Routing | N/A — new FastAPI routes are declarative HTTP handlers inside the existing guarded router style (main.py:74-77); no shell/subprocess/JUMP | — |
| Shell commands | N/A — verification only (pytest/npm build), no code executes subprocesses | — |
| VCS / PR automation | N/A in this artifact — chained-PR delivery is `sdd-tasks`/`sdd-apply`'s scope, not this design | Slice boundaries below feed tasks |

## Slice / PR boundaries (=400-line budget)

- **Slice 1 (backend, PR #1 → `main`)**: models + 3 routers + metrics + graph_execution + auth + main + backend tests. Verify: pytest green (all, includes new). Rollback: `git revert` of the slice-1 commit — backend returns to 503/404 but frontend stays safe behind error states.
- **Slice 2 (frontend, PR #2)**: hook + 5 views + `MetricClassificationCard` + `page.js` + `test_frontend_infra.py`. Branch chains: `feature/wire-feature-views-to-real-data/slice-2` branched from slice-1 head; after PR #1 merges, retarget PR #2 → `main` (per review guard: child diff must be clean). Verify: `npm run build` + grep gates (0 matches for `mock|1,240|3 Errores|tenant-demo-001|edited_output.mp4|s3://viralsync|idea-101` in the 5 views + `page.js`) + test. Rollback: revert restores mocks without breaking build.

## Migration / Rollout

No DB migration (DDL already 002; `|create_all` idempotent). Middleware/ORM change is backward-compatible: prod path untouched (fail-closed); old nested metrics contract removed from frontend in slice 2, so backends+frontend must ship in order (slice 1 → 2).

## Open Questions

None — the four open points (D1 dev-auth binding, D4 metrics aggregate, D5 brain shape, D6 hook vs duplicate) are settled above with recommendations + alternatives.