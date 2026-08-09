# Pipeline Production Gaps — Design

> **Technical approach**: close G-A (real multi-provider LLM), G-B (real pipeline persistence) and G-C (honest publish wiring) on the existing codebase — tables and ORM already exist; this design only adds the writing layer and the real fallback points.

## 1. Context and Scope (spec summary)

Spec: 306 lines, 12 requirements, 25 scenarios, 4 capabilities: `api-llm-routing` (new), `pipeline-persistence-writes` (new), `api-publish-wiring` (new), `api-ideas-scripts-brain-get` (REQ-API-06 MODIFIED). Verified current state (code + Engram #207):

- **G-A**: 4 direct `litellm.completion` call sites (`ideation_crew.py:72-83`, `scriptwriting_crew.py:75-84`, `video_prompt_crew.py:81-90`, `dm_response.py:84-95`) with a single model and template fallbacks; the fallback pool in `gateway/litellm_config.dev.yaml` is dead code because the LiteLLM proxy (compose `litellm`, :4000) never runs. Gemini 429s today.
- **G-B**: `ideas/scripts/videos` tables and the async ORM already exist (001-003, `models.py`); **nothing writes** — nodes only update state (`ideation.py:14-33`, `scriptwriting.py:15-30`); `approve_idea` is a no-op; global `MemorySaver` checkpointer (`graph_execution.py:12,20-21`); no `products` table; backend minio is a stub (`minio_client.py:27-42`).
- **G-C**: full IG contract in `microservices/publisher/adapters.py` (+ `app.py POST /publish` :8002 in compose) but `node_publish` never wires it; frontend sends only `{force_reideation:true}` (`PipelineMonitorView.jsx:20`, `ProductIngestModal.jsx:55`); `GraphRunRequest` declares tokens and `product_image_url` but state arrives `None`.

Out of scope (extension points reserved): Meta OAuth connect, LLM-composed video design (metadata/title), MemorySaver session migration, TikTok/YouTube, frontend redesign.

## 2. Design Decisions

| # | Decision | Alternatives | Chosen and WHY (tradeoffs) |
|---|----------|--------------|---------------------------|
| **D1** | Shared LLM router `agency/agents/llm.py` + proxy up | (a) shared helper + `docker compose up litellm`; (b) only switch `LITELLM_DEFAULT_MODEL` to groq | **(a)** Single routing point (REQ-LLM-02), kills gateway dead code, free multi-provider failover. Tradeoff: +1 service (config/volume), touches 4 files. Router tries the proxy first (`LITELLM_PROXY_URL` + `LITELLM_MASTER_KEY`, model `motor-agencia` from the YAML — pool fallbacks resolved by LiteLLM) and, if unreachable, falls to a direct per-env chain gemini→groq→openrouter using `GEMINI_API_KEY`/`GROQ_API_KEY`/`OPENROUTER_API_KEY`. Default provider **not pre-claimed**: fixed only after a real-key test (REQ-LLM-03-2). Expose sync + async `complete()`; per-site temperature/max_tokens preserved. |
| **D2** | Postgres checkpointer (async lib + thread mapping) | (1) `AsyncPostgresSaver` (langgraph-checkpoint-postgres); (2) `AsyncSqliteSaver` | **(1)**. Graph runs via `ainvoke`, so an async saver matches the runtime without changing it; SQLite saver is not installed (`import langgraph.checkpoint.sqlite` fails today) and Postgres keeps one store with the pipeline DB. Mapping: `thread_id=tenant_id` (already used in `graph_execution.py`); `session_id` NOT set (one session per thread — same current contract). Requires `await saver.setup(conn)` in lifespan with a long-lived async connection. Tests (`FORCE_SQLITE=true` in conftest) cannot reach the PG saver → factory returns `MemorySaver` under `FORCE_SQLITE` (REQ-PERSIST-04-2 covers discarding; real resume proven with docker Postgres e2e). Tradeoff: new async psycopg dependency + lifespan setup. |
| **D3** | Async write DAOs | (a) new `backend/db/daos.py`, nodes become `async def`; (b) engine delegate (sync nodes, post-graph writer) | **(a)**. `node_ideation`/`node_scriptwriting`/`node_video_edit` become `async def` (LangGraph supports async nodes); each opens `AsyncSessionLocal` (session.py) with **per-node unit-of-work** (one commit: ideas, script, video). Isolated DAOs → node contracts testable without ad-hoc DB plumbing. Tradeoff: sync→async signature change (mitigated by per-node tests). Key: the DB `idea_id` returned by the DAO is injected into each idea dict in state so scriptwriting can FK it and approve can UPDATE it (REQ-PERSIST-03). |
| **D4** | Migration 004 + `Product` ORM + real approve | no products table (state-only) | **004 + ORM**. DDL-as-truth: `migrations/004_add_new_products.sql` (`tenant_id` FK, `name`, `description`, `product_image_url`, `created_at`) + `Product` in `models.py` with exactly those columns (column read-back test per the `test_video_metric_orm_alignment` pattern → PERSIST-01-2). `approve_idea` (`graph_execution.py:67-102`) runs `UPDATE ideas SET approval_status=:st WHERE id=:idea_id AND tenant_id=:tenant_id`, then resumes with `Command(resume=…)`. Tradeoff: REQ-API-06 semantics change → adjust existing tests (`test_ideas_approve_returns_202_accepted_no_rows`, e2e steps 3/6: UPDATE on 0 rows still passes if id is absent). |
| **D5** | Publish wiring: HTTP `:8002` vs direct adapter | (1) HTTP `POST {PUBLISHER_URL}/publish`; (2) `PublisherFactory` called in the node | **(1) HTTP :8002** with `PUBLISHER_URL` env (default `http://localhost:8002`). WHY: the IG poll (12×5s, `adapters.py:65-67`) is blocking and must not run on the backend async loop; the `PublishRequest`/`PublishResponse` contract already exists; the microservice is already in compose (`video_publisher` :8002); `token_` dev-sim lives in the micro's adapters (env `AGENCY_ENV=dev`). Tokens are request-scoped — `/graph/run` injects them into initial state, never persists (REQ-PUBLISH-01). No token → `node_publish` does not call anything and propagates the real security error (`adapters.py:31-33`), removing the fabricated `f"post_..."` default (`publish.py:36`). `:8002` down → honest 5xx, no simulation. Unit tests mock httpx. |
| **D6** | Real backend MinIO | current stub (in-memory registry); SDK `put_object` | **Real SDK** (`minio>=7.2.0` added to `requirements.txt` — backend does NOT have it today; the renderer does). `storage/minio_client.py` rewritten to `minio.Minio(endpoint stripped of scheme per `renderer/app.py:35`), `bucket_exists`+`make_bucket`, real `put_object` of bytes; returns the real public URL feeding `product_image_url`. Honest behavior: if MinIO is unreachable → clear error, never fake URL (env vars `MINIO_ENDPOINT/BUCKET/USER/PASSWORD` already present, `.env:73`). TO VERIFY: public bucket policy vs pre-signed URL for renderer consumption. |
| **D8** | `product_image_url` data flow ingest→state→DB (REQ-PERSIST-05) | skip (field already existed unused) | `GraphRunRequest` gains `product_image_url` (optional); `run` puts it in initial state (`graph.py:25` already declares it); in `node_ideation` (same unit-of-work as D3) a `products` upsert persists it (tenant FK + name/description/url). No product → graceful TEXT_TO_VIDEO (PERSIST-05-2). `ProductIngestModal.jsx` forwards the ingest response's url in the `/run` body (today `:52-56` omits it). The URL comes from the now-real `save_product_photo_to_minio` (D6). |
| **D7** | Implementation slices / order | single PR | **Forecast > 400 lines (§6) → 4 work-units to main**, suite green on each: (1) router+proxy substitute, (2) 004+DAOs+async nodes, (3) real approve + PG checkpointer, (4) publish wiring + real minio + frontend. Removes cross-dependencies, keeps commits reviewable. |

## 3. File Architecture

**New**

| File | Purpose |
|------|---------|
| `agency/agents/llm.py` | Multi-provider router (proxy-first + direct chain), `complete(...)` + async `acomplete(...)`; honest error naming the failed provider |
| `agency/backend/db/daos.py` | Async DAOs: `insert_ideas(tenant_id, ideas) -> list[Idea]`, `insert_script(tenant_id, idea_id, script) -> Script`, `insert_video(tenant_id, script_id, raw_uri, edited_uri) -> Video`, `update_idea_approval(tenant_id, idea_id, status)`, `upsert_product(tenant_id, product) -> Product` |
| `agency/migrations/004_add_products.sql` | `products` table (DDL-as-truth) |
| `agency/backend/db/checkpointer.py` | `build_checkpointer()`: `FORCE_SQLITE` → `MemorySaver`, else `AsyncPostgresSaver` on the lifespan connection |
| `agency/tests/unit/test_llm_router.py`, `test_daos.py`, `test_node_writes.py`, `test_publish_wiring.py`, `test_minio_real.py` | See §4 |

**Modified**

| File | Change |
|------|--------|
| `agency/agents/crews/ideation_crew.py`, `scriptwriting_crew.py`, `video_prompt_crew.py`, `agents/nodes/dm_response.py` | Replace direct `litellm.completion` with `agents.llm` (REQ-LLM-02); templates only in the `except` all-providers-failed branch |
| `agency/agents/nodes/ideation.py`, `scriptwriting.py`, `video_edit.py` | `async def` + DAO writes |
| `agency/agents/nodes/publish.py` | HTTP to `PUBLISHER_URL`; honest no-token error; remove fabricated id fallback |
| `agency/backend/routers/graph_execution.py` | `GraphRunRequest` + `product_image_url`; `get_graph_app()` via checkpointer factory; approve real UPDATE + SSE broadcast + resume; publish/approve honest (no ids) |
| `agency/backend/db/models.py` | + `Product` (exact 004 columns) |
| `agency/backend/storage/minio_client.py` | Real SDK upload; keep `save_product_photo_to_minio` / list helpers |
| `agency/frontend/.../ProductIngestModal.jsx` | `/run` body += `product_image_url` from ingest |
| `agency/frontend/.../PipelineMonitorView.jsx` | `/run` body += `ig_user_id`/`ig_access_token` from session when present (TO VERIFY session source in store) |
| `requirements.txt` + `requirements.lock` | + `minio>=7.2.0`, + `langgraph-checkpoint-postgres` (pulls psycopg) |
| `agency/backend/main.py` | lifespan: checkpointer setup + `graph_app` rebuild |

**Env/config**: `PUBLISHER_URL` (new, default `http://localhost:8002`); reuse `MINIO_*`, `LITELLM_PROXY_URL`/`LITELLM_MASTER_KEY`, `GEMINI/GROQ/OPENROUTER_API_KEY` (all in `.env.example`). Services: `docker compose up litellm postgres minio video_publisher`.

## 4. Test Plan

| Layer | What | How |
|-------|------|-----|
| Unit | Router (REQ-LLM-01 scn 1-3) | monkeypatch provider module: provider1 ok → LLM text, no template; 429 → next provider; all fail → logged honest error. Tagged real-key test (skip by default) for REQ-LLM-03-2 |
| Unit | DAOs (REQ-PERSIST-01/02) | `db_session` fixture (SQLite StaticPool): insert/select ideas, script FK idea, video FK script; product upsert; column parity `Product` ⊆ DDL 004 |
| Unit | Node writes (REQ-PERSIST-02-2) | mocked crews; assert row counts; DAO raising → node fails honestly (no state-only success) |
| Unit | Approve (REQ-PERSIST-03) | pending idea → POST approve approved/rejected → DB `approval_status` changes |
| Unit | Publish (REQ-PUBLISH-01/02) | no token → ValueError; token → mocked httpx hit `:8002`; dev `token_` → simulated by adapters; no fake id |
| Unit | MinIO (D6) | mock minio client → `put_object` called, real URL returned |
| E2E | Full pipeline (REQ-PERSIST-02-1) | extend e2e test: run nodes with mocked crews + assert idea/script/video rows; PG checkpoint resume after restart in docker |

**Suite**: `cd agency && ../venv/bin/python -m pytest tests/` (conftest forces `FORCE_SQLITE=true`, `AGENCY_ENV=dev`). Must stay green on every slice.

## 5. Risks & Mitigations

| Risk | Lik. | Mitigation |
|------|------|------------|
| Provider quota 429 at runtime | High | fallback chain; default fixed from real verify test (REQ-LLM-03-2), never pre-claimed |
| Groq/OpenRouter unproven for this app | Med | real-key tagged test before fixing default |
| sync→async node contract change | Med | isolated DAOs + per-node tests; no graph topology change |
| PG checkpointer breaks SQLite tests | Verifiable | factory returns `MemorySaver` when `FORCE_SQLITE`; PG e2e in docker |
| `:8002` publisher unreachable | Med | `PUBLISHER_URL` config; honest 5xx; mocked unit tests |
| Real approve with non-UUID `idea_id` (e2e uses `"idea-e2e-001"`) | Low | UPDATE on 0 rows is a no-op (test stays green); frontend must pass real UUIDs from GET /ideas. TO VERIFY in apply |
| `edited_video_uri` default s3://… unusable for real publish | Low | TO VERIFY: renderer public URL must reach state before publish wiring |
| Secret leakage | — | Artifacts reference env var names only |

## 6. Review Workload Forecast

Authored-line estimate (additions+deletions): router `llm.py` ~110 + 4 call sites ~160 + LLM tests ~110 → **Slice1 ≈ 380**; DAOs+models+004+async nodes ~360 + tests ~120 → **Slice2 ≈ 480**; approve+checkpointer ~120 + tests ~70 → **Slice3 ≈ 190**; publish+minio+frontend ~260 + tests ~90 → **Slice4 ≈ 350**. Total ≈ **1400**.

`Decision needed before apply: Yes`
`Chained PRs recommended: Yes` (if separate PRs per slice are preferred; user decision: direct-to-main work-unit commits, allowed with 4 slices each < 400 lines)
`400-line budget risk: High` (only if merged as a single PR — not allowed; individual slices < 400)

Implementation order per D7, verified per slice; each slice revertible via `git revert`.

## 7. Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, or executable-classification boundary. Only process-integration site is the **HTTP call to the publisher :8002** (no subprocess): expected failure = honest 5xx with zero fabricated ids (RED test REQ-PUBLISH-02-3 covered in §4 unit). LiteLLM proxy already defined in compose (healthcheck via :4000, REQ-LLM-03-1).

## 8. Migration / Rollout

004 is ADD-only (`CREATE TABLE IF NOT EXISTS`, mounted via `docker-entrypoint-initdb.d` volume; no data backfill). Checkpointer swap discards MemorySaver sessions (documented non-goal, REQ-PERSIST-04-2). Rollback per slice via revert; drop `products` only if 004 itself is reverted.

## 9. Open Questions

- [ ] Real source of `ig_user_id`/`ig_access_token` in the frontend session — TO VERIFY in apply
- [ ] `products` bucket public vs pre-signed URL for Image-to-Video render — TO VERIFY
- [ ] Does the renderer's real `edited_video_uri` (minio URL) arrive in graph state before publish? — TO VERIFY
- [ ] Confirm `requirements.lock` regeneration workflow (pip-compile) — TO VERIFY