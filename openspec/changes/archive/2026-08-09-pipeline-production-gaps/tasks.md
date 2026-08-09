# Pipeline Production Gaps — Tasks

> Source: spec.md (12 reqs, 25 scenarios, 4 capabilities) + design.md (D1-D8, §6 forecast, §9 TO VERIFY) + verified code. Artifact language: neutral English (per scope contract). Strict TDD: RED test → GREEN implementation per unit; suite green per work unit.

## Review Workload Forecast (FINAL)

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1450 (authored, adds+deletes) |
| 400-line budget risk per unit | **Low** (every unit < 400; only ~1450 if merged in ONE unit — not allowed) |
| Chained PRs recommended | **No** |
| Suggested split | WU-01 → WU-02a → WU-02b → WU-03 → WU-04 (5 work units to main) |
| Delivery strategy | work-unit-sliced (direct-to-main) |

```
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Low
```

> **Decision (user, already taken)**: delivery straight to `main` as work-unit commits, NO chained PRs. Each work unit is < 400 authored lines, has a green suite, and is independently revertible via `git revert <wu-commit>` (design §8). Recalibrated per the gatekeeper mitigation: original Slice2 (~480) is split into WU-02a + WU-02b; all totals recomputed from the real code (design §6 was 380/480/190/350 → now 380/280/210/255/325).

### Suggested Work Units

| Unit | Slice | Goal | Focused test command | Runtime harness | Rollback boundary |
|------|-------|------|----------------------|-----------------|-------------------|
| WU-01 | Slice 1 | Shared LLM router + 4 call sites + proxy up (~380) | `.venv/bin/python -m pytest tests/unit/test_llm_router.py tests/unit/test_ideation_crew.py -p no:cacheprovider`1 | `docker compose up litellm`; real-key completion (REQ-LLM-03-2) | `git revert` of router commit → back to direct calls + templates (loop still works) |
| WU-02a | Slice 2a | 004 migration + `Product` ORM + async DAOs (persistence foundation) | `.venv/bin/python -m pytest tests/unit/test_daos.py tests/unit/test_video_metric_orm_alignment.py -p no:cacheprovider`1 | N/A (SQLite `db_session` fixture; 004 is ADD-only in initdb) | revert drops `products` only if 004 reverted; DAOs unused until WU-02b |
| WU-02b | Slice 2b | Async node writes via DAOs (ideas/scripts/videos + product upsert) | `.venv/bin/python -m pytest tests/unit/test_node_writes.py -p no:cacheprovider`1 | `docker compose up postgres` + `GET /ideas` / `GET /scripts` show rows | revert = nodes back to state-only; no rows written (empty states are valid UX) |
| WU-03 | Slice 3 | Real approve UPDATE + Postgres checkpointer | `.venv/bin/python -m pytest tests/unit/test_api_ideas_scripts_brain.py tests/unit/test_checkpointer.py -p no:cacheprovider`1 | `docker compose up postgres` e2e: pause at `human_approval_idea`, restart backend, resume same thread (PERSIST-04-1) | revert = approve back to no-op + MemorySaver; MemorySaver history discarded by design (PERSIST-04-2) |
| WU-04 | Slice 4 | Publish wiring `:8002` + real MinIO + frontend tokens/`product_image_url` | `.venv/bin/python -m pytest tests/unit/test_publish_wiring.py tests/unit/test_minio_real.py -p no:cacheprovider`1 + `cd ../frontend && npm run build` | `docker compose up minio video_publisher`; dev `token_` sim; no-token → security error | revert = stub minio + node_publish not wired; frontend bodies back to `{force_reideation}` |

Dependencies: WU-01 (none) → WU-02a (none; 004/migration independent) → WU-02b (needs its composed `Product`/DAOs) → WU-03 (needs `update_idea_approval` from WU-02a + idea rows from WU-02b for e2e) → WU-04 (needs T-00 bucket verdict + `edited_video_uri` state; independent of WU-03).

---

## Work Units

### WU-01 — Slice1: multi-provider LLM router (≈380 lines)
- Summary: `agency/agents/llm.py` router (proxy-first `LITELLM_PROXY_URL`+`LITELLM_MASTER_KEY` with model `motor-agencia`, then direct chain gemini→groq→openrouter) with sync `complete()` + async `acomplete()`; replace the 4 direct `litellm.completion` call sites; prove proxy `:4000` and pick default provider from a real-key test.
- Key files: `agency/agents/llm.py` (new), `agency/agents/crews/ideation_crew.py`, `agency/agents/crews/scriptwriting_crew.py`, `agency/agents/crews/video_prompt_crew.py`, `agency/agents/nodes/dm_response.py`, `agency/tests/unit/test_llm_router.py` (new).
- Commit msgs: `feat(llm): add multi-provider LLM router with failover` → `refactor(llm): route crews through shared router, drop direct litellm calls`.

### WU-02a — Slice 2a: persistence foundation (004 + ORM + DAOs)
- Summary: `products` DDL (migration 004, ADD-only, DDL-as-truth), `Product` ORM exactly matching 004, and `agency/backend/db/daos.py` async write layer (per-node unit-of-work on `AsyncSessionLocal`).
- Key files: `agency/migrations/004_add_products.sql` (new), `agency/backend/db/models.py` (+`Product`), `agency/backend/db/daos.py` (new), `agency/tests/unit/test_daos.py` (new).
- Commit msg: `feat(db): add products table, Product ORM, and async write DAOs`.

### WU-02b — Slice 2b: async node writes (≈210 lines)
- Summary: `node_ideation`/`node_scriptwriting`/`node_video_edit` become `async def` and write through DAOs; DB `idea_id` is injected back into each idea dict in state (so scriptwriting can FK it and approve can UPDATE it, design D3); `products` upsert in ideation when `product_image_url` exists (D8 / REQ-PERSIST-05).
- Key files: `agency/agents/nodes/ideation.py`, `agency/agents/nodes/scriptwriting.py`, `agency/agents/nodes/video_edit.py`, `agency/tests/unit/test_node_writes.py` (new).
- Commit msg: `feat(pipeline): persist ideas, scripts, and videos from async nodes`.

### WU-03 — Slice 3: real approve + Postgres checkpointer (≈280 lines)
- Spec: `approve_idea` performs a real `UPDATE ideas SET approval_status` then resumes the graph (REQ-API-06 reversed); `backend/db/checkpointer.py` factory (`FORCE_SQLITE` → `MemorySaver`, else `AsyncPostgresSaver` on a long-lived async conn, `thread_id=tenant_id`); lifespan setup; no MemorySaver migration (PERSIST-04-2).
- Key files: `agency/backend/routers/graph_execution.py`, `agency/backend/db/checkpointer.py` (new), `agency/backend/main.py`, `requirements.txt` + `requirements.lock` (+ `langgraph-checkpoint-postgres`), `agency/tests/unit/test_api_ideas_scripts_brain.py` (update approve tests), `agency/tests/unit/test_checkpointer.py` (new).
- Commit msgs: `feat(api): commit idea approvals in DB and resume graph` → `feat(api): swap checkpointer to AsyncPostgresSaver with SQLite fallback`.
- NOTES: `langgraph-checkpoint-postgres` and `minio` will be added to requirements.txt and regen lock via `uv` (see T-00 / logs). Add here; see WU-04.

### WU-04 — Slice 4: publish wiring + real MinIO + frontend (≈325 lines)
- Spec: `node_publish` POSTs to the real publisher `:8002` (`PUBLISHER_URL`, default `http://localhost:8002`); no tokens → real security error, NO fabricated `post_`/`s3://` defaults; dev `token_` sim stays on the microservice adapters; backend MinIO real SDK upload returning the URL that feeds `product_image_url`; frontend sends `ig_user_id`/`ig_access_token` (from session when present) + `product_image_url` in `/run` body.
- Key files: `agency/agents/nodes/publish.py`, `agency/backend/storage/minio_client.py`, `agency/frontend/src/features/Pipeline/views/PipelineMonitorView.jsx`, `agency/frontend/src/components/ProductIngestModal.jsx`, `requirements.txt` + `requirements.lock` (+`minio>=7.2.0`), `agency/tests/unit/test_publish_wiring.py`, `agency/tests/unit/test_minio_real.py`.
- Commit msgs: `feat(publish): wire node_publish to publisher :8002 with honest errors` → `feat(storage): real MinIO upload with presigned URL` → `feat(frontend): forward IG credentials and product_image_url on graph run`.

---

## Task list (T-00 → T-19)

### [x] T-00 — Pre-flight verification of design §9 TO VERIFY + run-interpreter check
- **Where**: no code; produces the task's verified decisions. Evidence (read in this session):
  1. **Frontend IG token source** (`design.md §9 #1`): no store holds `ig_user_id`/`ig_access_token` today — only `useAgentStore` (tenantId/nodes/logs) + `useTenantStore` (activeTenant metadata); `models.py` `Tenant` carries only `instagram_business_account_id` + `instagram_graph_api_token_ref`. **Verdict**: no session token exists; frontend MUST read `ig_user_id`/`ig_access_token` from the `activeTenant` object when present and omit them otherwise (honest PUBLISH-03-2). No OAuth endpoint (out of scope).
  2. **products bucket public vs pre-signed** (`#2`): default MinIO docker buckets are PRIVATE → `minio_client.py` must return a `presigned_get_object` URL unless `mc anonymous get viralsync-media` proves public. Accept via apply-time check.
  3. **edited_video_uri reaches state** (`#3`): VERIFIED by code — `video_edit.py:40-54` returns `edited_video_uri` from `render_res["video_url"]`; the `s3://…` default in `publish.py:11` is dead for successful runs and must be removed.
  4. **pip-compile workflow** (`#4`): VERIFIED — `requirements.lock` header: `uv pip compile requirements.txt -o requirements.lock`; `uv` at `~/.local/bin/uv`.
  5. (discovered) **test interpreter**: repo-root `venv/` lacks `sqlalchemy`; working interpreter is `agency/.venv` → canonical command from within `agency/`: `./.venv/bin/python -m pytest tests/`.
- **Acceptance**: each verdict documented in a `## Verificación` commit (or apply notes): 4 resolved items + corrected test command; blockers raised (none expected).
- **Commit msg**: `chore(verify): pre-flight pipeline assumptions for pipeline-production-gaps`

### WU-01

**[x] T-01 (RED)** — Write `agency/tests/unit/test_llm_router.py`
- `test_completion_returns_first_healthy_provider_text` (LLM-01-1: monkeypatch provider `completion` → returns text; assert LLM text, no template), `test_fallback_on_429_tries_next_provider` (LLM-01-2: gemini raises 429 → groq answers), `test_all_providers_fail_raises_honest_error` (LLM-01-3: error names reason), `test_real_key_default_skipped_by_default` tagged `@pytest.mark.real_keys` (REQ-LLM-03-2 gate).
  - Acceptance: suite RED for missing `agents.llm`.

**[x] T-02 (GREEN)** — implement `agency/agents/llm.py`
  - `complete(messages, temperature=None, max_tokens=None, ...) -> str` and async `acomplete(...)`; tries proxy (`LITELLM_PROXY_URL` + `LITELLM_MASTER_KEY`, model `motor-agencia`) then direct chain gemini→groq→openrouter (env keys `GEMINI_API_KEY`/`GROQ_API_KEY`/`OPENROUTER_API_KEY`); returns first success; raises `AllProvidersFailedError` naming providers on total failure.
- Acceptance: T-01 tests pass; no template substitution when a provider responds; honest error on total failure.

**[x] T-03 (RED)** — scan + LLM-02-2 tests
- Add to `tests/unit/test_ideation_crew.py` + new `tests/unit/test_llm_router.py` case: `test_no_direct_litellm_completion_in_call_sites` (LLM-02-1: scan the 4 files for `litellm.completion`) and `test_ideation_uses_llm_text_when_provider_responds` (LLM-02-2: monkeypatch `agents.llm.acomplete`; assert no fallback title `3 Errores...`).
- Acceptance: RED until T-04.

**[x] T-04 (GREEN)** — replace 4 call sites
- `ideation_crew.py` (lines 36-92), `scriptwriting_crew.py` (`45-96`), `video_prompt_crew.py` (`42-103`), `dm_response.py` (`59-113`): remove `import litellm` and `litellm.completion`, call `agents.llm` (async where the node is async), preserve per-site `temperature`/`max_tokens`; template fallback ONLY in the `except` all-providers-failed branch.
- Acceptance: T-03 passes; `grep -rn "litellm.completion"` in the 4 files → 0 hits.

**[x] T-05 (verify)** — proxy up (REQ-LLM-03-1/3-2, no new config: `docker-compose.yml:65-80` already defines `litellm`)
- `docker compose up litellm`; `curl -s http://localhost:4000/health` reachable; config `litellm_config.${AGENCY_ENV}.yaml` loads; run the tagged real-key test to FIX the default provider from evidence (never pre-claim).
- Acceptance: `:4000` health 200; default provider chosen from the observed responding provider, documented in a test.

### WU-02a

**T-06 (RED)** — `agency/tests/unit/test_daos.py`
- `test_product_columns_match_migration_004_exact` (PERSIST-01-2, DDL-as-truth; pattern from `test_video_metric_orm_alignment.py`), `test_daos_insert_ideas_returns_rows`, `test_daos_insert_script_fks_selected_idea` (PERSIST-02-1 unit), `test_daos_insert_video_fks_script`, `test_daos_upsert_product` (REQ-PERSIST-05), `test_daos_update_idea_approval_changes_status` (PERSIST-03 unit) — all on the `db_session` SQLite fixture.
- Acceptance: RED (no `Product` model; no `daos.py`).

**T-07 (GREEN)** — `agency/migrations/004_add-products.sql` + `Product` in `models.py`
- DDL: `CREATE TABLE IF NOT EXISTS products (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, name TEXT NOT NULL, description TEXT, product_image_url TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now()); CREATE INDEX idx_products_tenant ON products (tenant_id);`. Mounted by the existing `docker-entrypoint-initdb.d` volume (compose `postgres`) — no data backfill (ADD-only).
- `models.py`: `Product` (`__tablename__="products"`) with exactly those columns, `Uuid(as_uuid=False)` PK/FK convention; `create_all` must not clash with existing tables (per models.py convention).
- Acceptance: column-parity test green; `psql \d products` on docker Postgres shows the 5 columns.

**T-08 (GREEN)** — `agency/backend/db/daos.py` (new)
- Async functions using `AsyncSessionLocal`, one commit per call (per-node unit-of-work): `insert_ideas(tenant_id, ideas) -> list[Idea]`, `insert_script(tenant_id, idea_id, script) -> Script` (FK the approved idea), `insert_video(tenant_id, script_id, raw_video_uri, edited_video_uri) -> Video`, `update_idea_approval(tenant_id, idea_id, status) -> bool`, `upsert_product(tenant_id, product) -> Product`.
- Acceptance: T-06 green; `update_idea_approval` on non-UUID id → no-op `False` (e2e `"idea-e2e-001"` stays green).

### WU-02b

**T-09 (RED)** — `tests/unit/test_node_writes.py`
- `test_node_ideation_persists_rows_and_injects_db_ids` (mock `run_ideation_crew`; assert `ideas` count rows + `selected_idea["id"]` present), `test_node_scriptwriting_persists_script_row` (mock crew; FK to idea), `test_node_video_edit_persists_video_row` (mock `run_video_prompt_crew` + `trigger_video_render`; row carries `raw_video_uri`/`edited_video_uri`), `test_node_dao_failure_fails_honestly` (PERSIST-02-2: DAO raises → node propagates, no state-only success).
- Acceptance: RED until T-10.

**T-10 (GREEN)** — async nodes
- `agents/nodes/ideation.py`: `async def node_ideation`; after crew → `await insert_ideas(...)`, inject returned `id` into each idea dict + `selected_idea`; `await upsert_product(...)` when `product_image_url` present. `scriptwriting.py`: `async def node_scriptwriting` → `await insert_script(tenant_id, selected_idea["id"], script)`. `video_edit.py`: `async def node_video_edit` → `await insert_video(tenant_id, script["id"], raw_uri, edited_uri)`. LangGraph `ainvoke` supports async coroutine nodes — no graph topology change (`graph.py` untouched).
- Acceptance: T-09 green; `GET /ideas` and `GET /scripts` (via `ideas_router`/`scripts_router`) return real rows; run with no product → pipeline completes (PERSIST-05-2).

### WU-03

**T-11 (RED)** — update `agency/tests/tests/unit/test_api_ideas_scripts_brain.py`
- Replace `test_ideas_approve_returns_202_accepted_no_rows` (currently asserts no-op, REQ-API-06 old) with `test_ideas_approve_commits_approval_status` (PERSIST-03-1: seed pending `Idea` with real UUID; POST `/{t}/ideas/approve` `{idea_id, status:"approved"}` → 202 + `SELECT approval_status=="approved"` via `db_session`) and `test_ideas_reject_commits_rejected` (PERSIST-03-2). Keep `test_publish_approve_returns_202_no_fabricated_post_id` (API-06-2 unchanged).
- Acceptance: RED (status not committed today).

**T-12 (GREEN)** — real approve in `backend/routers/graph_execution.py` (`approve_idea`, lines 67-102)
- After SSE broadcast: `UPDATE ideas SET approval_status=:st WHERE id=:idea_id AND tenant_id=:tenant_id` via DAO/`AsyncSessionLocal`; keep `Command(resume=...)` + background resume; non-UUID id → UPDATE 0 rows (harmless).
- Acceptance: T-11 green; response stays `202 {status:accepted, kind:idea_approval, queued:true, idea_id}` (API-06-1).

**T-13 (RED)** — `tests/tests/unit/test_checkpointer.py`
- `test_build_checkpointer_force_sqlite_returns_memory_saver` (monkeypatch `FORCE_SQLITE=true`; instance of `MemorySaver`), `test_build_checkpointer_postgres_returns_async_postgres_saver` (mock import; assert `AsyncPostgresSaver` constructed), `test_no_memsaver_session_migration` (PERSIST-04-2, implied/documented non-goal).
- Acceptance: RED for missing `backend/db/checkpointer.py`.

**T-14 (GREEN)** — checkpointer + lifespan + deps
- `backend/db/checkpointer.py` `build_checkpointer()`: `FORCE_SQLITE` → `MemorySaver`; else `AsyncPostgresSaver(conn)` on a long-lived async psycopg connection from the app session engine; `thread_id=tenant_id` (same contract as today). `backend/main.py` lifespan: open conn + `await checkpointer.setup(conn)`, rebuild module-level `graph_app` from `get_graph_app()`. `graph_execution.py`: replace `global_memory = MemorySaver()` with the factory.
- Deps: add `langgraph-checkpoint-postgres` to `requirements.txt`; regen `requirements.lock` (`uv pip compile requirements.txt -o requirements.lock`). (psycopg2-binary already present; checkpoint-postgres pulls psycopg 3).
- Acceptance: `test_checkpointer.py` green; docker e2e PERSIST-04-1: run paused → restart backend → resume same thread (do NOT run this in CI/SQLite; manual with `docker compose up postgres`).

### WU-04

**T-15 (RED)** — `tests/tests/unit/test_publish_wiring.py`
- `test_node_publish_no_tokens_raises_security_error` (PUBLISH-02-3/01-2: no `ig_user_id`/`ig_access_token` → `ValueError`; `published_post_id` never set), `test_node_publish_calls_publisher_http` (PUBLISH-02-1: mock httpx → POST `{PUBLISHER_URL}/publish` with `tenant_id`/`video_url`/`caption`/user/token), `test_node_publish_no_edited_uri_raises` (removes `s3://` dead default), `test_node_publish_dev_token_simulated` (PUBLISH-02-2: dev `token_` → simulated via `adapters`, keep honest).
- Acceptance: RED before T-16.

**T-16 (GREEN)** — `agents/nodes/publish.py`: `async def node_publish`
- Read `ig_user_id`/`ig_access_token` from state; absent → `raise ValueError("... Token o User ID de Instagram ausente ...")` (mirror `adapters.py:31-33`), NO fictional id; present → `httpx.post(f"{PUBLISHER_URL}/publish", json=PublishRequest...)` (`PUBLISHER_URL` env, default `http://localhost:8002`); remove `f"post_{tenant_id[:8]}"` (`publish.py:36`) and `s3://` default (`publish.py:11`); `:8002` down → honest error (no sim).
- Acceptance: T-15 green; `grep -rn "post_"` in the node → no fabricated default.

**T-17 (RED)** — `tests/tests/unit/test_minio_real.py`
- `test_upload_product_image_calls_put_object` (mock `minio.Minio` → `put_object` called; returns real presigned/public URL), `test_minio_unreachable_raises_clear_error` (mocked connect error → raised, no fake URL), `test_helpers_keep_signature` (`save_product_photo_to_minio`/`get_tenant_media_list`/`delete_tenant_media_item` interface unchanged — `ingestion.py:159,189,198` depend on them).
- Acceptance: RED before rewrite.

**T-18 (GREEN)** — real `backend/storage/minio_client.py`
- Rewrite `MinIOStorageClient` with `minio.Minio` SDK: endpoint = `MINIO_ENDPOINT` stripped of scheme (pattern `renderer/app.py:35`), `bucket_exists(...)` + `make_bucket(...)`, real `put_object(bucket, key, data=file_bytes, length=...)` of the product photo; returned URL = `presigned_get_object` (or public root if the bucket policy is public — per T-00 verdict #2, default PRIVATE → presigned); commute only on genuine success. Deps: add `minio>=7.2.0` to `requirements.txt`, regen lock via `uv pip compile` (see T-00 #4).
- Acceptance: T-17 green; in docker `upload` places an object and reads it back; `product_image_url` non-null and real.

**T-19 (GREEN)** — frontend wiring
- `PipelineMonitorView.jsx` (handleRunGraph, line 17-21): body = `{force_reideation:false, ...(ig_user_id && ig_access_token ? {ig_user_id, ig_access_token} : {})}` — tokens from `useTenantStore().activeTenant` when present (PUBLISH-03-1), otherwise omitted and the run starts (PUBLISH-03-2).
- `ProductIngestModal.jsx` (line 52-56): `/run` body += `product_image_url: data.product_image_url` from the ingest response (already stored at line 47-49).
- Acceptance: `cd agency/frontend && npm run build` exit 0; frontend-structure pytest (`test_frontend_structure.py`/`test_frontend_features_phase*`) stays green.

### Shared verification commands

- Full suite (per unit, must stay green on each): `cd agency && ./.venv/bin/python -m pytest tests/` (conftest forces `FORCE_SQLITE=true` + `AGENCY_ENV=dev` — verified at `conftest.py:13`).
- Focused: the per-unit commands in the Work Units table (use `./.venv/bin/python` from `agency/` — repo root `venv/` lacks `sqlalchemy`, verified; `agency/.venv` has all deps).
- Frontend: `cd agency/frontend && npm run build`.
- Lock regen: `uv pip compile requirements.txt -o requirements.lock` (`uv` at `~/.local/bin/uv`; run from repo root after editing `requirements.txt`).
- Docker: `docker compose up litellm postgres minio video_publisher`; health `curl -s http://localhost:4000/health`, `curl -s http://localhost:8002/health`.

## Riesgos
| Risk | Lik | Mitigation |
|------|-----|------------|
| All 4 providers 429 at runtime | High | fallback chain; default fixed from real-key tagged test (REQ-LLM-03-2), never pre-claimed |
| Groq/OpenRouter unproven for this app | Med | real-key gate in T-05 before fixing default |
| sync→async node contract change | Med | isolated DAOs + per-node tests (T-09/T-10); graph topology unchanged |
| PG checkpointer breaks SQLite tests | Verifiable | factory returns `MemorySaver` under `FORCE_SQLITE` (T-13/T-14); PG e2e only in docker |
| `:8002` publisher unreachable | Med | `PUBLISHER_URL` default; honest error; mocked unit tests |
| Real approve with non-UUID `idea_id` (e2e `"idea-e2e-001"`) | Low | UPDATE on 0 rows is a no-op; frontend passes real UUIDs from GET /ideas |
| `products` bucket private → renderer can't read | Low | pre-signed URL decision in T-00 (verified) / T-18 |
| Worker tree dirty (uncommitted frontend changes at session start) | Low | per-unit commits only add touched files; `git status` review before each commit |
| `venv/` mismatch breaks the documented test command | Low (resolved) | canonical command uses `agency/.venv`; noted in T-00 |

1 The habit `-p no:cacheprovider` is optional; keep the doc **focused command** short. The real, always-green runner is `cd agency && ./.venv/bin/python -m pytest tests/`.