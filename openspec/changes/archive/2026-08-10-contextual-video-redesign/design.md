# Design: Contextual Video Redesign — Scene-Aware Renderer + Budget-Guarded LLM Director

## Technical Approach

Three additive, deploy-safe slices satisfy the 3 specs: (1) optional `scenes[]` on `RenderRequest` with a per-scene render path and an untouched flat `script_text` branch guaranteed byte-identical (REQ-VSR-01..06); (2) `node_video_edit` forwards `video_storyboard` → `trigger_video_render` → `render_payload["scenes"]`; (3) `run_video_director_crew` curates metadata via the shared router `llm.acomplete()` behind the `check_tenant_llm_budget` gate (mirrors `dm_response.py:62-72`), with deterministic template fallback, plus RUM-threshold/trend-cache injection at the exact prompt-build seams of both writer crews. Director is the 5th router call site; zero direct `litellm.completion` remains (verified in HEAD).

## Architecture Decisions

| # | Option | Tradeoff | Decision |
|---|---|---|---|
| D1 | Scenes contract shape | Strict forbid loses forward-compat | `RenderScene{block, text required; tts_voice, visual_prompt, duration_s optional}`; pydantic 2.13 default `extra='ignore'` drops unknown keys; `scenes: []` falsy → flat path (VSR-06) |
| D2 | Flat fallback guarantee | Refactor shared helpers risks behavior drift | Branch `if req.scenes` before the existing pipeline; flat block keeps today's statements verbatim, same call order/progress events (VSR-02) |
| D3 | Per-scene render | Per-scene Pexels adds serial time | Per-scene TTS (scene `tts_voice` else `DEFAULT_VOICE`), per-scene search (`visual_prompt`→derived keywords, else payload keywords, `per_page=2`), concat in order; scene duration = `duration_s` or TTS length; total capped `min(sum, max_duration_seconds or 45.0)`; `max_duration_seconds` added as optional model field only (legacy sends 45 → unchanged) |
| D4 | Sync↔async bridge | `asyncio.run()` raises inside `node_video_edit`'s running loop | Sync `run_video_director_crew` drives async curation via `asyncio.new_event_loop().run_until_complete(coro)` (legal in both Celery-sync and node-async contexts); test seam = monkeypatch `agents.llm.acomplete` (pattern `test_ideation_crew.py:59-67`) |
| D5 | Budget gate scope | REQ-LLM-04 wording could imply gating all 5 sites (scope expansion) | Director-only gate per proposal: Redis read `llm_spend:{tenant_id}` + `check_tenant_llm_budget`; over-budget → early-return template WITHOUT calling `acomplete()` (provable by fake); Redis down → warn + continue (dm_response pattern, CVD-02-3). Other 4 sites pre-date this change, untouched |
| D6 | Fallback/parse | Loose parse leaks bad metadata | Strict JSON parse (`final_title`, `description`, `hashtags`, `keywords`), strip ``` fences, type-checked; any failure → `curate_video_metadata`; `render_payload` gains additive `description`/`hashtags` (old renderer ignores) |
| D7 | Prompt context | New constants would violate RUM rule | New `agents/crews/prompt_context.py`: `resolve_rum_threshold(niche)` wraps `get_dynamic_threshold` (Redis, clamp [0.50,0.90], default 0.70 — no new constant) + `build_trend_section(niche)` reads `rag_cache.get(f"tendencia_{niche}")`, snippet ≤400, `""` on miss (CVD-04-2). Injected into `user_prompt` at `scriptwriting_crew.py:51-64` and `video_prompt_crew.py:49-70` |

## Data Flow

```
node_video_edit ──storyboard──▶ trigger_video_render
    │ storyboard (state)          │ director: budget-gate ─▶ llm.acomplete() ─▶ metadata(title/desc/hashtags/keywords)
    │                             │ scenes[] + title/keywords ─▶ POST /render
    │                             ▼
    └─ video_storyboard ──▶ renderer: validate scenes (4xx) ─▶ per-scene TTS/Pexels ─▶ concat (cap) ─▶ MinIO
                              flat (scenes absent) ─▶ legacy pipeline (byte-identical)
```

## File Changes

| File | Action | Description |
|---|---|---|
| `agency/microservices/renderer/app.py` | Modify | `RenderScene`, `scenes`/`max_duration_seconds` fields; `validate_scenes` + per-scene TTS/b-roll/compose helpers; flat branch untouched |
| `agency/workers/video_edit_task.py` | Modify | Accept `storyboard` param; forward `scenes` into `render_payload` when present (else omit → flat) |
| `agency/agents/nodes/video_edit.py` | Modify | Pass `storyboard` to `trigger_video_render` |
| `agency/agents/crews/video_director_crew.py` | Modify | `curate_video_metadata_llm` (async, budget-gated), sync bridge, strict parse, template fallback |
| `agency/agents/crews/prompt_context.py` | Create | `resolve_rum_threshold` + `build_trend_section` shared helpers |
| `agency/agents/crews/{scriptwriting,video_prompt}_crew.py` | Modify | Inject threshold + trend section at prompt seams |
| `agency/tests/unit/test_video_renderer_microservice.py` | Modify | Scenes validation/serialization + per-scene render (mocked edge_tts/MoviePy/requests) + flat byte-identity |
| `agency/tests/unit/test_video_director_guardian.py` | Modify | fake_acomplete curation, budget-exceeded no-call, all-providers-down fallback, parse |
| `agency/tests/unit/test_prompt_context.py` | Create | Zero-token threshold/trend prompt-build tests |
| `agency/tests/unit/test_video_edit_wiring.py` | Create | Celery eager + mocked renderer client + fake_acomplete → payload carries scenes + curated fields |
| `agency/tests/unit/test_llm_router.py` | Modify | Exactly-5-sites scan; no `litellm.completion` in the 5 files (LLM-04-1) |

## Interfaces / Contracts

```python
class RenderScene(BaseModel):
    block: str
    text: str = Field(min_length=1)           # non-empty required (VSR-06)
    tts_voice: Optional[str] = None
    visual_prompt: Optional[str] = None
    duration_s: Optional[float] = Field(default=None, gt=0)

class RenderRequest(BaseModel):
    title: str; script_text: str
    keywords: List[str] = Field(default_factory=lambda: ["business", "technology", "office"])
    tenant_id: Optional[str] = "default_tenant"
    scenes: Optional[List[RenderScene]] = None   # ignored by old renderer
    max_duration_seconds: Optional[float] = 45.0 # legacy sends 45 → flat unchanged
# render_payload gains optional: description, hashtags (additive)
```

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | Scene validation: missing `block`/`text`, empty text → 4xx; unknown keys ignored; `scenes: []` → flat | Pure pydantic/pytest (VSR-06) |
| Unit | Flat fallback byte-identity: same calls/order for legacy payload | Assert unchanged flat branch output vs pre-change behavior (VSR-02) |
| Unit | Per-scene TTS/b-roll/duration semantics | Mock `edge_tts`, `requests`, `moviepy` (VSR-03/04/05) |
| Unit | Budget decisions: over-budget → template + `acomplete` NOT called; Redis down → continue | fake_acomplete + monkeypatched budget read (CVD-02) |
| Unit | Director prompt build + strict parse; threshold/trend injection | fake captures messages, asserts seam content (CVD-03/04) |
| Integration | Worker wiring: eager Celery, mocked renderer client returns 201, fake_acomplete | Scenes + curated fields reach POST body (VSR-01, LLM-04-2) |
| E2E | None (constraint) | — |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. (Renderer↔worker POST is an existing API boundary; the change only adds JSON fields.)

## Migration / Rollout

No migration. Deploy order safe both ways: **old worker → new renderer**: no `scenes` → flat path; **new worker → old renderer**: pydantic v2 ignores unknown `scenes`/`description`/`hashtags` keys → flat render. Rollback = revert worker + crews; renderer stays compatible. Never touch `frontend/.../MediaGalleryView.jsx` (dirty locally).

## Work-Unit Commit Boundaries

1. `feat(renderer): additive per-scene render contract with flat fallback` — renderer + its tests (independently shippable: separate service).
2. `feat(workers): forward storyboard scenes into render payload` — `video_edit.py` + `video_edit_task.py` + wiring tests.
3. `feat(director): budget-guarded contextual LLM metadata curation` — `video_director_crew.py` + tests.
4. `feat(crews): inject RUM threshold and trend cache into writer prompts` — `prompt_context.py` + both crews + tests.

Forecast: ~450-550 authored lines → **>400 budget risk: High; chained PRs recommended**: PR-A = WU1 (renderer, zero coupling), PR-B = WU2+WU3 (worker+director), PR-C = WU4 (prompts). Chain strategy not set — orchestrator to confirm before apply (≤60-min review slices, dependency diagram per `chained-pr`).

## Open Questions

- [ ] REQ-LLM-04's "any call site … MUST pass the budget guard" vs proposal director-only scope — design assumes director-only (D5); confirm no retrofit of the 4 legacy sites.
- [ ] Existing `test_trigger_video_render_task_fallback` / `test_video_director_guardian` run without fake_acomplete: safe (no CI keys → router raises `AllProvidersFailedError` → template), but should be updated with explicit fakes for determinism.