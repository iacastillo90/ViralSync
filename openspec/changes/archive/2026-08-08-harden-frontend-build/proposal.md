# Proposal: Harden Frontend Build (Scope A — Frontend Only)

## Intent

Three frontend defects block production stability:

1. **Build blocker**: `Header.jsx` dereferences `activeTenant.current_llm_spend_usd` but the store initializes `activeTenant: null` and nothing populates it. `next build` crashes prerendering the 2 static admin pages that render `Header`; the 8 dynamic `[tenantId]` routes crash at runtime on mount.
2. **Tailwind CRITICAL**: content globs miss `./src/features/**` → all feature-view utility classes are purged from production CSS.
3. **Mock data in 2 backable views**: Leads Inbound and Metrics 72h render hardcoded mocks while matching API endpoints already exist.

No backend/session/auth work. Non-backable views keep their mocks.

## Scope

### In Scope (all under `agency/frontend/`)
- Null-guard `Header.jsx` with placeholders ("—", "No asignado") when `activeTenant` is null/empty; disable tenant selector then.
- Add `./src/features/**` glob to `tailwind.config.js`.
- `InboundLeadsView.jsx` — fetch `GET /api/v1/tenants/{tenantId}/leads`; add loading/empty/error states; keep `handleTakeover` as-is.
- `MetricsDashboardView.jsx` — fetch per-video `GET /api/v1/tenants/{tenantId}/metrics` (shape matches card contract 1:1, no adapter); loading/empty/error states. `/metrics/72h` only if summary view chosen (then adapter).
- Keep existing `fetchWithTenant` (apiConfig.js) graceful token/tenantId behavior.

### Out of Scope
- Backend, migrations, docker/compose edits.
- Session/auth bootstrap (localStorage session, `GET /tenants`) — future change.
- Rewiring Ideas / Scripts / Brain / Admin / Pipeline mocks.

## Capabilities

Existing specs (`openspec/specs/`): only `docker-lockfile-db-bootstrap` (infra) — no frontend capability specs exist.

### New Capabilities
- `frontend-header-null-safety`: Header renders placeholders and disabled tenant selector when no active tenant; no crash at prerender or runtime.
- `frontend-build-hardening`: Tailwind content globs cover all source dirs; production CSS retains feature classes.
- `frontend-leads-inbound-fetch`: InboundLeadsView loads real leads via API with loading/empty/error states.
- `frontend-metrics72h-fetch`: MetricsDashboardView loads real metrics via API with loading/empty/error states (incl. response mapping if aggregated endpoint chosen).

### Modified Capabilities
- None.

## Approach

1. `Header.jsx`: conditionally render spend/budget as `—` and selector placeholder ("Sin tenant activo") when `activeTenant`/`availableTenants` are empty.
2. `tailwind.config.js`: append one content glob line for `./src/features/**`.
3. Both views: `useEffect` + `fetchWithTenant`, local `loading`/`error` state; render table/card grid on success, empty state on `[]|no_data`, error state on throw. No mock fallback (assumption below).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agency/frontend/src/components/layout/Header.jsx` | Modified | Null-safe rendering, placeholder UI |
| `agency/frontend/tailwind.config.js` | Modified | +`./src/features/**` glob |
| `agency/frontend/src/features/LeadsInbound/views/InboundLeadsView.jsx` | Modified | mock → real fetch + states |
| `agency/frontend/src/features/Metrics72h/views/MetricsDashboardView.jsx` | Modified | mock → real fetch + states |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Other prerendered pages still deref null | Low (only `Header.jsx` derefs `activeTenant`; verified) | `npm run build` in verify; guard sits in shared Header |
| Metrics endpoint contract drift | Med | Prefer `/metrics` array (exact match); adapter isolated in view if `/metrics/72h` |
| No token ⇒ all fetches fail | High (no session exists yet) | Graceful error/empty state; never crash or mock-fallback |

## Rollback Plan

Single-revert: `git revert <commit>` — each file change is independent and small (guard, glob line, two view wirings). Header guard can be dropped first if UI complains; views fall back to `useState([])`.

## Dependencies

- Backend endpoints `GET /tenants/{tid}/leads` and `GET /tenants/{tid}/metrics` (already shipped).
- No new packages.

## Success Criteria

- [ ] `npm run build` succeeds; static pages `/admin/sistema` and `/tenants/nuevo` prerender.
- [ ] Production CSS contains feature-view classes (grep `bg-slate-950` in build output).
- [ ] Leads + Metrics views render real API data; empty/error states shown without token.
- [ ] Budget ≤ 400 changed lines (~150–250 expected).

## Proposal Question Round

1. **Metrics source**: keep per-video card grid via `GET /tenants/{id}/metrics` (recommended, exact shape match) or switch UI to consolidated summary via `/metrics/72h` (requires adapter)? Assumption: keep cards.
2. **Empty-data UX**: when no data or missing token, show explicit empty state (recommended) — never fall back to mocks? Assumption: empty state.
3. **Loading UX**: minimal inline skeleton vs spinner? Assumption: lightweight skeleton.