# Exploration: contextual-video-redesign

Redesign of the video generation pipeline with contextual LLM integration.
Investigation only — no specs, proposals, or code changes were made.

## Current State

### 1. Video pipeline end-to-end

Entry point is `POST /api/v1/tenants/{tenant_id}/graph/run`
(`backend/routers/graph_execution.py:223`) which runs the LangGraph
`StateGraph` (`agents/graph.py:39` `build_agency_graph`) in background and
streams SSE events (`backend/sse_manager.py`). The graph is strictly linear:

```
ideation → human_approval_idea (interrupt_before) → scriptwriting
        → video_edit → human_approval_publish (interrupt_before) → publish → END
```

Step owners and the data they carry (all in the `AgencyState` TypedDict,
`agents/graph.py:20-37`):

- **ideation** (`agents/nodes/ideation.py:24`) → `run_ideation_crew`
  (`agents/crews/ideation_crew.py:20`): niche + market_map + live sanitized
  SearXNG trends → 5 candidate ideas, 5/50 gate + RUM score. Persists `ideas`
  rows (`backend/db/daos.py`).
- **scriptwriting** (`agents/nodes/scriptwriting.py:19`) →
  `run_scriptwriting_crew` (`agents/crews/scriptwriting_crew.py:19`): idea +
  niche_ppp + brand RAG context → 4-block script dict
  (`gancho_0_5s`, `contexto_5_30s`, `moraleja_30_50s`, `cta_50_60s`,
  `keyword`). Persists `scripts` row.
- **video_edit** (`agents/nodes/video_edit.py:20`): `run_video_prompt_crew`
  (`agents/crews/video_prompt_crew.py:18`) produces a 4-scene storyboard
  (`video_storyboard` in state), then calls the Celery task
  `trigger_video_render` (`workers/video_edit_task.py:28`) synchronously.
- **render** (`workers/video_edit_task.py`): runs the deterministic
  "Video Director" guardian (`agents/crews/video_director_crew.py:111`) which
  builds `render_payload = {title, script_text (4 blocks concatenated,
  truncated ~110 words), keywords, tenant_id, max_duration_seconds,
  requested_resolution}` and POSTs it to the renderer microservice (`:8001`).
- **renderer** (`microservices/renderer/app.py:188` `POST /render`): edge-tts
  over the whole `script_text`, Pexels b-roll by joined keywords (≤4 clips),
  MoviePy 9:16 compose (≤45s), upload to MinIO. Reports progress back to the
  backend `/progress` (→ SSE `render_progress`). Returns 201
  `{status, video_url, tenant_id, duration_seconds}`.
- **video persist**: `node_video_edit` writes the `videos` row
  (`backend/db/daos.py:120` `insert_video`, model `backend/db/models.py:144`).
- **publish** (`agents/nodes/publish.py:51`): builds caption from script
  blocks, posts to publisher `:8002/publish`
  (`microservices/publisher/app.py:45`, `PublishRequest`), with a sha256
  idempotency key (`publish.py:38`). Returns real `published_post_id` or
  fails honestly.

Data structures between steps: the `idea` dict, the `script` dict (the
"video plan"), the `storyboard` list (produced by `video_prompt_crew`,
`video_storyboard` in state), and the `render_payload` dict.

### 2. LLM call sites (production) and their context

Exactly four LLM call sites, all via the shared router
(`agents/llm.py`, proxy-first `motor-agencia` → direct gemini→groq→openrouter),
all async `acomplete()` (verified: commit `f00f9be`, RELIABILITY-003):

| Site | File:line | Produces | Context received |
|---|---|---|---|
| Ideation | `agents/crews/ideation_crew.py:64` | 5 ideas + RUM self-scores | niche, market_map, sanitized SearXNG trends (3 results, snippets truncated) |
| Scriptwriting | `agents/crews/scriptwriting_crew.py:67` | 4-block script | idea title, suggested gancho, niche_ppp, brand RAG (`query_rag_knowledge("personaje de marca")`) |
| Video prompting | `agents/crews/video_prompt_crew.py:73` | 4-scene cinematic storyboard | niche, idea title, product_image_url, the 4 script blocks |
| DM reply | `agents/nodes/dm_response.py:78` | lead reply (non-video) | RAG context + incoming message |

The "Video Director" crew (`video_director_crew.py`) is **not** an LLM: it is
a deterministic rule-based guardian — RUM quality is a character-length
heuristic (≥0.70), metadata curation is a template
(`"🚀 {title} | Caso Práctico 2026"`, description/hashtag templates), and
keywords are title words + fixed base terms (`extract_keywords_from_script`).

Context machinery that exists today:
- RAG MCP (`agents/mcp_servers/rag_mcp_server.py`): deterministic 384-dim
  hash embedding, Qdrant `marketing_brain` collection, Redis semantic cache;
  knowledge base in `agency/knowledge/` (brand_character, pdh_triangle,
  ppp_promise, filter_5_50, rum_formula, competitor_quadrants, ...).
- SearXNG MCP (`agents/mcp_servers/searxng_mcp_server.py`): `sanitize_html_content`
  (strip tags, collapse whitespace, snippet ≤400 chars) + synthetic fallback
  — used by ideation and by `trend_scraper_task` (`workers/trend_scraper_task.py:17`,
  writes `rag_cache["tendencia_{niche}"]`).
- RUM threshold per niche: `agents/criterion/rum_calculator.py:64`
  `get_dynamic_threshold` reads Redis `rum_threshold:{niche}` (EMA-recalibrated
  by `workers/metrics_loop_task.py:20`), clamped [0.50, 0.90].
- Qualifier: `agents/qualifier/lead_qualifier.py` keyword match against active
  campaigns — feeds the DM flow, not the video LLMs.

Weak/missing context:
- The RUM dynamic threshold of the niche is never injected into any LLM prompt;
  RUM scores are LLM self-assessed in ideation and gated by a hardcoded 0.70
  heuristic in the guardian.
- Scraped trends in `rag_cache["tendencia_{niche}"]` are never read by
  scriptwriting/video_prompt — ideation re-queries SearXNG live.
- Product context reaches video_prompt (IMAGE_TO_VIDEO) and the `products`
  table, but never the renderer or the director.
- RAG query in scriptwriting is a single fixed query "personaje de marca",
  not niche-scoped.

### 3. The storyboard disconnect (key finding)

`video_prompt_crew` produces per-scene prompts with timestamps, camera shots
and `visual_mode`, but:
- the local renderer (`:8001`) receives only the concatenated `script_text` +
  3-4 keywords — no scenes, no timestamps, no visual prompts, no per-block
  structure;
- `generate_storyboard_videos` (`agents/mcp_servers/video_gen_client.py:137`)
  is only used by `process_video_postproduction`
  (`workers/video_edit_task.py:142`), whose provider clients return mock
  `s3://.../mock_clip_scene_N.mp4` URIs in dev — and that task is **not**
  called by `node_video_edit`, so the graph path never consumes it;
- json2video (`agents/mcp_servers/json2video_client.py:56`) rebuilds its own
  4-scene structure (Pexels clip + azure voice + text per block);
- the storyboard is persisted to state (`video_storyboard`) and used for
  nothing else.

In short: money-class LLM work (scene prompts) is generated and then discarded;
the actual render is a single TTS blob over random keyword-matched b-roll.

### 4. Frontend surface a redesign would touch

- `frontend/src/features/VideoPreview/views/PublishApprovalView.jsx` — publish
  checkpoint card; reads `GET /tenants/{tenant}/scripts` (no `/videos` endpoint
  exists — `graph_execution.py:198`), shows latest script CTA + keyword,
  approve/reject → `POST /publish/approve`.
- `frontend/src/features/Pipeline/views/PipelineMonitorView.jsx` — node map +
  SSE console; starts the graph via `POST /graph/run` with IG creds from the
  tenant store.
- `frontend/src/features/Media/views/MediaGalleryView.jsx` — media gallery over
  `GET /tenants/{tenant}/media` (MinIO listing). **Has 6-insert/3-delete local
  modifications from another session (unrelated). NEVER touch in this change.**
- `frontend/src/features/Scriptwriting/views/ScriptInspectorView.jsx` +
  `Script4BlockReader.jsx` — script inspection.
- Frontend SSE hook `hooks/useSSEStream.js` subscribes to events
  `node_change` / `log_entry` / `checkpoint_paused`, while the backend emits
  `node_start` / `graph_complete` / `graph_error` / `render_progress` /
  `node_progress` — an existing event-name mismatch worth flagging, not fixing
  here.

### 5. Hard constraints (Agents.md §8, verified in code)

- **interrupt_before**: every graph node that publishes, spends tenant budget,
  or writes on the tenant's behalf MUST have a LangGraph `interrupt_before`
  (`Agents.md:290`; graph interrupts before `human_approval_idea` and
  `human_approval_publish` in `graph.py:63-66`).
- **serial video processing on dev**: 4 cores / 16 GB; Celery always
  `--concurrency=1`, video tasks strictly one at a time
  (`Agents.md:295`, `docker-compose.yml:114`); test mode uses eager Celery
  (`celery_app.py:42`).
- **sanitization wrapper**: web content reaching an LLM must go through the
  sanitizer (strip HTML, snippet ≤400 chars) — `searxng_search_sanitized`.
- **zero-token-spend tests**: crews that hit the LLM are unit-tested against a
  `fake_acomplete` seam asserting async-only calls (RELIABILITY-003,
  `tests/unit/test_ideation_crew.py:59-67`).
- RUM/filter thresholds come from Redis/DB, never hardcoded as globals.

### 6. Prior review (pipeline-production-gaps, b2038af..f00f9be) — all verified in HEAD

- S3 bucket private by default (`b2038af`).
- No fabricated video URL on render failure (`2b9e15f`; `video_edit_task.py:116-131`,
  honest `status: "failed"` path; propagated through `node_video_edit.py:43-49`
  and `process_video_postproduction.py:156-170`).
- Publisher timeout 150s + sha256 idempotency key (`0db4c7b`;
  `publish.py:35-48`).
- SSE `graph_error` on background graph failure (`908f627`;
  `graph_execution.py:50-90`, `sse_manager.py:54`).
- Async `acomplete()` in all four LLM call sites (`f00f9be`).

## Affected Areas

- `agency/microservices/renderer/app.py` — `RenderRequest` has no scene array;
  the contract to extend for scene-aware rendering.
- `agency/workers/video_edit_task.py` — builds and dispatches `render_payload`;
  would pass scenes through.
- `agency/agents/crews/video_director_crew.py` — deterministic guardian/data
  curator; candidate to become a (budget-guarded) contextual LLM director.
- `agency/agents/crews/scriptwriting_crew.py` / `video_prompt_crew.py` /
  `ideation_crew.py` — prompts to receive richer context (RUM threshold,
  cached trends, niche RAG).
- `agency/agents/mcp_servers/{rag,searxng}_mcp_server.py` — context source
  wiring (trend cache re-use, niche-scoped RAG).
- `agency/frontend/src/features/{VideoPreview,Pipeline,Scriptwriting}` — views
  that display pipeline output. NOT `Media/views/MediaGalleryView.jsx`.
- `agency/tests/unit/test_{ideation,scriptwriting,video_prompt}_crew.py` and
  `test_video_director_guardian.py` — zero-token-spend tests to extend for any
  new LLM call site.

## Approaches

1. **Scene-aware render contract** (close the storyboard disconnect)
   - Extend `RenderRequest` with `scenes: [{block_type, timestamp_range,
     text, keywords, visual_prompt}]`; renderer runs per-scene TTS + per-scene
     b-roll keyword search + per-scene duration; keep the flat `script_text`
     fallback for backward compatibility; map the same scenes to the
     json2video v2 API semantics.
   - Pros: directly monetizes the existing `video_prompt_crew` output; render
     quality improves without more LLM spend; additive API change.
   - Cons: touches a separately deployed service (coordinate deploy);
     json2video mapping adds surface; render time may grow (dev serial rule).
   - Effort: **Medium**.

2. **Contextual LLM director + richer prompt context**
   - Replace the template metadata curation with an LLM call fed by RUM score,
     niche threshold (from Redis), niche_ppp, product info and sanitized trend
     snippets → title/description/hashtags/keywords; inject RUM threshold +
     cached trends into scriptwriting/video_prompt prompts; run under the
     budget guard (`backend/services/llm_budget_service.py`) and honor the
     interrupt rule if the director ever writes on tenant behalf.
   - Pros: higher leverage on retention (titles/CTAs), bounded extra spend
     (one cheap call), reuses existing router seam; every new call stays on
     `acomplete` and is coverable by zero-token tests.
   - Cons: must not hardcode thresholds; needs explicit fallback (director
     currently runs offline-safe); +1 LLM call per video (serial latency).
   - Effort: **Medium**.

3. **Context convergence (RAG/trend reuse)**
   - Read `rag_cache["tendencia_{niche}"]` in scriptwriting/ideation contexts
     (so daily-scraped trends actually reach the writers) and make the brand
     RAG query niche-scoped.
   - Pros: cheap, no new services; uses existing sanitization.
   - Cons: cache-key conventions must be defined; low visual impact alone.
   - Effort: **Low-Medium**.

## Recommendation

The idea is coherent. Recommended path: **Approach 1 + 2 as the core change
(renderer scene contract + contextual LLM director), Approach 3 as an
in-scope extension.** Approach 1 is the highest-leverage fix because the
pipeline already spends LLM budget producing a storyboard that is silently
discarded; Approach 2 makes the "contextual" promise real at the content
layer. Keep the flat-payload fallback so the renderer contract stays
backward-compatible, and extend the zero-token-spend tests for any new call
site.

## Risks

- **CRITICAL**: Any new LLM call that spends tenant budget or writes must
  respect the interrupt_before rule and the LiteLLM per-tenant budget guard —
  otherwise it is a policy violation by definition (`Agents.md:290`).
- **CRITICAL**: The renderer (`:8001`) is a separate service. A scene-aware
  contract must be additive (flat `script_text` fallback) or deploys of
  backend worker + renderer must be coordinated; the video pipeline runs
  strictly serial on dev (4 cores) — richer renders must not assume
  parallelism.
- **WARNING**: `Media/views/MediaGalleryView.jsx` carries unrelated local
  modifications from another session — this change must never touch it.
- **WARNING**: Frontend SSE event names (`node_change/log_entry/...`) do not
  match backend emissions (`node_start/graph_complete/render_progress/...`);
  any frontend redesign must not assume the pipeline monitor is wired to
  render progress events.
- **WARNING**: video_gen_client provider paths return mock `s3://` URIs in
  dev; if the redesign revives per-scene clip generation, mock URIs must not
  leak into persisted `videos`/`edited_video_uri` state (reliability rule).
- **WARNING**: No `openspec/config.yaml` exists at repo root (sdd-init config
  not persisted) — the change folder follows the openspec convention only for
  the exploration artifact.

## Ready for Proposal

Yes. Tell the user: the redesign is coherent; the pipeline today generates a
storyboard that the renderer never consumes and a director that is purely
deterministic; the highest-leverage move is (1) a scene-aware renderer
contract wired to the existing `video_prompt_crew` storyboard and (2) a
budget-guarded contextual LLM director with RUM-threshold/trend context.
`pipeline-production-gaps` fixes (honest failures, SSE errors, idempotency,
async LLM) are all present in HEAD and create a safe foundation for this
change.