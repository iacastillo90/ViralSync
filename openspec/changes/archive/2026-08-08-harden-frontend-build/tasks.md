# Tasks: Harden Frontend Build (Scope A)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~150–250 (Header +6/−9; Tailwind +1; Leads +30/−13; Metrics +35/−26) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR, single commit (D7) |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Work Unit

| Goal | PR | Focused test command | Runtime harness | Rollback boundary |
|------|----|----------------------|-----------------|-------------------|
| 4-file hardening (Header guard, Tailwind glob, 2 API-fetched views) | PR 1, 1 commit | `npm run build` in `agency/frontend/` → exit 0 | `npm run dev`; `/tenants/<id>/leads`, `/metricas`: no token → error state; token → data | `git revert <sha>`; any view reverts alone via `useState([])` |

## Tasks

- [x] **T1 — Null-guard Header** `agency/frontend/src/components/layout/Header.jsx` (D1)
  - Line 29: `{activeTenant ? `…${activeTenant.current_llm_spend_usd.toFixed(2)} / ${activeTenant.monthly_llm_budget_usd.toFixed(2)}` : "—"}` (keep `font-mono`); line 37: `value={activeTenant?.id ?? ""}`; `availableTenants.length === 0` → `<select disabled>` + `<option>Sin tenant activo</option>`; `onChange` byte-for-byte.
  - Deps: none · Accept: HDR-S2, HDR-S3 · Verify: `grep -n "activeTenant ? "` and `grep -n "Sin tenant activo"` in Header.jsx

- [x] **T2 — Tailwind features glob** `agency/frontend/tailwind.config.js` (D2)
  - Append `"./src/features/**/*.{js,ts,jsx,tsx,mdx}",` to `content` after `./src/app/**` line.
  - Deps: none · Accept: HDR-T1 · Verify: `grep -n "src/features" tailwind.config.js`

- [x] **T3 — Leads: mock → API** `src/features/LeadsInbound/views/InboundLeadsView.jsx` (D3–D5)
  - Replace mock state (lines 13–24) with mount effect: `AbortController`; `!tenantId` → error, skip; `fetchWithTenant(`/tenants/${tenantId}/leads`, {signal: c.signal}, tenantId)`; resolve `Array.isArray(d) ? d : []`; catch ignores `AbortError`; cleanup `abort()`. Loading → "Cargando…"; error block; `[]` → "No hay leads aún"; else `<LeadsTable/>`. `handleTakeover` untouched.
  - Deps: T1 · Accept: HDR-L1/L2/L3, HDR-F2 · Verify: `grep -n "fetchWithTenant"`; `grep -n "lead-001"` → no match

- [x] **T4 — Metrics: mock → API** `src/features/Metrics72h/views/MetricsDashboardView.jsx` (D3–D5)
  - Drop `mockMetrics` (lines 9–34); same pattern, endpoint `/tenants/${tenantId}/metrics`, no adapter (array matches card 1:1); loading/error/"Sin métricas todavía"/cards.
  - Deps: T1 · Accept: HDR-M1, M2, M3, HDR-F2 · Verify: `grep -n "fetchWithTenant"`; `grep -nE "mockMetrics|video-55"` → no match

- [x] **T5 — Regression guard (D6)**
  - Confirm exactly the 4 in-scope files changed; Ideas/Scripts/Brain/Admin/Pipeline/`tenants/nuevo`+`Sidebar.jsx` byte-identical.
  - Deps: T1–T4 · Accept: HDR-R1 · Verify: `git diff --name-only HEAD` = 4 paths

- [x] **T6 — Final verification**
  - From `agency/frontend/`: `npm run build` exit 0, `/admin/sistema` + `/tenants/nuevo` prerender; grep `.next/static/css/*.css` for `bg-slate-950` + `md:grid-cols-2`; rerun T1–T5 greps; manual go/no token check; clean tracked tree + 4-file diff.
  - Deps: T1–T5 · Accept: HDR-S1, HDR-T2, success criteria · Verify: `npm run build && grep -o "bg-slate-950" .next/static/css/*.css`

## Commit Plan

- Single commit (per D7 rollback): `fix(frontend): harden build against null tenant, tailwind glob, real API fetches`. Tests/docs N/A — no JS test runner (build + grep + manual checklist per design).