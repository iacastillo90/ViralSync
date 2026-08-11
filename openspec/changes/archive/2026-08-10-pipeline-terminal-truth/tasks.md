# Tasks: Pipeline Terminal Truth

> Source: spec.md (REQ-PTT-01..04, 11 scenarios) + design.md (D-A..D-G) + code verified at HEAD `be3e903`. Strict TDD: RED test → GREEN implementation per task; suite green at the END of every slice (no red window inside a slice). Zero-token only: crews/`agents.llm.acomplete` monkeypatched (`fake_acomplete`), publisher `fake_http`, DB `db_session` (SQLite StaticPool) — no real tokens, no docker, no `:8002`. Baseline verified at HEAD: `252 passed, 1 skipped` (canonical: `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/ -q`).

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines (total) | ~525 authored (adds+deletes) |
| Slice 1 (write-back) | ~165 |
| Slice 2 (topology + empty-candidates) | ~220 |
| Slice 3 (approve 404 + e2e) | ~140 |
| 400-line budget risk per slice | **Low** (each slice < 400; total ~525 > 400 ⇒ chained) |
| Chained PRs recommended | Yes |
| Suggested split | PR1 = Slice 1 → PR2 = Slice 2 → PR3 = Slice 3 (each →main) |
| Delivery strategy | auto-forecast (chained) |
| Chain strategy | stacked-to-main (cached) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low

> Decision status: `size:exception` already APPROVED (total ~525 > 400); `stacked-to-main` cached. No further user decision required.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| WU-1 | Slice 1: `update_video_publish` DAO; `video_id` in `AgencyState`; `node_video_edit` returns inserted row id; `node_publish` write-back after 2xx (REQ-PTT-01) | PR 1 (→main) | `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/unit/test_publish_wiring.py tests/unit/test_node_writes.py -q` | N/A — zero-token: publisher `fake_http`, write-back read-back via `db_session`; no real `:8002` | `git revert` WU-1 commits (daos.py, video_edit.py, publish.py, graph.py key) → publish state-only again; `video_id` drop harmless |
| WU-2 | Slice 2: positive `idea_rejected`/`publish_rejected` keys; `term_rejected` node + 2 `add_conditional_edges` sets; `NoCandidatesError`; SSE `code`/`terminal` (REQ-PTT-02/03) | PR 2 (→main) | `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/unit/test_node_writes.py tests/unit/test_api_ideas_scripts_brain.py -q` | N/A — zero-token: `MemorySaver` + crew monkeypatch | Revert graph.py + terminal.py + errors.py + ideation/scriptwriting + router payloads/SSE → unconditional edges restored |
| WU-3 | Slice 3: 0-row approve → 404 pre-broadcast; `Literal["approved","rejected"]` → 422; e2e Step 3 rewrite 202→404 + real-id 202 (REQ-PTT-04) | PR 3 (→main) | `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/unit/test_api_ideas_scripts_brain.py tests/e2e/test_full_pipeline.py -q` | N/A — ASGITransport in-process; resume mocked w/ counter; zero-token | Revert graph_execution.py 404/allowlist + e2e edits → legacy 202-on-0-row returns |

Dependencies (strict, no red window per slice): WU-1 (none) → WU-2 (needs `video_id` + state keys from WU-1) → WU-3 (needs router payload keys from WU-2 + honest e2e).

## Phase 1 — Slice 1: publish write-back (REQ-PTT-01, ~165 lines)

- [x] **TCK-001 (RED)** — Title: write-back contract tests. Files: `agency/tests/unit/test_publish_wiring.py` (extend `fake_http` pattern :80-100). Tests: `test_node_publish_persists_write_back_after_2xx` (PTT-01-1: monkeypatch publish-module `update_video_publish`; assert called once w/ `(tenant_id, video_id, post_id, published_at)` after 2xx + real id), `test_node_publish_skips_write_back_without_video_id` (PTT-01-3: no call, no crash), `test_node_publish_failure_never_writes_back` (PTT-01-2: `fake_http["raise_exc"]` → DAO never called). Zero-token ✓. Rollback: test-only.
- [x] **TCK-002 (RED)** — Title: video_id + DB-level write-back. Files: `agency/tests/unit/test_node_writes.py` (`T_IDS` per-tenant ids, `_fake_*` crew monkeypatches). Tests: `test_node_video_edit_exposes_video_id_from_insert_video` (D-A: `result["video_id"] == row.id`), `test_publish_write_back_persists_on_videos_row` (node_video_edit → node_publish w/ fake_http 2xx → row `instagram_post_id` set, `published_at` not None, `publish_approval_status` still `approved` — CHECK-safe, spec risk note). Zero-token ✓. Rollback: test-only.
- [x] **TCK-003 (GREEN)** — Title: write-back implementation. Files: `agency/backend/db/daos.py` (`update_video_publish(tenant_id, video_id, post_id, published_at) -> bool`: single UPDATE both cols WHERE id+tenant; non-UUID → False, `_is_uuid` :143), `agency/agents/graph.py` (declare `video_id` in `AgencyState` — D-A; langgraph drops undeclared), `agency/agents/nodes/video_edit.py:62` (capture `row = await insert_video(...)`, return `video_id`), `agency/agents/nodes/publish.py:103-117` (`if video_id: await update_video_publish(..., datetime.now(timezone.utc))` after real `post_id`; skip on absent ⇒ PTT-01-3; never called on raise ⇒ PTT-01-2). Acceptance: TCK-001/002 green; suite green. Rollback: WU-1 boundary. Est: co-test ~90 / prod ~75.

## Phase 2 — Slice 2: terminal topology + empty-candidates (REQ-PTT-02/03, ~220 lines)

- [x] **TCK-004 (RED)** — Title: rejection topology routes. Files: `agency/tests/unit/test_node_writes.py` (pattern `test_graph_ainvoke_runs_async_nodes_and_persists` :227-252: `build_agency_graph(checkpointer=MemorySaver())`, resume `Command`). Tests: `test_resume_rejected_idea_ends_term_rejected_no_script` (PTT-02-1: `{"idea_rejected": True}` → `terminal_state=="term_rejected"`, zero `Script` rows, scriptwriting crew never invoked — monkeypatch to raise), `test_resume_rejected_publish_ends_terminal_no_publish` (PTT-02-2: publisher never invoked), `test_resume_approved_idea_reaches_scriptwriting` (PTT-02-3: `idea_approved: True` → script row, unchanged), `test_resume_pending_self_repauses` (D-C fallback). Zero-token ✓ (MemorySaver + crew monkeypatch). Rollback: test-only.
- [x] **TCK-005 (RED)** — Title: empty-candidates + SSE honesty. Files: `test_node_writes.py` + `test_api_ideas_scripts_brain.py` (SSE region :389+). Tests: `test_node_ideation_empty_candidates_raises_no_candidates_no_rows` (PTT-03-1: crew → `[]` → `NoCandidatesError`; zero Idea/Script/Video rows), `test_node_scriptwriting_missing_idea_id_raises` (D-D); `test_graph_error_emits_code_for_coded_error`, `test_graph_complete_emits_terminal_when_present` (guarded `isinstance(final_state, dict)` — fake returning `None`). Zero-token ✓. Rollback: test-only.
- [x] **TCK-006 (GREEN)** — Title: terminal topology implementation. Files: `agency/agents/errors.py` (new: `class NoCandidatesError(Exception): code="no_candidates"`), `agency/agents/nodes/terminal.py` (new: `node_term_rejected` → `{"terminal_state": "term_rejected"}`), `agency/agents/graph.py` (add `idea_rejected`/`publish_rejected`/`terminal_state`; register `term_rejected`→END; `add_conditional_edges` after both approval nodes: `approved→next`, `rejected→term_rejected`, `pending→self` — D-C), `agency/agents/nodes/ideation.py:33` (raise `NoCandidatesError` when empty, BEFORE any write — PTT-03-1), `agency/agents/nodes/scriptwriting.py:32` (guard `selected_idea.get("id")` — D-D), `agency/backend/routers/graph_execution.py` (resume payloads add positive `idea_rejected`/`publish_rejected` — :180/:213, D-B; `emit_graph_error` + optional `code=getattr(exc,"code",None)` — sse_manager.py:54; `graph_complete` additive `terminal` when `terminal_state` present, guarded isinstance :74-86). Acceptance: TCK-004/005 green; legal-approve path unchanged (PTT-02-3). Rollback: WU-2 boundary. Est: co-test ~110 / prod ~110.

## Phase 3 — Slice 3: approve 404 + allowlist + e2e (REQ-PTT-04, ~140 lines)

- [x] **TCK-007 (RED)** — Title: approve honesty unit tests. Files: `agency/tests/unit/test_api_ideas_scripts_brain.py` (approve region :280-385). Tests: `test_ideas_approve_unknown_id_returns_404_no_resume` (PTT-04-2: non-existent UUID → 404; `_resume_graph_background` monkeypatched counter → 0 invokes), `test_ideas_approve_invalid_status_returns_422` (PTT-04-3: `"published"` → 422, no commit, no resume), `test_publish_approve_invalid_status_returns_422` (design: both approve models allowlisted). `test_ideas_approve_commits_approval_status` (:297) stays green (PTT-04-1). Zero-token ✓ (ASGITransport). Rollback: test-only.
- [x] **TCK-008 (RED)** — Title: e2e honest approve rewrite. Files: `agency/tests/e2e/test_full_pipeline.py` Step 3 (:69-80): 0-row `"idea-e2e-001"` → `assert res_idea_app.status_code == 404`; persist crew idea via `insert_ideas` → approve real UUID → 202 + `approval_status=="approved"` (PTT-04-1, spec risk note). Step 6 publish approve stays 202 (:104-109 — REQ-PTT-04 does not touch publish/approve). Zero-token ✓ (crew template fallback pattern). Rollback: test-only.
- [x] **TCK-009 (GREEN)** — Title: approve 404 + allowlist implementation. Files: `agency/backend/routers/graph_execution.py` (`IdeaApproveRequest.status` + `PublishApproveRequest.status` → `Literal["approved","rejected"]` :117-124 → 422 validation; `approve_idea` :142-188: UPDATE first — `if not updated` → `HTTPException(404, "idea not found or stale")` BEFORE SSE broadcast + resume — D-E; resume payload `{"idea_approved": st=="approved", "idea_rejected": st=="rejected"}`; real id keeps 202 + `approved` commit — PTT-04-1). Acceptance: TCK-007/008 green; full suite green. Rollback: WU-3 boundary. Est: co-test ~80 / prod ~60.

## Dependency order & zero-token constraint

Slices land strictly 1 → 2 → 3 (stacked-to-main): WU-1 (none) → WU-2 (needs `video_id` declared + graph keys) → WU-3 (needs router payload keys + honest e2e). Every slice ends with the full suite green (baseline at HEAD `be3e903`: `252 passed, 1 skipped`). Zero-token: every test touching LLM paths monkeypatches crews or `agents.llm.acomplete`; publish uses `fake_http`; DB via `db_session`; no docker/real tokens. Design Threat Matrix: N/A (no routing/shell/subprocess/VCS boundary).