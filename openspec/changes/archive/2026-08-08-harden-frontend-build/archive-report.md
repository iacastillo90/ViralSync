# Archive Report: harden-frontend-build

- **Change**: harden-frontend-build (Scope A — frontend only)
- **Archived at**: 2026-08-08
- **Status**: success
- **Mode**: openspec
- **Implementation commit**: `2e629ee` `fix(frontend): harden build against null tenant, tailwind glob, real API fetches` (parent `ba45862`)
- **Verification**: `verify-report.md` persisted in change folder — verdict **PASS WITH NO BLOCKERS**, critical_findings 0, requirements 6/6, scenarios 14/14, build exit 0 (×2), evidence_revision `sha256:9befe16be74825aa6ccbed102c31c5013afff1b6a073d44bfe45fcc2844599d9`

## Task Completion Gate

- [x] All implementation tasks checked in `tasks.md` (6/6: T1–T6) — no stale unchecked tasks.
- [x] No CRITICAL issues in verification report (verdict PASS, 0 blockers, 0 critical findings).
- [x] All required artifacts present in the change folder (proposal, specs, design, tasks, verify-report) — no intentional partial archive needed.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| harden-frontend-build | Created | Main spec did not exist (`openspec/specs/` only held `docker-lockfile-db-bootstrap`). Delta spec copied to `openspec/specs/harden-frontend-build/spec.md` with canonical main-spec headers (`# harden-frontend-build Specification`, `## Purpose` from `Preamble`, `## ADDED Requirements` → `## Requirements`), per the precedent set by the docker-lockfile-db-bootstrap archive. All 6 requirements and 14 scenarios preserved verbatim, including original scenario IDs (HDR-S1…HDR-F2) and scenario group tags (build, header, tailwind, leads, metrics, fetch-contract, non-goal). |

### Requirements carried over (6)

1. Production build passes with null tenant state (HDR-S1/S2/S3)
2. Tailwind content globs cover feature views (HDR-T1/T2)
3. Leads view fetches the real API (HDR-L1/L2/L3)
4. Metrics view fetches the per-video array (HDR-M1/M2/M3)
5. Mock removal limited to two backable views (HDR-R1)
6. Reuse existing fetch plumbing (HDR-F1/F2)

## Implementation Evidence

- 4 in-scope files on commit `2e629ee`: `agency/frontend/src/components/layout/Header.jsx`, `agency/frontend/tailwind.config.js`, `agency/frontend/src/features/LeadsInbound/views/InboundLeadsView.jsx`, `agency/frontend/src/features/Metrics72h/views/MetricsDashboardView.jsx` (HDR-R1: exactly 4 paths, non-touch files byte-identical).
- Build green twice; static pages `/admin/sistema` and `/tenants/nuevo` prerender; feature CSS classes present in production CSS (HDR-S1/T2).
- No JS test runner exists (package.json scripts: dev, build, start, lint) — verification by build + static grep + live browser, per design.md.

## Archive Contents

- proposal.md ✅
- specs/harden-frontend-build/spec.md ✅ (delta spec)
- design.md ✅
- tasks.md ✅ (6/6 tasks complete)
- verify-report.md ✅ (present — PASS with no blockers)
- archive-report.md ✅ (this file)

## Drift / Risks

- **None (specs vs implementation)**: no drift found — implemented code and verification evidence match the 6 requirements / 14 scenarios as specified; all design decisions D1–D7 followed per verify report.
- With-token render branches (HDR-L1 rows, HDR-M1 cards) marked **MANUAL-PENDING** in verify-report (non-blocking; no live backend + token in env); static contract verified.
- No `openspec/config.yaml` present; no `rules.archive` constraints applied (same as previous archive).

## Reconciliation Notes

- **Stale-checkbox reconciliation**: none needed — tasks.md already showed 6/6 `[x]` from sdd-apply; no exceptional repair performed.