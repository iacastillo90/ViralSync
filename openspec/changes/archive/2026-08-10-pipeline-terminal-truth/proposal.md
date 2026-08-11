# Proposal: Pipeline Terminal Truth

## Intent

Make the LLM video pipeline's terminal state honest and persistent (debt verified at HEAD `be3e903`): publish success leaves `videos` stuck `pending` (RELIABILITY-007); rejection still resumes into scriptwriting/publish (RELIABILITY-004, PERSIST-03-2 unreachable); empty candidates crash with `IntegrityError` (RELIABILITY-008); 0-row approve looks like a real commit (RELIABILITY-009).

## Scope

### In Scope
- **Publish write-back (RELIABILITY-007)**: `update_video_publish` DAO; `video_id` declared in `AgencyState`; `node_publish` writes `published_post_id`+`published_at` on success. No migration (cols exist, `models.py:157-159`).
- **Honest rejection terminal (RELIABILITY-004/008 + PERSIST-03-2)**: conditional edges end the run at an honest END on `idea_approved=False`/`publish_approved=False`; empty candidates raise an honest error, not FK crash.
- **RELIABILITY-009**: approve distinguishes 0-row no-op; status allowlist `approved|rejected`.

### Out of Scope
MinIO honesty (slice 3: RISK-02/03/04/07, READABILITY-002, RESILIENCE-010); health honesty (slice 4: RESILIENCE-009); READABILITY-005 `complete_json`; legacy LLM sites; frontend.

## Capabilities

> Contract with sdd-spec. No new capability — three delta specs.

### New Capabilities
None.

### Modified Capabilities
- `pipeline-persistence-writes`: REQ-PERSIST-02 gains publish write-back; REQ-PERSIST-03 rejection terminates (PERSIST-03-2 reachable); ADDED empty-candidates honesty.
- `api-publish-wiring`: REQ-PUBLISH-02 — `node_publish` persists `published_post_id`/`published_at`.
- `api-ideas-scripts-brain-get`: REQ-API-06 — 0-row approve distinguishable; allowlist enforced.

## Approach

- **Slice 1**: `update_video_publish(tenant_id, video_id, post_id, published_at)` in `daos.py`; declare `video_id` in `AgencyState` (langgraph drops undeclared keys, `graph.py:20-37`); `node_video_edit` returns inserted `video_id`; `node_publish` updates row on success (skip if `video_id` absent).
- **Slice 2**: `add_conditional_edges` after both approval nodes gating on resume payload keys → END on reject; `node_ideation` raises honest "no candidates" when `ideas` empty (`ideation.py:33`); `node_scriptwriting` guards `selected_idea`.
- Rollback boundaries = slice boundaries (code revert, no migration); chain PRs per slice.

## Affected Areas

| Area | Impact | Change |
|------|--------|--------|
| `agents/nodes/publish.py:115-117` | Modified | write-back call on success |
| `backend/db/daos.py:134,151-168` | Modified | `update_video_publish`; allowlist |
| `agents/graph.py:55-59` | Modified | conditional edges → END |
| `agents/nodes/ideation.py:33` | Modified | honest empty-candidates error |
| `agents/nodes/scriptwriting.py:32` | Modified | guard |
| `backend/routers/graph_execution.py:117-122,166-188` | Modified | 0-row distinction; payloads |
| `tests/unit/test_publish_wiring.py`, `test_node_writes.py` | Modified | extend (fake_http, db_session) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Topology change breaks approved-resume→scriptwriting (e2e `test_full_pipeline.py:70-71,105-106` non-UUID idea + approved) | Med | conditional router keeps `approved` path; e2e stays green |
| SQLite lacks PG CHECK → values pass tests, fail prod (`001_init_schema.sql:132-133`: only pending/approved/rejected) | Med | design fixes status value pre-spec; new value ⇒ migration |
| Reject-vs-pending ambiguity (`idea_approved: False` = "not yet") | Med | design disambiguates signal (e.g. `idea_rejected`) |
| Write-back without `video_id` on replay/resume | Low | guard + node test |

## Rollback Plan

Revert per slice, code only, no migration — deploy-safe. Slice 2 rollback: restore unconditional edges in `graph.py`.

## Dependencies

None new: `add_conditional_edges` + `Command(resume=...)` already in use; publisher contract unchanged.

## Success Criteria

- [ ] Publish success → `videos` row has `instagram_post_id`+`published_at`; survives restart.
- [ ] Rejected idea → run ends at END; zero `scripts` rows (PERSIST-03-2).
- [ ] Rejected publish → run ends; publisher never invoked.
- [ ] Empty candidates → honest error, no `IntegrityError` (`models.py:154` FK).
- [ ] 0-row approve → response distinguishable from real commit.
- [ ] `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/ -q` green (baseline 251 passed / 1 skipped).

## Open Decisions (defer to design)

- Terminal `publish_approval_status` value (reuse `approved` vs new `published` ⇒ CHECK migration).
- END node naming; reject-vs-pending signal in resume payload.
- Checkpoint interplay: resume-after-reject must not re-enter scriptwriting.
- SSE signal for terminal states (`graph_complete` vs `graph_error` vs new event).