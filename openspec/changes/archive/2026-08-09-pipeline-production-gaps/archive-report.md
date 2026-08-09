# Archive Report: pipeline-production-gaps

- **Change**: pipeline-production-gaps (G-A real multi-provider LLM router + G-B real pipeline persistence + G-C honest publish wiring + REQ-API-06 real approve)
- **Archived at**: 2026-08-09
- **Status**: success
- **Mode**: hybrid (openspec filesystem + Engram)
- **Implementation commits**: `961edc3` → `022883a` (12 commits, WU-01, WU-02a, WU-02b, WU-03, WU-04), 30 files, +2202/−180

## Task Completion Gate

- [x] All implementation tasks checked in `tasks.md` (T-00…T-19, 20/20) — no stale unchecked tasks.
- [x] No open CRITICAL findings on the change at HEAD. The single CRITICAL surfaced during verify was a **concurrent-editor incident on the working tree, not the change**: uncommitted external edits to `agency/agents/nodes/ideation.py` (extracted helper referenced `selected_idea` out of scope → NameError; dropped id-injection) and `agency/backend/db/checkpointer.py` (try/except returning `None`). Incident RESOLVED before archive: tree restored to HEAD (verify `git status` shows neither file modified; HEAD=`022883a`), full suite re-run green **201 passed / 0 failed / 1 skipped**. The same run that had produced the CRITICAL (`196 passed / 5 failed / 1 skipped`) never touched the change commits — HEAD-only runs were always green.
- [x] All required artifacts present and archived (proposal, spec delta, design, tasks). `verify-report.md` lives in Engram (obs #217) — this change's verify phase persisted to Engram, not to a local file (hybrid mode).

## Specs Synced (delta → base)

| Domain | Action | Details |
|--------|--------|---------|
| api-llm-routing | Created | `openspec/specs/api-llm-routing/spec.md` — REQ-LLM-01/02/03, scenarios LLM-01-1..LLM-03-2 (3 reqs, 7 scenarios) |
| pipeline-persistence-writes | Created | `openspec/specs/pipeline-persistence-writes/spec.md` — REQ-PERSIST-01/02/03/04/05, scenarios PERSIST-01-1..PERSIST-05-2 (5 reqs, 10 scenarios) |
| api-publish-wiring | Created | `openspec/specs/api-publish-wiring/spec.md` — REQ-PUBLISH-01/02/03, scenarios PUBLISH-01-1..PUBLISH-03-2 (3 reqs, 7 scenarios) |
| api-ideas-scripts-brain-get | Updated | REQ-API-06 replaced (202 no-op → real `ideas.approval_status` UPDATE + honest publish approval, no fabricated ids); Purpose and Acceptance Criteria updated to match. All other requirements (REQ-API-1..REQ-API-05, 17 scenarios) preserved untouched |

## Verification Evidence

- **Full suite (run at HEAD after the concurrent-editor incident was resolved)**: `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/ -q` → **201 passed / 0 failed / 1 skipped**, exit 0. Only skip = real-key gate `tests/unit/test_llm_router.py:253` (`RUN_REAL_KEYS=1`).
- **Frontend build**: `NEXT_PUBLIC_API_URL=http://localhost:8000 NEXT_PUBLIC_SSE_URL=http://localhost:8000 NEXT_PUBLIC_ALLOW_LOCALHOST=true npm run build` (in `agency/frontend`) → exit 0.
- **Live docker proof**: postgres/backend/minio/searxng/qdrant/redis healthy; `products` table (migration 004, 1 row), `ideas` 3 rows, `checkpoints`/`checkpoint_blobs`/`checkpoint_writes`/`checkpoint_migrations` present with `thread_id=tenant UUID` rows → AsyncPostgresSaver lifespan ran for real.
- **Grep gates**: 0× `litellm.completion` in the 4 call sites (all `import agents.llm` → `llm.complete()/acomplete()`); `publish.py` has no fabricated `published_post_id` and no `s3://` default (requires `edited_video_uri`).
- **Requirements covered: 12/12** (REQ-LLM-01..03, REQ-PERSIST-01..05, REQ-PUBLISH-01..03, REQ-API-06).
- **Scenarios: 26/26** — 23 ✅ compliant, 3 ⚠️ partial (gated by real keys / manual docker harness, not implementation gaps):
  - LLM-03-1 (proxy reachable): compose config + manual `docker compose up litellm` harness; container not running at verify time.
  - LLM-03-2 (default chosen from evidence): real-key test skipped without `RUN_REAL_KEYS=1`.
  - PERSIST-04-1 (resume after restart): documented manual docker e2e; unit wiring + live checkpoint rows proven.
- **Design §9 TO VERIFY (4/4 resolved)**: (1) frontend IG token source = `activeTenant` (`PipelineMonitorView.jsx:22`); (2) products bucket private → `presigned_get_object` (`minio_client.py:121`, 3 live minio tests OK); (3) `edited_video_uri` reaches state via `video_edit.py` `render_res["video_url"]`, `publish.py` raises if absent; (4) lock regen via `uv pip compile requirements.txt -o requirements.lock`.
- **Design coherence (D1..D8)**: followed at HEAD — multi-provider router, `AsyncPostgresSaver` + `thread_id=tenant_id`, node persistence with DB id injection, honest publish `:8002` without `s3://` default, real MinIO + presigned private URL, frontend token/URL forwarding, real approve UPDATE.

## Implementation commits (`961edc3` → `022883a`)

| Commit | Message | Work unit |
|--------|---------|-----------|
| `961edc3` | feat(llm): add multi-provider LLM router with failover | WU-01 |
| `e66db20` | refactor(llm): route crews through shared router, drop direct litellm calls | WU-01 |
| `640ed5a` | feat(db): add products migration 004 and ORM models | WU-02a |
| `3199525` | feat(db): add async DAOs for product persistence | WU-02a |
| `0aa6ca9` | feat(agents): persist ideation/script/video rows via async DAOs | WU-02b |
| `406bfa0` | feat(api): upsert products from product-ingest and graph run state | WU-02b |
| `ba8e599` | feat(api): approve endpoint persists real approval decisions | WU-03 |
| `d7db06a` | feat(graph): persistent Postgres checkpointer with real resume | WU-03 |
| `15c99d1` | feat(publish): honest publish wiring to publisher service | WU-04 |
| `6b08643` | feat(storage): real MinIO upload with presigned URLs | WU-04 |
| `7e73c08` | feat(api): honest empty product_image_url when no file uploaded | WU-04 |
| `022883a` | feat(frontend): forward IG credentials and product_image_url on graph run | WU-04 |

## Engram Traceability

- `sdd/pipeline-production-gaps/verify-report` — obs **#217** (verify evidence, incident CRITICAL + resolution, scenario statuses).
- `sdd/pipeline-production-gaps/archive-report` — this report (mirrored to Engram).

## Drift / Risks

- **None (specs vs implementation)**: code and verification match all requirements/scenarios; the 3 partial scenarios are environment-gated (real keys / manual docker), not code gaps.
- Non-blocking follow-ups for the next change:
  1. `s3://` placeholder defaults OUTSIDE change scope remain: `agency/agents/nodes/video_edit.py:48` (`raw_video_uri`) and `agency/agents/mcp_servers/video_gen_client.py` (lines 39, 82, 114, 119, 124, 129, 134).
  2. No JS unit tests for PUBLISH-03-1/2 (source inspection + `npm run build` only).
  3. Production frontend build requires `NEXT_PUBLIC_ALLOW_LOCALHOST=true` (and API/SSE URLs) — `next.config.js:12-29` fails fast on production builds without them; a real deploy must supply them.
  4. `langgraph-checkpoint-postgres~=3.1.0` pinned in `requirements.txt`; re-validate if the lock is regenerated.

## Reconciliation Notes

- **Concurrent-editor incident (recorded, resolved)**: verify escalated with a CRITICAL because the working tree was modified DURING verification by an external actor (uncommitted `ideation.py` / `checkpointer.py` edits). Human reconciled: tree restored to HEAD, suite re-run **201 passed / 0 failed / 1 skipped**. No code fix or commit was made by verify/archive (verify contract preserved). Archive proceeds on the clean HEAD tree with the incident documented above.
- No other stale-checkbox or artifact reconciliation was needed — `tasks.md` showed 20/20 `[x]`, all artifacts present.