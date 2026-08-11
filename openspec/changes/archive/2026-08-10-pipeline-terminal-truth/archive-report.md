# Archive Report: pipeline-terminal-truth

- **Change**: pipeline-terminal-truth — honest terminal state: publish write-back, rejection terminal (`term_rejected`), empty-candidates honesty, approve 202/404/422
- **Archived at**: 2026-08-10
- **Status**: success
- **Mode**: hybrid (openspec filesystem + Engram)
- **Implementation commits** (stacked-to-main, main, no push, no PR): `8f5e824` (WU-1 RED) → `b2ce5e3` (WU-1 GREEN write-back) → `72be04f` (TCK-004/005 RED) → `10bea8b` (TCK-004/005 GREEN terminal) → `967c22c` (TCK-007/008 RED) → `58c424f` (TCK-009 GREEN approve 404/allowlist). Base `be3e903` → head `58c424f`; 15 files, +1095/−63; authored changed lines 1158 (size:exception APPROVED, forecast ~525).
- **Delivery**: auto-forecast, chained stacked-to-main, review_budget_lines 400. PRs not pushed — user opens per slice if desired.

## Task Completion Gate

- [x] All implementation tasks checked in `tasks.md` — **9/9 `[x]`** (TCK-001..009), no stale unchecked tasks. No archive-time reconciliation needed.
- [x] No open CRITICAL verification findings: verify verdict **PASS** — full suite **271 passed / 0 failed / 1 skipped** (skip = pre-existing real-key gate `test_llm_router.py:281`); deterministic 5-file suite **66 passed**; 11/11 scenarios PASS; D-A..D-G honored in code.
- [x] Review receipt gate: bounded 4R review terminal — `reviews/receipt.json` `transaction_state: approved`, verdict `approved`, escalation false; `reviews/gate-context.json` `terminal_state: approved`, validated 2026-08-10. Ledger frozen: 22 findings, **0 blockers / 0 critical** (11 warnings + 10 suggestions + 1 insufficient — all info; 21 info rows + 1 inconclusive). No refuter/correction/scoped-validator launched.
- [x] All required artifacts present and archived (proposal, delta spec, design, tasks, reviews/). `verify-report.md` lives in Engram (obs #252), not as a local file — same hybrid pattern as `2026-08-09-pipeline-production-gaps`.

## Specs Synced (delta → base)

The change's delta spec is a single flat `spec.md` (repo single-file convention, aligning with archived `2026-08-09-pipeline-production-gaps/spec.md`). It modifies three canonical specs and adds one requirement. All syncs are additive/extending — no REMOVED or RENAMED requirements, no destructive merge.

| Domain | Action | Details |
|--------|--------|---------|
| api-publish-wiring | Updated | `openspec/specs/api-publish-wiring/spec.md` — **REQ-PUBLISH-02 extended** with publish write-back (persist `instagram_post_id` + `published_at` on the `videos` row, `publish_approval_status` stays `approved` — existing CHECK value, no migration; failure leaves row untouched; absent `video_id` on replay/resume → no write-back, no crash). Scenarios PUBLISH-02-1..3 preserved + **PTT-01-1/2/3 appended**. Purpose paragraph updated with the write-back sentence (consistency edit matching the merged requirement, per prior archive convention). REQ-PUBLISH-01/03 untouched. |
| pipeline-persistence-writes | Updated | `openspec/specs/pipeline-persistence-writes/spec.md` — **REQ-PERSIST-03 extended** with rejection-terminal semantics (rejected idea/publish routes the run to the distinct terminal state `term_rejected` → END; rejection final per run, no checkpoint resume re-enters scriptwriting/publish; re-approval requires a new run; rejected candidate stays `approval_status='rejected'` in DB; legal `approved` resume reaches scriptwriting unchanged). PERSIST-03-1 preserved; PERSIST-03-2 updated to assert the now-reachable `term_rejected`; **PTT-02-1/2/3 appended**. **ADDED REQ-PTT-03** (Empty-candidates honesty: no idea passes the 5/50 filter → honest visible "no candidates" error state, never `IntegrityError`, never paused; scenarios PTT-03-1/03-2). Purpose paragraph updated with rejection-terminal + no-candidates sentence. REQ-PERSIST-01/02/04/05 untouched. |
| api-ideas-scripts-brain-get | Updated | `openspec/specs/api-ideas-scripts-brain-get/spec.md` — **REQ-API-06 extended** with 0-row approve honesty (UPDATE matches no row → distinct non-202 error **404**, graph NOT resumed; valid `idea_id` keeps 202 + `approval_status` commit; `status` restricted to allowlist `approved\|rejected` → **422**, no commit/resume). Scenarios API-06-1/2 preserved + **PTT-04-1/2/3 appended**. Purpose paragraph updated with the 404/allowlist sentence (consistency edit). REQ-API-1..REQ-API-05 untouched. |

## Verification Evidence (linkage)

- **Verify report**: Engram obs **#252** (`sdd/pipeline-terminal-truth/verify-report`, `obs-1f581d33e8c69e0e`). Verdict **PASS** — REQ-PTT-01..04 all mapped to named passing tests (PTT-01-1..3, PTT-02-1..3, PTT-03-1..2, PTT-04-1..3 = 11/11 scenarios); D-A..D-G honored; TDD evidence validated from apply-progress obs #247 (RED files exist, GREEN on execution, triangulation 2–6 cases per behavior, no tautological assertions).
- **Full suite (HEAD `58c424f`)**: `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/ -q` → **271 passed / 0 failed / 1 skipped**. Deterministic suite (5 files): 66 passed (test_publish_wiring 11, test_node_writes 17, test_daos 11, test_api_ideas_scripts_brain 22, test_graph_execution_resilience 5).
- **E2E**: `test_full_pipeline.py` Step 3 rewritten — 0-row non-UUID `"idea-e2e-001"` → **404**; real persisted UUID → **202** + DB `approval_status=="approved"`. Step 6 publish approve untouched (still 202).
- **Zero-token**: every LLM-path test monkeypatches crews / `agents.llm.acomplete` (`fake_acomplete`); publisher `fake_http`; DB via `db_session` (SQLite StaticPool); e2e ASGITransport in-process; no real `:8002`, no docker.

## Review Gate Evidence (native 4R, terminal approved)

- `reviews/transaction.json` — `lineage_id: pipeline-terminal-truth-review-001`; snapshot base `be3e903` → head `58c424f` (6 commits); risk tier High; 4 lenses (review-risk, review-resilience, review-readability, review-reliability).
- `reviews/policy.md` — bounded policy: findings freeze after initial sweeps; WARNING/SUGGESTION rows are `info`, never drive correction or block approval.
- `reviews/ledger.json` — frozen; 22 findings: 0 blockers, 0 critical, 11 warnings, 10 suggestions, 1 insufficient; refuter/correction/scoped-validator not launched.
- `reviews/receipt.json` — `transaction_state: approved`; final verification approved; follow-up non-blocking items: REL-002 (Doc/API_CONTRACTS.md drift 202/404/422), RES-002 (SSE terminal/code have no frontend consumer), RISK-002/READ-002/REL-001/RES-001 (node_publish discards `update_video_publish` bool — silent 0-row write-back), READ-006 (1158 authored lines vs ~525 forecast), REL-004/REL-005 (real-LLM tests, pre-existing flake potential).
- `reviews/chain-bundle.json` + `reviews/gate-context.json` — portable recovery bundle + gate context (`terminal_state: approved`, validated 2026-08-10); lifecycle gates (pre-commit/pre-push/pre-PR/release) must call native review-validate with this gate context before any publication.

## Engram Traceability

| Artifact | Obs | Sync |
|----------|-----|------|
| proposal | #243 (`obs-c1794786bb4b694a`) | — |
| spec | #244 (`obs-3c261f380a84f67b`) | — |
| design | #245 (`obs-4076b712a5908f1e`) | — |
| tasks | #246 (`obs-23f8b6b894abb946`) | — |
| apply-progress | #247 (`obs-7562cd14196d951f`) | merged into this report (TDD table) |
| verify-report | #252 (`obs-1f581d33e8c69e0e`) | merged into this report |
| reviews/ (native 4R) | filesystem only (`openspec/changes/archive/2026-08-10-pipeline-terminal-truth/reviews/`) | archived with the change folder |
| **archive-report** | saved this phase (`sdd/pipeline-terminal-truth/archive-report`) | 3 delta syncs merged into `openspec/specs/`; folder → `openspec/changes/archive/2026-08-10-pipeline-terminal-truth/` |

## Archive Contents

- `archive-report.md` (this file) ✅
- `proposal.md` ✅
- `spec.md` ✅ (delta — flat single-file convention, per `2026-08-09-pipeline-production-gaps`)
- `design.md` ✅
- `tasks.md` ✅ (9/9 tasks complete, historical record — not rewritten)
- `reviews/` ✅ (`transaction.json`, `ledger.json`, `receipt.json`, `chain-bundle.json`, `gate-context.json`, `policy.md` — all persisted review artifacts)

Active `openspec/changes/` now contains only `archive/` — the change is no longer active.

## Commit / Uncommitted Consistency Notes

- Archive operations made **zero commits**: synced specs + archived change folder left uncommitted, consistent with the change folder being untracked since propose (planning artifacts were never committed by prior phases). The three synced main specs and the archived folder are ready to be committed by the orchestrator at the lifecycle gate with receipt validation (suggest `docs(openspec): archive pipeline-terminal-truth with consolidated delta specs`).
- No production code touched; no frontend files touched; no migration.

## Reconciliation Notes

- No stale-checkbox reconciliation needed (`tasks.md` 9/9 `[x]`).
- No destructive merge: only MODIFIED (REQ-PUBLISH-02, REQ-PERSIST-03, REQ-API-06 — extended, full requirement blocks replaced with merged text) and ADDED (REQ-PTT-03) applied; all requirements not mentioned in the delta preserved.
- No CRITICAL verification findings; no intentional partial archive; no deviations from the archive contract.
- No `openspec/config.yaml` and no `openspec/README` index exist in this repo — no index/roadmap update required (noted, skipped per convention check).

## Next Recommended

**none** — change closed. SDD cycle complete: planned, implemented (6 commits), verified (PASS, 271/0/1), reviewed (approved, 22 findings info/inconclusive), and archived. Non-blocking follow-ups for future changes: REL-002 (document 202/404/422 in `agency/backend/DOC/API_CONTRACTS.md`), RES-002 (frontend consumer for SSE terminal/code signals), RISK-002 (surface `update_video_publish` bool instead of discarding), READ-006 (keep slices under forecast next time).
