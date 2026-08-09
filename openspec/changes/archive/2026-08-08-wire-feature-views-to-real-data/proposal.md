# Proposal: Wire Feature Views to Real Data

**id**: wire-feature-views-to-real-data

## Summary

Ideas, Guiones, Cerebro, Publish, and dashboard cards render hardcoded mocks while their APIs exist or must exist: `GET /tenants/{id}/ideas|scripts|brain` → 404; `GET /tenants/{id}/metrics` → 503 (ORM/DDL drift); dev auth guard → 403 for real tenant UUIDs. Replace mocks with honest loading/error/empty states via `fetchWithTenant`. No mocks, demo, or hacks — an empty state is acceptable until the pipeline writes data.

## Intent

Every remaining mock-backed view becomes truthful against real Postgres (7 tenants, 11 tables, 0 rows in ideas/scripts/leads/video_metrics). Stop presenting fabricated data as product.

## Scope

### In Scope

**Slice 1 — backend:**
- Align `VideoMetric` ORM to migration 002 DDL (`views_72h/likes/comments/shares/ratio_relativo/classification/action_taken/captured_at`) — fixes 503.
- Add `GET /tenants/{id}/ideas|scripts|brain` with honest shapes (200 `[]` when no rows).
- Approvals: persist POST approve to Postgres OR return an explicit honest no-op — never claim persisted data that isn't.
- Dev auth guard: allow tenant-scoped GETs in dev without a real JWT; fail-closed in prod (policy = open question, option A recommended).

**Slice 2 — frontend:**
- Wire `IdeaApprovalView`, `ScriptInspectorView`, `BrainManagementView`, `PublishApprovalView`, and dashboard idea/script/video cards to `fetchWithTenant` with loading/error/empty states; zero mock fallback.
- `MetricsDashboardView` mapping rides on slice 1.

### Out of Scope
- Full JWT/auth implementation (only the dev guard tweak blocking GETs).
- Visual redesign.
- LLM pipeline persistence beyond honest empty states / minimal approve persistence.

## Requirements

- No `mock` literal remains in the five views or dashboard cards.
- New GETs return 200 with real shape or honest empty result.
- Views never crash on 403/503/404 — error state shown.
- Dev fallback stays fail-closed in staging/prod.

## Capabilities

Existing specs: `docker-lockfile-db-bootstrap`, `harden-frontend-build` (no API/fetch coverage).

### New Capabilities
- `api-ideas-scripts-brain-get`: tenant-scoped GET endpoints with honest empty results.
- `frontend-feature-views-real-data`: five views + dashboard cards fetch real data with loading/error/empty states.
- `backend-video-metric-ddl-alignment`: ORM matches 002 DDL; metrics endpoint returns 200.

### Modified Capabilities
- None.

## Approach

1. Fix ORM columns per migration 002.
2. Add 3 GET routers behind existing `_TENANT_GUARD`; reuse async session pattern.
3. Dev auth: allow header-derived tenant in dev only when guard would 403; prod unchanged.
4. Frontend: shared `useApiResource`-style hook; remove mock arrays.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agency/backend/db/models.py` | Modified | VideoMetric columns match 002 DDL |
| `agency/backend/routers/{ideas,scripts,brain}.py` | New | GET endpoints |
| `agency/backend/routers/metrics.py` | Modified | 503 → 200 via aligned ORM |
| `agency/backend/security/auth.py` | Modified | dev tenant guard policy |
| `agency/frontend/src/features/{Ideation,Ideation,Scriptwriting,RAGBrain,VideoPreview}/views/*.jsx` | Modified | mock → fetch in the 5 views |
| `agency/frontend/src/app/page.js` (dashboard cards) | Modified | real data |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dev auth guard 403s every real UUID | High | Guard tweak in slice 1; scanner test |
| ORM/DDL drift recurs | Med | Column-level read-back assert in pytest |
| Zero-data reality (0 rows) | High | Honest empty states are the target UX |
| No JS test runner | Med | `npm run build` + browser verify |
| >400-line chained split | Med | Slice 1 backend / slice 2 frontend; clean branch chain |

## Open Questions

1. **Dev auth policy**: (A, recommended) dev-only allow header tenant when JWT absent; (B) dev-only full bypass — risks prod-style behavior; (C) keep 403, ship a dev JWT-maker script.
2. **Approve POST**: persist approvals to Postgres vs explicit honest no-op response.
3. **Dashboard cards**: share one hook with views (recommended) or stay bespoke?

## Timeline Estimate

- Slice 1 (backend): ~0.5–1 day incl. design + verify.
- Slice 2 (frontend): ~1–1.5 days incl. browser verification.
- Total: 2–3 dev days, two chained PRs.

## Success Criteria

- [ ] `GET /tenants/{id}/scripts` returns 200 with Script shape or 200 `[]` (same for ideas/brain).
- [ ] `GET /tenants/{id}/metrics` returns 200 `[]` (no 503).
- [ ] No `mock` literal in the five views + dashboard cards (grep clean).
- [ ] Dev GETs over real tenant UUIDs return data/empty, not 403.
- [ ] `pytest` green; `npm run build` exit 0.
- [ ] Views show loading/error/empty states without token.

## Rollback Plan

Per-slice `git revert` — backend revert restores 503/404 but views stay safe behind error states; frontend revert restores mocks without breaking build.

## Dependencies

- Postgres with migration 002 applied (present: 11 tables).
- Existing `fetchWithTenant` service and `_TENANT_GUARD`.

## Proposal Question Round

Open Questions 1–3 above need stakeholder decision before spec (sdd-spec).
