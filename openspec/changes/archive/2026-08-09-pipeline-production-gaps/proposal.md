# Pipeline Production Gaps — Proposal

**id**: pipeline-production-gaps

## Intent

Honest meta: leave the pipeline 100% real. Today the "real" LLM only exists behind a false door (template/fallback when the single model is rate-limited), the pipeline persists no product and no session (8 tenants, 0 rows), and publishing to Instagram authentically is impossible because there is no OAuth and no tokens in the graph state. This change closes the three gaps so that (a) the LLM runs contextually across the WHOLE loop with real multi-provider failover, (b) ideas/scripts/videos become real data visible in the UI, and (c) a real publish path is enabled whenever valid tokens exist. As a bonus, a scoped extension is positioned where the LLM composes the video design layer (metadata/title/narrative) without redesigning the renderer.

## Contexto

**G-A (real LLM)**: the four call sites (`ideation_crew.py`, `scriptwriting_crew.py`, `video_prompt_crew.py`, `dm_response.py`) call `litellm.completion(...)` directly with `LITELLM_DEFAULT_MODEL=gemini/gemini-3.5-flash`. The multi-provider fallback pool already exists in `gateway/litellm_config.{dev,staging,production}.yaml` (gemini→groq→openrouter→ollama) but is dead code: the LiteLLM proxy defined in `docker-compose.yml:65` never runs and the crews bypass it. Live logs (ago-09 04:31): `429 Too Many Requests — generate_content_free_tier_requests, limit: 20` followed immediately by "Usando fallback cinematográfico/en base de plantillas". Real credentials present: GEMINI (53 chars), GROQ (56), OPENROUTER (73), GITHUB_MODELS (40); empty/missing: OPENAI, ANTHROPIC, TOGETHER, and `PAID_API_KEY` (the production config references claude-3-haiku with a key that does NOT exist). `LITELLM_PROXY_URL` points at a dead proxy.

**Persistence (G-B)**: the ticket premise was partially wrong — the ideas/scripts/videos tables already exist (migrations 001-003) and the async SQLAlchemy ORM is configured and functional. The real hole: nobody writes. 8 tenants, 0 rows; `approve_idea` is an honest no-op; the checkpointer is `MemorySaver` (in-memory, lost on restart); no `products` table; backend minio is a stub. Alembic is a marker only (real migrations are static `.sql` mounted in initdb).

**Instagram OAuth / real publish (G-C)**: the real flow is fully implemented in `microservices/publisher/adapters.py` (media → poll → media_publish, GRAPH_API_VERSION v19.0) and the HTTP contract in `publisher/app.py` waits for `ig_user_id`/`ig_access_token`. But the frontend never sends tokens (`PipelineMonitorView.jsx` only sends `{force_reideation: true}`), there is no OAuth connect endpoint (no redirect/exchange/long-lived), tokens are not persisted, and the publisher :8000 is not wired. In dev the publish simulates only when `token.startswith("token_")`. Logs confirm: "Token o User ID de Instagram ausente."

**Video design research (contact point for the visual segment)**: rendering already runs `render_video(script, keywords)` → `json2video_client` builds 4 script blocks (hook/context/moral/cta) + Azure es-MX voice + Pexels clips from extracted keywords. The LLM gap is in the authorship layer: `curate_video_metadata` is a static template (NO LLM), the storyboard is static, and `product_image_url` exists in the graph state but NOBODY populates it (the frontend never sends it) → in practice always TEXT_TO_VIDEO. Conclusion: the LLM extension does not require touching the renderer — it composes metadata/narrative and populates `product_image_url` on the existing rendering path.

## Goals

- **G-A**: 100% of LLM calls in the loop go through a real multi-provider router with fallback; zero template usage when at least one provider responds. Default provider is **validated with curl/test against real credentials during verify** — not pre-claimed.
- **G-B**: every graph run writes real ideas/scripts/videos; `approve_idea` performs a real DB commit; the checkpointer survives restarts; existing GETs return real rows.
- **G-C**: OAuth connect + long-lived token persistence + token injection into graph state; real IG publish **only if valid real tokens exist**; dev keeps the honest `token_` simulation as fallback.
- **Video design (optional/post)**: LLM generates metadata/title/caption and populates `product_image_url` on the existing render path, no renderer redesign.

## Non-Goals

- Full visual redesign of the renderer or frontend.
- Meta app review / production OAuth if no real tokens: this change ships the honest wiring and the dev mode.
- Giant refactor: no full async migration of the graph, no SQLAlchemy engine replacement.
- Migrating existing MemorySaver sessions (the saver is swapped; in-memory history is discarded).
- TikTok/YouTube/other platforms.
- Real backend minio and media storage (only the existing real renderer is integrated).
- No secrets in the repo: only env var names.

## Approach / Proposed decisions with tradeoffs

### G-A — Real LLM router + multi-provider fallback (Medium)
- **Option A (recommended)**: shared helper `backend/agents/llm.py` with a router (gemini→groq→openrouter→ollama) + bring up the LiteLLM proxy (`docker compose up litellm`); replace the 4 direct call sites.
  - Tradeoffs: removes gateway dead code and centralizes config under free-tier cost; costs touching 4+ files and adds a service dependency (config/volume).
- **Option B (minimal)**: only switch `LITELLM_DEFAULT_MODEL` to `groq/llama-3.3-70b-versatile` + per-crew catch fallback. Less surface, no centralization.
- **Honesty**: the default is declared in verify via `curl` (or test) against real keys; today Gemini is 429ing and Groq/OpenRouter are untested for this app.

### G-B — Table writes + async DAOs + products table + persistent checkpointer (Medium)
- Migration 004 (`products` table) + `Product` in models; async DAO layer for ideas/scripts/videos; `ideation`/`scriptwriting` nodes write via DAO; `approve_idea` = real commit; post-graph writer for outputs.
- Checkpointer: `AsyncSqliteSaver` if available with the current install, else `langgraph-checkpoint-postgres` (new dependency; tradeoff of config/initdb).
- Tradeoffs: touching nodes changes the graph contract (mitigable with per-node tests); a good chunk is done (tables+ORM); MemorySaver sessions are not migrated.
- **Spec impact**: `api-ideas-scripts-brain-get` defines approve/publish as 202 no-ops — this change REVERSES that semantics to a real commit → modified capability.

### G-C — OAuth connect + token persistence + wiring (Large; requires decision)
- New endpoints: IG redirect → exchange → long-lived token persisted per tenant; `POST /graph/run` injects `ig_user_id`/`ig_access_token` from the user session; `node_publish` connects to the `publisher` microservice :8002 or directly to adapters (reuse the ready contract).
- Dev: use the stored TEST_* token as fallback.
- Tradeoffs: real OAuth needs Meta app review + redirect URI + UI connect flow; without it, the honest maximum is dev `token_` mode. **Open to the user**: slice 3 inside this change or as a separate change.

### Video design with LLM (post-slide note)
- No renderer redesign. The LLM composes `title`/metadata/caption (today a static template) and populates `product_image_url` to enable real IMAGE_TO_VIDEO. Cost: one crew task + state values. Proposed as an optional post-change slice, out of this change's core unless the user says otherwise.

## Proposed slices

1. **Slice 1 — backend pipeline (G-A + G-B + wiring)** — core of this change:
   - `llm.py` router + proxy up / replacement of the 4 direct calls (decision A/B).
   - Async DAOs + migration 004 (products) + node writes + real approve + persistent checkpointer.
   - Full wiring: `product_image_url` populated from ingest (data) and state queryable.
2. **Slice 2 — video design LLM (optional = post, suggested)**: metadata/title/caption LLM on the current render path (no renderer changes).
3. **Slice 3 — real OAuth (large, requires user decision)**: connect/exchange/long-token + secure token persistence + wiring into `/graph/run`; only if real tokens are available; otherwise the honest `token_` simulated path remains.

## Capabilities (contract with sdd-spec)

### New Capabilities
- `api-llm-routing`: multi-provider router with fallback + shared helper + validated default.
- `pipeline-persistence-writes`: async DAOs, `products` table, real approve, persistent checkpointer.
- `api-instagram-oauth-connect` (only if Slice 3 is in scope): OAuth endpoints + token persistence.

### Modified Capabilities
- `api-ideas-scripts-brain-get`: REQ-API-06 is invalidated — approve/publish stop being 202 no-ops and become real commits (and real publish if OAuth is in scope).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agency/agents/crews/{ideation,scriptwriting,video_prompt}_crew.py`, `agents/nodes/dm_response.py` | Modified | direct call → shared router |
| `agency/backend/agents/llm.py` (new) | New | multi-provider router helper |
| `agency/backend/db/models.py` + `migrations/004_*.sql` | New/Modified | write DAOs + `products` table |
| `agency/agents/nodes/{ideation,scriptwriting}.py` | Modified | write graph state via DAO |
| `agency/backend/routers/graph_execution.py` | Modified | real approve + persistent checkpointer + token injection |
| `agency/frontend` (GraphApi / PipelineMonitor / ProductIngestModal) | Modified | send tokens + `product_image_url` to the graph |
| `agency/backend/routers/instagram_oauth.py` (Slice 3) | New | OAuth connect/exchange |
| `agency/backend` publisher wiring (node_publish → :8001 / adapters) | Modified | real IG publish path |

## Risks and open decisions

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Default provider 429/no quota at run time | High | default chosen in verify via curl; fallback chain; no pre-claimed success |
| Groq/OpenRouter keys unproven for this app | Med | real test in verify before fixing the default |
| Nodes becoming async/DB changes the graph contract | Med | isolated DAOs + per-node tests |
| Checkpointer migration loses in-memory sessions | Low | no historical value; discard |
| OAuth: no real tokens / value review | High | Slice 3 gated by user decision; honest dev `token_` mode |
| Secret leakage | Low | only env var names in artifacts |

**Open decisions**: (1) default provider and option A vs B for G-A; (2) SQLite vs Postgres excel-saver checkpointer; (3) Slice 3 (OAuth) in this change or a separate change — the only large infra piece, requires the user to decide; (4) Slice 2 video design in this change or post.

## Acceptance criteria (tests)

- [ ] LLM router: with at least one real key responding, the crews produce LLM text (no template); default proven in verify with `curl`; `pytest` unit runs with mock key + real-key tagged test.
- [ ] G-B: run graph → rows in ideas/scripts/videos (assert via psql / `pytest` with SQLite); `approve_idea` commits (no-op removed); UI GETs show real rows.
- [ ] Checkpointer: new saver survives a backend restart (no fabricated data).
- [ ] `products` table populated and `product_image_url` non-null when a product exists.
- [ ] (Slice 3) OAuth connect/exchange returns a long-lived token; simulated `token_` publish keeps working in dev.
- [ ] `pytest` green; `docker compose up -d` exits 0; `npm run build` exits 0.

## Rollback Plan

Per slice: `git revert` of the backend PR returns to (a) template fallbacks — the loop keeps working, (b) no-op approve, (c) empty GETs (empty states are already valid UX). Slice 3 revert restores the dev simulation. Non-destructive: migration 004 is ADD-only; revert drops the table if needed through the PR revert.

## Dependencies

- Postgres with migrations 001-003 applied (present; 11 tables).
- Real env vars GEMINI/GROQ/OPENROUTER (G-A) and `TEST_INSTAGRAM_ACCESS_TOKEN` (G-C dev).
- LiteLLM proxy optional in Option A (`docker compose up litellm`).
- (Slice 3) Meta app OAuth: redirect URI, existing app secret, user decision, and app review if production is desired.