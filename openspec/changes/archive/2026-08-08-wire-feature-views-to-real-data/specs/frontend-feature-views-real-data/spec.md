# Delta for frontend-feature-views-real-data

**id**: `frontend-feature-views-real-data`
**status**: approved
**title**: Wire the five feature views and dashboard cards to the real APIs with loading/error/empty states

## Summary

Removes the last mock-backed and hardcoded-data views in the frontend (`IdeaApprovalView`, `ScriptInspectorView`, `BrainManagementView`, `PublishApprovalView`, and the dashboard idea/script/video cards) and points them at the GET endpoints defined by `api-ideas-scripts-brain-get`. MetricsDashboardView re-maps to the real flat metrics shape. Every view renders loading → data | empty | error; nothing crashes and nothing fabricates. Zero `mock` literal and zero demo values remain where this spec gates.

## Preamble (verified in code)

- Features/views: `Ideation/views/IdeaApprovalView.jsx` (has `mockIdea`, raw `fetch` POST w/ fake id), `Scriptwriting/views/ScriptInspectorView.jsx` (mockScript + `Script4BlockReader`), `RAGBrain/views/BrainManagementView.jsx` (hardcoded "1,240 Chunks", 384, brand attributes), `VideoPreview/views/PublishApprovalView.jsx` (hardcoded S3 URI + raw POST publish/approve), `Metrics72h/views/MetricsDashboardView.jsx` (already wired to `/metrics`, but renders the legacy nested `metrics_72h.views/ratio` contract that the DDL-aligned API removes), `app/page.js` (dashboard hardcodes "3 Errores Críticos al Escalar B2B en 2026", `idea_id: "idea-101"`, `tenant-demo-001/edited_output.mp4`; loads leads/metrics via fetchWithTenant; metric tab reads `item.metrics_72h`).
- Fetch contract: `services/apiConfig.js` `fetchWithTenant(endpoint, options, tenantId)` sets `X-Tenant-ID` + optional Bearer, throws on non-2xx.
- No JS test runner: proof via `npm run build`, code greps, and `agency/tests/unit/test_frontend_infra.py`-style pytest asserts.

## ADDED Requirements

### Requirement: REQ-FEAT-1 — Five views fetch the real endpoints with loading/empty/error

The five views MUST fetch on mount via `fetchWithTenant` (or a shared hook atop it), with `tenantId` from route params: `IdeaApprovalView` → `GET /tenants/{id}/ideas`; `ScriptInspectorView` → `/scripts`; `BrainManagementView` → `/brain`; `PublishApprovalView` → `/scripts` (videos have no GET in this change; the script drives the approval card); `MetricsDashboardView` → `/metrics`. Each MUST render a loading state while pending, the items from the response array only, an honest empty state on `[]` (never demo content), and an error state on rejection — 401/403/404/5xx/network — without crashing or falling back to mock.

#### Scenario: FEAT-V1 — empty state, honest

- GIVEN the backend returns `[]` for the view's endpoint
- WHEN the view renders after resolution
- THEN an empty message appears and NO hardcoded/demo item is shown

#### Scenario: FEAT-V2 — error state, no crash

- GIVEN a rejected fetch (missing token, 401/403/404, network error, 503)
- WHEN the view renders
- THEN an error state renders inside the chrome (page/header/sidebar intact), no mock fallback, and no uncaught exception

#### Scenario: FEAT-V3 — rows render from the API only

- GIVEN a response array with one item
- WHEN the view renders
- THEN the item's fields (e.g. `texto`/`rum_score`, `gancho_0_5s`…) render and the exact request `fetchWithTenant(`/tenants/${tenantId}/…`)` was issued

### Requirement: REQ-FEAT-02 — Zero mock literals and zero fabricated demo values

The five views plus `src/app/page.js` MUST contain no `mock` literal and none of the previous fabricated anchors (`idea-101`, `3 Errores Críticos al Escalar B2B en 2026`, `tenant-demo-001`, `1,240 Chunks`, `edited_output.mp4`, `s3://viralsync-media-dev/…`). All previously hardcoded content MUST instead come from live responses or be replaced by an honest empty/queued state.

#### Scenario: FEAT-N1 — mock-literal grep is clean

- GIVEN the shipped change
- WHEN `grep -rniE "mock" src/features/{Ideation,Scriptwriting,RAGBrain,VideoPreview,Metrics72h}/views src/app/page.js` runs
- THEN zero matches are returned (fails while a `mockIdea`/`mockScript` survives)

#### Scenario: FEAT-N2 — fabricated anchors are gone

- GIVEN the shipped change
- WHEN the five views + `src/app/page.js` are scanned for `idea-101`, `tenant-demo-001`, `edited_output.mp4`, `1,240`, and `3 Errores`
- THEN zero matches are returned (an anchored pytest in `test_frontend_infra.py` fails whenever a demo value is re-introduced)

### Requirement: REQ-FEAT-3 — Approval buttons are honest interactions

The Aprobar/Rechazar buttons in `IdeaApprovalView` MUST POST `{idea_id: <fetched idea id>}` (never `idea-101`), and `PublishApprovalView` MUST POST `publish/approve`; on `202` both MUST show a "queued / encolado para procesamiento" state (buttons disabled while queued), on error an error state, and they MUST NOT render fake persisted objects (no fabricated URIs/ids). With zero eligible items the buttons MUST be disabled and only the honest empty state shown.

#### Scenario: FEAT-A1 — 202 shows queued state

- GIVEN a fetched pending idea/script and a `202` response
- WHEN the user clicks Aprobar
- THEN the view shows "encolado/queued for processing" and no fake confirmation object appears

### Requirement: REQ-FEAT-4 — Dashboard cards fetch the same endpoints (shared shape)

The dashboard idea/script/publish cards and the metrics tab MUST consume the same GET endpoints as the feature views (`/ideas`, `/scripts`, `/metrics`), fetched once (a simple shared `useTenantResource`-style hook is acceptable), with loading/error/empty behavior; metrics cards MUST render the flat `views_72h`/`ratio_relativo` shape. No hardcoded card content remains.

#### Scenario: FEAT-D1 — Empty dashboard shows honest cards

- GIVEN the fetched arrays are empty
- WHEN the dashboard renders
- THEN idea/script/publish/metrics cards show explicit empty/queued states — no `3 Errores`… demo card and no `item.metrics_72h` deref

#### Scenario: FEAT-D2 — Metrics tab renders the flat shape

- GIVEN `/metrics` returns `[{video_id, views_72h, ratio_relativo, classification, action_taken}]`
- WHEN the metrics tab renders
- THEN cards use `views_72h` and `ratio_relativo` (no runtime TypeError from a missing `metrics_72h`)

### Requirement: REQ-FEAT-5 — build and regression gates

`npm run build` MUST exit 0 with the views wired; the client-only views MUST javascript-safe-render with no tenant/token (loading→error on no token), and the empty/error branches must not crash the page.

#### Scenario: FEAT-B1 — build passes and error branch renders

- GIVEN `npm run build` in `agency/frontend`
- THEN it exits 0
- AND rendered client-side with no token, the views show the error/empty branch without an uncaught exception

## Acceptance Criteria

- [ ] `grep -rni "mock"` over the five views + `src/app/page.js` → 0 matches
- [ ] Anchored demo literals (`idea-101`, `3 Errores`, `tenant-demo-001`, `1,240`, `edited_output.mp4`) → 0 matches in the same files
- [ ] The five feature views + dashboard render loading → data | empty | error; no crash on 401/403/404/503
- [ ] `npm run build` exit 0; `pytest` extends `test_frontend_infra.py` for the greps

## Notes on proof

- No JS runner: proof = build + pytest-infrastructure greps + browser sanity check (empty DB → empty states; no token → error states).
- Optional shared hook: `src/hooks/useTenantResource.js` (endpoint + tenantId → `{data, loading, error}`), reused by the views and dashboard when the design decides it is simple enough.