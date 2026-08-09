# Tasks: Wire Feature Views to Real Data

Change `wire-feature-views-to-real-data`. Two ordered chained PR slices: **PR #1 backend** (fix data layer + new GETs + dev-auth + honest approvals) → **PR #2 frontend** (wire 5 views + dashboard cards). Honest loading/error/empty UX only; zero mocks.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | **Slice 1 backend ~550–650** (models.py ~80, metrics.py ~175, auth.py ~15, main.py ~15, 3 new routers ~200, graph_execution.py ~50, tests ~205) · **Slice 2 frontend ~400–450** (hook ~25, 5 views ~350, dashboard+cards ~95, test_frontend_infra.py ~45) · **Total ~950–1100** |
| 400-line budget risk | **High** (total >2× budget; slice 1 alone is borderline) |
| Chained PRs recommended | Yes (mandated: slice 1 backend first, slice 2 frontend second) |
| Suggested split | PR #1 `feature/wire-feature-views-to-real-data/slice-1` → main · PR #2 `…/slice-2` branched from slice-1 head, retargeted → main after PR #1 merges (design §Slice/PR boundaries) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main (design: PR #1 → main; slice-2 branch from slice-1 head, retarget → main; keep then: enforce clean child diff) |

```
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

Slicing protects reviewers: slice 1 carries all DB/API tests (~205 authored test lines), slice 2 is wiring + grep gates. frontend-design skill NOT applicable — no visual design change, data wiring + honest states only (D6).

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | ORM→DDL alignment (VideoMetric/Idea/Niche) + read-back test | PR 1 | `AGENCY_ENV=dev .venv/bin/python -m pytest tests/unit/test_video_metric_orm_alignment.py -p no:cacheprovider -q` | N/A — unit test proves shape | `models.py` + `test_video_metric_orm_alignment.py` |
| 2 | Flat `/metrics` + 72h aggregate + 200-only test | PR 1 | `… -m pytest tests/unit/test_fastapi_endpoints.py` | N/A — unit/integration | `routers/metrics.py`, `test_fastapi_endpoints.py` |
| 3 | Dev-auth tenant bind + 3 GETs + mounts + 202 no-ops | PR 1 | `… -m pytest tests/unit/test_api_ideas_scripts_brain.py tests/e2e/test_full_pipeline.py -p no:cacheprovider -q` | real Postgres curl 200 (`<uuid>/…/ideas` w/ `X-Tenant-ID`) | `security/auth.py`, `routers/{ideas,scripts,brain}.py`, `main.py`, `graph_execution.py` + tests |
| 4 | useTenantResource hook + 4 notes/views wired | PR 2 | `npm run build` exit 0 + grep gates | N/A — no JS runner; browser sanity (empty DB → empty states) | `hooks/useTenantResource.js` + 5 views |
| 5 | Dashboard cards + metrics flat map + grep gates | PR 2 | `… -m pytest tests/unit/test_frontend_infra.py` + `npm run build` | browser: no token → error state | `src/app/page.js`, `MetricClassificationCard.jsx` |

## Phase 1 (Slice 1 — Backend, PR #1 → main)

- [ ] **T1 (GREEN after RED)** Align ORMs — `agency/backend/db/models.py`: `VideoMetric` → exactly 002 columns (`views_72h, likes, comments, shares, ratio_relativo, classification, action_taken, captured_at`), drop all 7 phantom columns (incl. `published_at/null_…/created_at`); re-align `Idea` (models.py:39-48) to DDL 001 keys (`niche_id, gancho, entendible_nino_5_anos, interesa_50_de_100, universalidad, intensidad, claridad, shareability, distribucion, alineacion, rum_score, rum_threshold_id, passes_threshold, approval_status, origen_reintento_de`); add minimal `Niche` (only 001 cols: `id, tenant_id, niche, micronicho, ppp, personaje_marca_json`). Follow `Lead` docstring precedent (models.py:68-73). **REQ-VID-1 (VID-01-01/02)**
- [ ] T2 — **RED first** `agency/tests/unit/test_video_metric_orm_alignment.py`: column-set assert == 002 set AND none of phantom cols present; insert/select regression via `init_test_db` (no `UndefinedColumn`). Then GREEN on T1. **REQ-VID-1**
- [ ] T3 — Rewrite `agency/backend/routers/metrics.py:29-126` (D4): flat list `[{video_id, views_72h, likes, comments, shares, ratio_relativo, classification, action_taken, captured_at}]`; `/metrics/72h` aggregate over last-72h window filtered by `captured_at` → `{status, tenant_id, window_hours:72, metrics:{total_views, total_likes, total_comments, total_shares, avg_ratio_relativo, videos_analyzed, classification_distribution:{ROJO,AMARILLO,VERDE}}}`, `{"status":"no_data"}` when empty; keep 503 only on DB error. Tighten `agency/tests/unit/test_fastapi_endpoints.py::test_get_metrics_endpoint` (line 53): `(200, 503)` → `200` only. **REQ-VID-2 (VID-02-02), REQ-API-4 (API-04-2)**
- [ ] T4 — Dev-auth guard: `agency/backend/security/auth.py` `get_current_user` (lines 91-98) accept `request: Request`; when `AGENCY_ENV in ("dev","development")` and no Bearer, return `{"sub":"usr_dev_001","tenant_id": getattr(request.state,"tenant_id",None), "role":"admin"}` (drop hardcoded `"default_tenant"`); `verify_tenant_access` and prod branch untouched. Tests MUST `monkeypatch.setattr(backend.security.auth, "AGENCY_ENV", "prod")` — module constant (auth.py:22), never only `os.environ`. **REQ-API-05 (API-05-1/2/3)**
- [ ] T5 — NEW routers mirroring `leads.py:67-102` guarded pattern: `agency/backend/routers/ideas.py` (`GET /{tid}/ideas`: `select(Idea)` → 200 `[]`/rows, `503` only on DB error), `routers/scripts.py` (select Script, DDL-001), `routers/brain.py` (D5: `{"tenant_id","status","persona","collection_stats": null,"chunks":[],"collection":"marketing_brain"}`, persona parsed from `niches.personaje_marca_json` first row → status `ok`/`no_data`; NO Qdrant, NO invented counts). Mount in `main.py` after line 70 — imports after line 30, `app.include_router(x, dependencies=_TENANT_GUARD)` after line 77. **REQ-API-1, REQ-API-2, REQ-API-3**
- [ ] T6 — Honest 202 no-ops in `agency/backend/routers/graph_execution.py` (lines 67-129): `POST …/ideas/approve` → `status_code=202`, body `{"status":"accepted","kind":"idea_approval","queued":true}` (echo only real `idea_id`), keep SSE `idea_checkpoint` + background `_resume_graph`; `POST …/publish/approve` → delete invented `ig_reel_…_99812` (line 102), body `{"status":"accepted","kind":"publish_approval","queued":true}`, SSE without `published_post_id`. NO DB writes. **REQ-API-06 (API-06-1/2)**
- [ ] T7 — Integration tests `agency/tests/unit/test_api_ideas_scripts_brain.py` (httpx ASGITransport): dev real-UUID 200 (empty list), prod no-JWT 401 (monkeypatched `auth.AGENCY_ENV`), cross-tenant JWT → 403, brain shape (`chunks` list, no `1240`), approve 202 + `count(*)` unchanged; update `agency/tests/e2e/test_full_pipeline.py` (202 asserts, `published_post_id` absent, no `ig_…` id). **API-GET-3/4, API-02-2, API-03-2, API-06**
- [ ] T8 — Verification slice 1: `cd agency && AGENCY_ENV=dev .venv/bin/python -m pytest tests/ -p no:cacheprovider -q` (all green, incl. tightened metrics and new suites); Postgres dev smoke: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/tenants/<real-uuid>/{ideas,scripts,brain,metrics} -H "X-Tenant-ID: <uuid>"` → 200 (metrics no longer 503). **API-GET-1, API-02-1, API-03-1, API-04-1, VID-02-01**

## Phase 2 (slice 2 — Frontend, PR #2 → main)

- [ ] T9 — Create `agency/frontend/src/hooks/useTenantResource.js`: ~25-line wrapper of `fetchWithTenant` (`InboundLeadsView.jsx` pattern, AbortController + ignore-AbortError) returning `{data, loading, error}`; array-views `Array.isArray`, brain uses object. **REQ-FEAT-4**
- [ ] T10 — `features/Ideation/views/IdeaApprovalView.jsx`: drop `mockIdea`/`idea-101`/`"3 Errores…"`; `useTenantResource("ideas", tenantId)`; loading/empty ("No hay ideas pendientes")/error; Aprobar/Rechazar POST `{idea_id: <fetched id>}` → 202 → "encolado" chip + disabled; buttons hidden when empty. **REQ-FEAT-1 (FEAT-V1/2/3), REQ-FEAT-3 (FEAT-A1), REQ-FEAT-02**
- [ ] T11 — `features/Scriptwriting/views/ScriptInspectorView.jsx`: drop `mockScript`; `useTenantResource("scripts")`, `Script4BlockReader` renders `data[0]`; empty "Sin guiones todavía". **REQ-FEAT-1, REQ-FEAT-02**
- [ ] T12 — `features/RAGBrain/views/BrainManagementView.jsx`: drop "1,240 Chunks"/hardcoded brand attrs; `useTenantResource("brain")`; persona/chunks/collection_stats from object; no data → "Cerebro sin datos aún". **REQ-FEAT-1, REQ-FEAT-02 (FEAT-N2)**
- [ ] T13 — `features/VideoPreview/views/PublishApprovalView.jsx`: drop `s3://viralsync-media-dev/{tenantId}/edited_output.mp4` URI; `useTenantResource("scripts")` provenance (latest script keyword/CTA); POST publish/approve → 202 "encolado"; never renders fake persisted URI. **REQ-FEAT-1, REQ-FEAT-3, REQ-FEAT-02**
- [ ] T14 — `features/Metrics72h/views/MetricsDashboardView.jsx` + `components/MetricClassificationCard.jsx` (35,39): `useTenantResource("metrics")`; flat `views_72h`/`ratio_relativo` (no `metrics_72h` deref — crash-proof). **REQ-FEAT-4 (FEAT-D2)**
- [ ] T15 — `src/app/page.js` (dashboard, 103/275/296/397-407): remove `idea-101`, "3 Errores…", `tenant-demo-001/edited_output.mp4`; idea/publish/metrics cards via `useTenantResource`; first real pending item + real approval id; empty → disabled buttons + empty text; metric tab reads flat shape. **REQ-FEAT-4 (FEAT-D1/D2), REQ-FEAT-02 (FEAT-N2)**
- [ ] T16 — Extend `agency/tests/unit/test_frontend_infra.py` grep gates: `mock` (incl. `mockIdea`/`mockScript`), `1,240`, `3 Errores`, `tenant-demo-001`, `idea-101`, `edited_output.mp4` → 0 matches in the 5 views + `page.js`; hook file exists; endpoint strings wired. **REQ-FEAT-02 (FEAT-N1/N2), REQ-FEAT-5 (FEAT-B1)**
- [ ] T17 — Verify slice 2: `cd agency/frontend && npm run build` exit 0; re-run T16 pytest; browser sanity (empty DB → empty states; no token → error state without uncaught exception). **REQ-FEAT-5 (FEAT-B1)**

## Committing Guidance (work units, conventional, NO AI attribution)

**Slice 1 (PR #1 → main)** — commit tests WITH their behavior:
1. `fix(backend): align VideoMetric and Idea ORM to DDL 002/001` (models.py + read-back test)
2. `fix(backend): restore /metrics 200 with flat DDL-002 shape` (metrics.py + tightened fastapi test)
3. `feat(backend): dev auth binds requested tenant, prod stays fail-closed` (security/auth.py)
4. `feat(backend): add tenant-guarded GET endpoints for ideas/scripts/brain` (routers + main.py + api tests)
5. `feat(backend): honest 202 no-op approve and publish checkpoints` (graph_execution.py + e2e test)

**Slice 2 (PR #2 → main, retarget after PR #1 merges):**
1. `feat(frontend): add shared useTenantResource hook with abort guard`
2. `feat(frontend): wire idea/script/brain/publish views to real data`
3. `feat(frontend): wire metrics dashboard to flat metric shape` (card + view)
4. `feat(frontend): wire dashboard idea/publish/metrics cards to real data` (page.js)
5. `test(frontend): grep gates for mock and demo anchors` (test_frontend_infra.py)

No AI attribution, no `--no-verify` skips. Yours: verify each commit independently (the focused `pytest`/build commands above).

## Notes for executor

- Auth: MONKEYPATCH THE MODULE CONSTANT `backend.security.auth.AGENCY_ENV` (auth.py:22) — `os.environ` is NOT read again at request time.
- DDL names EXACT from `002_add_video_metrics…` / `001_init_schema.sql` — typo'd column name ⇒ 503/UndefinedColumn.
- Brain must be fabricated-free: status derives from real persona row; no `1240`, no vector counts.
- Approve/publish POSTs are the ONLY `202`s — keep SSE + graph resume, NO DB row creation.
- `useTenantResource` returns raw parsed payload; consumers guard array vs object. Run ONLY before/after: `app/page.js`, 5 views, `Card` — `Sidebar.jsx` default `tenant-demo-001` is not gated (`page.js` + 5 views only).
- pytest CWD `agency`: `AGENCY_ENV=dev .venv/bin/python -m pytest tests/ -p no:cacheprovider -q` (venv `agency/.venv`); frontend CWD `agency/frontend`: `npm run build`.