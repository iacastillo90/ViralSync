# Proposal: Contextual Video Redesign — Scene-Aware Renderer + Budget-Guarded LLM Director

## Intent

The pipeline spends LLM budget generating a 4-scene cinematic storyboard the renderer never consumes, and the "Video Director" is deterministic template-craft with zero LLM or niche context. One additive, backward-compatible slice fixes both: wire the existing `video_prompt_crew` storyboard into the renderer via a `scenes[]` contract, and replace template metadata curation with a budget-guarded contextual LLM director fed by the RUM dynamic threshold, sanitized trend cache, and RAG context.

## Scope

### In Scope
- Additive `scenes[]` on renderer `RenderRequest` (per-scene TTS, b-roll, duration); flat `script_text` fallback retained.
- `video_edit_task.py` forwards storyboard scenes into `render_payload`.
- Contextual LLM director (title/description/hashtags/keywords) via shared router `acomplete()`, gated by `check_tenant_llm_budget`; deterministic fallback when budget is exhausted.
- Inject RUM dynamic threshold and sanitized `rag_cache["tendencia_{niche}"]` into scriptwriting/video_prompt prompts.
- Tests: scene serialization, budget decisions, director prompt build (zero token); Celery eager + mocked renderer integration.

### Out of Scope
- json2video v2 scene mapping; niche-scoped RAG rewrite; frontend views (MediaGalleryView.jsx NEVER touched); SSE event-name mismatch fix.

## Capabilities

### New Capabilities
- `video-scene-render-contract`: additive scenes[] protocol, flat script_text fallback, per-scene TTS/b-roll/duration.
- `contextual-video-director`: budget-guarded LLM metadata curation; RUM/trend context injection.

### Modified Capabilities
- `api-llm-routing`: director is a new call site and MUST use the shared router `acomplete()`.

## Approach

Reuse existing seams: storyboard already held in graph state, shared router (`agents/llm.py`), `check_tenant_llm_budget` (pattern from `dm_response.py:62-69`), sanitization wrapper, Redis `rum_threshold:{niche}`. Director mirrors the dm_response budget gate; it honors `interrupt_before` by writing nothing on the tenant's behalf — the publish checkpoint already exists downstream.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `microservices/renderer/app.py` | Modified | Optional `scenes[]` + per-scene render path |
| `workers/video_edit_task.py` | Modified | Scenes into render_payload |
| `agents/crews/video_director_crew.py` | Modified | LLM director + fallback |
| `agents/crews/{scriptwriting,video_prompt}_crew.py` | Modified | RUM threshold + trend cache context |
| `tests/unit/test_video_director_guardian.py` + crew tests | Modified | Zero-token director tests |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| New call skips budget/interrupt guard (policy bug) | Med | Reuse check_tenant_llm_budget + router; explicit test |
| Renderer deploy drift (separate service) | Med | Additive contract; fallback wins on old renderer |
| Mock s3:// URIs leak into persisted rows | Low | Scenes carry text/prompt only; clip gen out of slice |
| Serial dev latency (+1 LLM call) | Med | One cheap call; offline-safe fallback |

## Rollback Plan

Revert worker + crews only; renderer stays compatible (flat fallback). Or drop `scenes[]` from the payload — old deterministic path intact. No migration.

## Dependencies

- `api-llm-routing`, `pipeline-persistence-writes` (storyboard in state) already in HEAD.

## Success Criteria

- [ ] Renderer honors scenes[]; flat script_text renders unchanged for old payloads
- [ ] Director call budget-guarded; deterministic fallback on exhaustion
- [ ] Zero-token tests green; no real LLM spend in CI
- [ ] `MediaGalleryView.jsx` untouched (git diff clean)