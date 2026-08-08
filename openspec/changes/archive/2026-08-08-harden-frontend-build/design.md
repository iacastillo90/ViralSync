# Design: Harden Frontend Build

## Technical Approach

Four independent, frontend-only fixes under `agency/frontend/`: (1) null-guard `Header.jsx` against store init state (`activeTenant: null`, `availableTenants: []`), (2) add one Tailwind content glob, (3) `InboundLeadsView.jsx` and (4) `MetricsDashboardView.jsx` replace mock state with a mount-effect fetch via `fetchWithTenant` plus loading/empty/error states. Reuses existing plumbing; no new packages, no global state, no backend edits.

## Architecture Decisions

### D1. Header guard shape (scenarios HDR-S1/S2/S3)

| Option | Tradeoff | Decision |
|---|---|---|
| Conditional render inside existing spans | Minimal diff, zero behavioral change | **Chosen** |
| Store-level default object | Hides missing data; touches store | Rejected |

- Spend/budget (line 29): `{activeTenant ? `…${activeTenant.current_llm_spend_usd.toFixed(2)} / ${activeTenant.monthly_llm_budget_usd.toFixed(2)}` : "—"}` — `"—"` shows both values; keeps `font-mono` class.
- Selector `value` (line 37): `value={activeTenant?.id ?? ""}`.
- When `availableTenants.length === 0`: render `<select disabled>` with one `<option value="">Sin tenant activo</option>`; keep the existing `onChange` handler byte-for-byte (fires only for non-empty lists).

### D2. Tailwind glob edit (HDR-T1/T2)

Append after line 6, matching the existing `./src/<dir>/**/*.{js,ts,jsx,tsx,mdx}` style:

```js
"./src/features/**/*.{js,ts,jsx,tsx,mdx}",
```

### D3. Fetch strategy (HDR-L1/L2/L3, M1/M2/M3)

| Option | Tradeoff | Decision |
|---|---|---|
| Mount `useEffect` + local `loading/error` + `AbortController` | Minimal diff, view-local | **Chosen** |
| Global state (useAgentStore pattern) | Spec forbids new state/storage | Rejected |
| No signal | setState-after-unmount leak | Rejected |

`fetchWithTenant` spreads `options`, so `{ signal }` reaches the underlying `fetch` config. Abort/unmount guard: catch ignores `AbortError`; effect returns `() => controller.abort()`.

### D4. tenantId wiring (HDR-F1)

Already wired: route pages `use(params)` and pass `tenantId={resolvedParams.tenantId}` as a prop; both views already accept the `tenantId` prop. No `useParams` in the view, no new storage. Effect guards `if (!tenantId) → setError(...)`, skip fetch.

### D5. Fetch failure contract (HDR-F2, L3, M3)

- No token / network error / non-2xx → `fetchWithTenant` throws → `error` state renders; **never mock fallback**, never rethrow.
- Non-array result → coerce to `[]` (endpoints return arrays).
- `[]` → empty-state block ("No hay leads aún" / "Sin métricas todavía").

### D6. Non-goal guard (HDR-R1)

**Never touch**: `src/app/page.js`, `src/app/tenants/[tenantId]/{pipeline,guiones,cerebro,aprobaciones/ideas,aprobaciones/publicacion}/page.js`, `src/app/admin/sistema/page.js`, `src/app/tenants/nuevo/page.js`, `src/components/layout/Sidebar.jsx`, all non-view files under the two feature dirs, and everything outside `agency/frontend/`.

### D7. Rollback boundary

Single commit (4 files, ≤250 lines, under the 400-line review budget) → `git revert <sha>`. Pure frontend, no flags/migrations.

## Data Flow

```
Route use(params) → tenantId prop → View → fetchWithTenant(`/tenants/${tid}/{leads|metrics}`, {signal}, tenantId)
     │                                     │
     │                                     ▼
     │                       loading → "Cargando…"; ok → LeadsTable / card grid (1:1)
     └─ guard(!tenantId) ─── [] → empty block; error → error block (never mock)
```

## File Changes

Modify exactly: `agency/frontend/src/components/layout/Header.jsx` (D1), `agency/frontend/tailwind.config.js` (D2), `agency/frontend/src/features/LeadsInbound/views/InboundLeadsView.jsx` (D3–D5, `handleTakeover` untouched), `agency/frontend/src/features/Metrics72h/views/MetricsDashboardView.jsx` (D3–D5, **no adapter**). Backend shapes confirmed read-only (`routers/metrics.py:44-60` matches `MetricClassificationCard` 1:1: `video_id, published_at, metrics_72h{views,followers_at_posting,ratio,leads_generated}, classification, action_taken`; `routers/leads.py:83-93` matches `LeadsTable` columns).

Shared effect pattern (per view, endpoint subs in):

```tsx
useEffect(() => {
  const c = new AbortController();
  setLoading(true); setError(null);
  if (!tenantId) { setError(new Error("Sin tenant activo")); setLoading(false); return; }
  fetchWithTenant(`/tenants/${tenantId}/${endpoint}`, { signal: c.signal }, tenantId)
    .then((d) => setItems(Array.isArray(d) ? d : []))
    .catch((e) => { if (e.name !== "AbortError") setError(e); })
    .finally(() => setLoading(false));
  return () => c.abort();
}, [tenantId, endpoint]);
```

## Verification Approach

- **Build** (HDR-S1): `npm run build` in `agency/frontend/` must exit 0; `admin/sistema` and `tenants/nuevo` prerender.
- **CSS** (HDR-T2): `grep -o 'bg-slate-950' .next/static/css/*.css` after clean build; repeat for a feature-only class (e.g. `md:grid-cols-2`).
- **Static assertions**: `grep -n "activeTenant ?"` in Header; `grep -n "src/features/**"` in tailwind config; `grep -n "fetchWithTenant"` in both views; `grep -n "mockMetrics|lead-001|video-55"` in both views → must be empty.
- **Manual view check**: `/tenants/<id>/leads` and `/metricas` with no token (error state), with token (rows/cards).
- **No JS test runner exists** (definitive): `agency/frontend/package.json` scripts are `dev`, `build`, `start`, `lint` only — no jest/vitest/node:test. Verification rests on build + static grep + manual check; unit tests N/A unless a runner is added (out of scope).

## Scenario Mapping (all 14)

| Spec (spec.md) | Requirement | Design |
|---|---|---|
| HDR-S1 | Build prerenders | D1 + build |
| HDR-S2/S3 | Header null / selector | D1 |
| HDR-T1/T2 | Tailwind glob + CSS | D2 |
| HDR-L1–L3 | leads fetch/empty/error | D4/D5 |
| HDR-M1–M3 | metrics fetch/empty/error | D4/D5 |
| HDR-R1 | only 4 files changed | D6 + `git diff --name-only HEAD` |
| HDR-F1 | tenantId from params | D4 |
| HDR-F2 | no-token graceful | D5 |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary; client HTTP uses existing routes and helper only.

## Migration / Rollout

No migration, no feature flags. Single commit; `git revert` is the rollback. ≤ 250 changed lines.

## Open Questions

None — assumptions locked by proposal Q&A (per-video `/metrics`; empty/error states, never mocks).