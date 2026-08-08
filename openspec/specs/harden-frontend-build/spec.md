# harden-frontend-build Specification

## Purpose

Frontend-only (`agency/frontend/`). Verified: `Header.jsx` derefs `activeTenant` (store init `null`), so `next build` crashes prerendering `/admin/sistema` and `/tenants/nuevo`. Tailwind globs miss `./src/features/**`. Endpoints exist: `GET /api/v1/tenants/{tid}/leads`, `GET /api/v1/tenants/{tid}/metrics` (array matches card 1:1). `fetchWithTenant` in `src/services/apiConfig.js`. Assumptions: `/metrics` array, not `/metrics/72h`; empty/error UI, never mock.

## Requirements

### Requirement: Production build passes with null tenant state

The Header MUST render without dereferencing `activeTenant` when null/empty — spend/budget show `—`; with `availableTenants: []` the selector renders disabled showing "Sin tenant activo". The build MUST succeed from initial store state.

#### Scenario: HDR-S1 — Build prerenders static pages (group: build)

- GIVEN store state `activeTenant: null`
- WHEN `npm run build` runs
- THEN it exits 0 AND `/admin/sistema`, `/tenants/nuevo` prerender without throwing

#### Scenario: HDR-S2 — Header with null activeTenant (group: header)

- GIVEN `activeTenant: null`
- WHEN `Header` renders
- THEN spend/budget show `—` and no `activeTenant` property is read

#### Scenario: HDR-S3 — Selector disabled without tenants (group: header)

- GIVEN `availableTenants: []`
- WHEN `Header` renders
- THEN the selector is disabled with "Sin tenant activo" and no crash

### Requirement: Tailwind content globs cover feature views

The Tailwind config MUST include `./src/features/**` in `content`; production CSS MUST retain feature-view classes.

#### Scenario: HDR-T1 — Features glob present (group: tailwind)

- GIVEN `agency/frontend/tailwind.config.js`
- WHEN the `content` array is inspected
- THEN it includes a glob covering `./src/features/**`

#### Scenario: HDR-T2 — CSS retains feature classes (group: build)

- GIVEN a successful `npm run build`
- WHEN the generated CSS is searched for a feature-view class (e.g. `bg-slate-950`)
- THEN the class is present in the output

### Requirement: Leads view fetches the real API

`InboundLeadsView` MUST fetch `GET /api/v1/tenants/{tenantId}/leads` on mount via `fetchWithTenant`, render rows in `LeadsTable`, with loading/empty/error states. MUST NOT render mock data or crash; `handleTakeover` unchanged.

#### Scenario: HDR-L1 — Rows render from the API (group: leads)

- GIVEN valid token and `tenantId` (route param)
- WHEN the fetch resolves with an array
- THEN the request was issued and rows render in `LeadsTable`

#### Scenario: HDR-L2 — Empty response (group: leads)

- GIVEN the fetch resolves with `[]`
- WHEN the view renders
- THEN an empty state appears and no mock rows show

#### Scenario: HDR-L3 — Fetch failure (group: leads)

- GIVEN missing token, network error, or non-2xx
- WHEN the fetch rejects
- THEN an error state renders, no crash, no mock fallback

### Requirement: Metrics view fetches the per-video array

`MetricsDashboardView` MUST fetch `GET /api/v1/tenants/{tenantId}/metrics`, render one card per item (`video_id`, `metrics_72h.views/ratio`, `classification`, `action_taken`), with loading/empty/error states. MUST NOT use the `/metrics/72h` shape or mock data.

#### Scenario: HDR-M1 — Card grid from the API (group: metrics)

- GIVEN valid token and `tenantId`
- WHEN the fetch resolves with a per-video array
- THEN the request was issued and one card renders per item with existing fields

#### Scenario: HDR-M2 — Empty array (group: metrics)

- GIVEN the fetch resolves with `[]`
- WHEN the view renders
- THEN an empty state shows and no mock cards appear

#### Scenario: HDR-M3 — Fetch failure (group: metrics)

- GIVEN missing token, network error, or non-2xx
- WHEN the fetch rejects
- THEN an error state renders, no crash, no mock fallback

### Requirement: Mock removal limited to two backable views

This delta MUST NOT change Ideas/Scripts/Brain/Pipeline/Admin/`/tenants/nuevo` content; only `Header.jsx`, `tailwind.config.js`, `InboundLeadsView.jsx`, `MetricsDashboardView.jsx` are modified.

#### Scenario: HDR-R1 — No regression outside scope (group: non-goal)

- GIVEN the shipped change
- WHEN the diff is reviewed
- THEN only the four in-scope files changed

### Requirement: Reuse existing fetch plumbing

Views MUST reuse `fetchWithTenant` with `tenantId` from route params, no new global state or auth handling; missing token renders graceful empty/error UI.

#### Scenario: HDR-F1 — tenantId from route params (group: fetch-contract)

- GIVEN a page under `/tenants/[tenantId]/...`
- WHEN the view mounts
- THEN requests carry `resolvedParams.tenantId` and no new storage is added

#### Scenario: HDR-F2 — No token renders gracefully (group: fetch-contract)

- GIVEN no token in `localStorage`
- WHEN both views render
- THEN empty/error UI renders, no crash, no mock fallback