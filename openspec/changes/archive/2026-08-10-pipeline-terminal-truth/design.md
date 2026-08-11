# Design: Pipeline Terminal Truth

## Technical Approach

Three additive, deploy-safe slices on the existing graph/DAO layer (aligns with archived 2026-08-09-pipeline-production-gaps D3/D5): (1) publish write-back via one atomic DAO UPDATE, `video_id` declared in `AgencyState`; (2) conditional edges routing rejection to a new `term_rejected` node, plus an honest empty-candidates error; (3) 0-row approve → 404 and a `status` allowlist. No migration — columns exist (`models.py:158-159`); prod CHECK (`001_init_schema.sql:132-133`) stays `pending|approved|rejected`. Zero-token tests reuse existing fakes (`fake_http`, `db_session`, crew monkeypatch).

## Architecture Decisions

| # | Decision | Chosen / Why |
|---|---|---|
| D-A | `video_id` flow | Declare `video_id` in `AgencyState` — langgraph drops undeclared keys (`graph.py:20-37`). `node_video_edit` captures the `insert_video` return row (discarded today, `video_edit.py:62`) and sets `video_id`; `node_publish` reads it. |
| D-B | Rejection signal | New positive keys `idea_rejected`/`publish_rejected` set by resume payloads. `idea_approved: False`/absent stays "not yet" — no conflation; legal `approved` resume routes to scriptwriting unchanged (PTT-02-3, e2e green). |
| D-C | Topology | `add_conditional_edges` after both approval nodes: `approved→next`, `rejected→term_rejected` (new node → END), `pending→self` (re-pause; only reachable via malformed resume — endpoints always send exactly one flag). Rejection FINAL, no path re-enters scriptwriting/publish → PERSIST-03-2 reachable. |
| D-D | Empty candidates | `NoCandidatesError(code="no_candidates")` raised in `node_ideation` before any write; propagates to existing `graph_error` SSE with additive `code`. Never `IntegrityError`, never paused. `selected_idea.id` guard in `node_scriptwriting` (defense-in-depth). |
| D-E | 0-row approve | **404** — the tenant-scoped UPDATE matched no row, so the resource is absent; 409 implies conflict on an existing resource and no versioning exists. Check in `approve_idea` on the DAO bool, BEFORE SSE broadcast + resume; `status` → `Literal["approved","rejected"]` → 422, no commit/resume. |
| D-F | Write-back atomicity | One `update_video_publish(tenant_id, video_id, post_id, published_at)` UPDATE (both columns) only after POST 2xx with a real post id; `if not video_id: skip` (PTT-01-3); publisher raise ⇒ no call (PTT-01-2). `publish_approval_status` untouched → stays `approved` (CHECK-safe). |

## Data Flow

```
ideation → human_approval_idea ─(approved)→ scriptwriting → video_edit → human_approval_publish ─(approved)→ publish → END
                │ (rejected)                                  │ (rejected)
                └──→ term_rejected → END                      └──→ term_rejected → END
video_edit: insert_video → row.id → state{video_id}
publish:    POST :8002 2xx → update_video_publish(video_id) → state{published_post_id}
```

## Interfaces / Contracts

```python
# AgencyState additions
video_id: str; idea_rejected: bool; publish_rejected: bool; terminal_state: str

# agents/errors.py (new)
class NoCandidatesError(Exception): code = "no_candidates"

# daos.py
async def update_video_publish(tenant_id, video_id, post_id, published_at) -> bool

# graph_execution.py
status: Literal["approved", "rejected"] = "approved"   # both approve models
# 0-row → HTTPException(404, "idea not found or stale"); no broadcast, no resume
# resume payloads: {"idea_approved": st=="approved", "idea_rejected": st=="rejected"}
```

## File Changes

| File | Action | Description |
|---|---|---|
| `agents/graph.py` | Modify | 4 state keys; `term_rejected` node; 2 conditional-edge sets |
| `agents/nodes/video_edit.py` | Modify | capture insert row, return `video_id` |
| `agents/nodes/publish.py` | Modify | write-back after 2xx; `video_id` guard |
| `agents/nodes/ideation.py` | Modify | raise on empty candidates |
| `agents/nodes/scriptwriting.py` | Modify | `selected_idea.id` guard |
| `agents/nodes/terminal.py`, `agents/errors.py` | Create | `node_term_rejected`; `NoCandidatesError` |
| `backend/db/daos.py` | Modify | `update_video_publish` |
| `backend/routers/graph_execution.py` | Modify | 404 check, Literal statuses, payloads, terminal SSE (guard `isinstance(final_state, dict)`) |
| `tests/unit/test_publish_wiring.py`, `test_node_writes.py` | Modify | write-back / skip / no-write-on-fail; video_id; empty→error 0 rows |
| `tests/unit/test_api_ideas_scripts_brain.py` | Modify | 404 + 422 cases |
| `tests/e2e/test_full_pipeline.py` | Modify | Step 3 per REQ-PTT-04 (below) |

## E2E Update (REQ-PTT-04 — same change)

`test_full_pipeline.py:69-80` Step 3 posts non-UUID 0-row `"idea-e2e-001"` and asserts 202:

```python
res_idea_app = await ac.post(
    f"/api/v1/tenants/{tenant_id}/ideas/approve",
    json={"idea_id": "idea-e2e-001", "status": "approved"},   # :70-71
    headers=auth_headers,
)
assert res_idea_app.status_code == 202                          # :74
...
assert idea_body["idea_id"] == "idea-e2e-001"                   # :80
```

→ must become 404 (0-row, no resume). Update Step 3 to (a) assert 404 for the 0-row id, (b) persist the crew idea via `insert_ideas` and approve its real UUID → 202 + `approved` commit (PTT-04-1). Step 6 (`:104-109`) publish approve keeps 202 — REQ-PTT-04 does not touch publish/approve.

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit | write-back success / skip / fail | `fake_http` + `db_session`; absent `video_id` → no UPDATE |
| Unit | topology routes | `build_agency_graph` + resume `Command` flags → next node / `term_rejected` |
| Unit | empty candidates | monkeypatch crew `[]` → `NoCandidatesError`, zero rows |
| Unit | approve 404 / 422 | ASGITransport; no resume (fake graph counts invokes) |
| E2E | honest approve | Step 3: real-id 202 + 0-row 404 |

Suite: `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/ -q` green per slice (baseline 251 passed / 1 skipped).

## Rollback / Work Units (D-G — stacked-to-main)

| Slice | Content | Est. lines | Rollback |
|---|---|---|---|
| 1 | write-back + `video_id` (REQ-PTT-01) | ~165 | `git revert` |
| 2 | topology + terminal + empty-candidates (REQ-PTT-02/03) | ~220 | revert `graph.py` + nodes |
| 3 | approve 404 + allowlist + e2e (REQ-PTT-04) | ~140 | revert router + e2e |

Each slice < 400 (review_budget_lines); total ≈ 525 (>400, size:exception APPROVED per preflight). Suite green per slice; code-only revert, no migration; no frontend changes.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, or executable-classification boundary. Only process-integration site is the publisher HTTP call (behavior unchanged; failure already honest).

## Migration / Rollout

No migration. Columns already exist; additive only; deploy-safe per slice.

## Open Questions

None blocking. SSE wire shape resolved additively: `graph_error` gains `code` (`getattr(exc, "code", None)`); run/resume success broadcasts `graph_complete` with optional `terminal` when `terminal_state` present.