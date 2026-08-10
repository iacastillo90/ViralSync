# Tasks: Contextual Video Redesign — Scene-Aware Renderer + Budget-Guarded LLM Director

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines (total) | ~950-1250 authored |
| PR-A (renderer scenes contract) | ~280-400 |
| PR-B (worker forwarding + director) | ~420-540 |
| PR-C (prompt context injection) | ~250-320 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR-A → PR-B → PR-C |
| Delivery strategy | auto-forecast (chain strategy pending user) |
| Chain strategy | stacked-to-main (advisory) |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| WU1 | Renderer additive `scenes[]` contract + per-scene render | PR-A | `pytest agency/tests/unit/test_video_renderer_microservice.py -q` | N/A — no E2E allowed (design constraint); edge_tts/MoviePy/requests mocked | Revert `agency/microservices/renderer/app.py` + its test; worker untouched, flat path intact |
| WU2 | Worker forwards storyboard scenes into render_payload | PR-B | `pytest agency/tests/unit/test_video_edit_wiring.py -q` | Celery eager: run `trigger_video_render` with mocked renderer client; assert POST body | Revert `agency/agents/nodes/video_edit.py`, `agency/workers/video_edit_task.py` + wiring test; payloads flat again |
| WU3 | Budget-guarded LLM director (shared router, strict parse, fallback) | PR-B | `pytest agency/tests/unit/test_video_director_guardian.py -q` | N/A — pytest only; monkeypatched `agents.llm.acomplete`, zero-token | Revert `agency/agents/crews/video_director_crew.py` + guardian tests; deterministic director restored |
| WU4 | Prompt context injection (RUM threshold + trend cache) | PR-C | `pytest agency/tests/unit/test_prompt_context.py -q` | N/A — pure prompt-build tests, zero-token | Revert `agency/agents/crews/prompt_context.py` + both crews + tests; prompts unchanged |

## Phase 1: PR-A — Renderer Scenes Contract (TDD)

- [x] 1.1 [RED] `agency/tests/unit/test_video_renderer_microservice.py`: 4-scene payload accepted → per-scene render (VSR-01-1); absent `scenes` accepted → flat (VSR-01-2); `scenes: []` → flat (VSR-06-2); unknown keys ignored (VSR-06-3). Ev: fail pre-change (no scenes field). Cmd: `pytest agency/tests/unit/test_video_renderer_microservice.py -q`. Rollback: test-only.
- [x] 1.2 [RED] Validation: scene missing `block`/`text` or empty text → 4xx naming invalid scene, no fallback render (VSR-06-1); `duration_s <= 0` rejected. Ev: failing tests. Same cmd. Rollback: test-only.
- [x] 1.3 [RED] Flat byte-identity: legacy payload (`title`/`script_text`/`keywords`/`tenant_id`) → identical calls/order/output vs pre-change (VSR-02-1). Ev: failing until `if req.scenes` branch proves flat path untouched. Same cmd. Rollback: test-only.
- [x] 1.4 [GREEN] `agency/microservices/renderer/app.py`: `RenderScene` (block/text required; tts_voice/visual_prompt/duration_s optional) + `scenes`/`max_duration_seconds` on `RenderRequest`, pydantic `extra='ignore'` (D1); `validate_scenes`; `if req.scenes` branch before unchanged flat pipeline (D2). Ev: 1.1-1.3 green. Same cmd. Rollback: PR-A boundary.
- [x] 1.5 [GREEN] Per-scene render: TTS per scene (`tts_voice` else `DEFAULT_VOICE`; VSR-03-1/03-2), b-roll per scene (`visual_prompt`-derived keywords else payload keywords, `per_page=2`; VSR-04-1/04-2), duration `duration_s` else TTS length, total capped `min(sum, max_duration_seconds or 45.0)`, concat in order (VSR-05-1/05-2; D3). Ev: 1.1 green incl. per-scene assertions. Same cmd. Rollback: PR-A boundary (app.py + test revert).

## Phase 2: PR-B — Worker Scenes Forwarding (WU2)

- [x] 2.1 [GREEN] `agency/agents/nodes/video_edit.py` + `agency/workers/video_edit_task.py`: accept `storyboard` param; when present map to `scenes` (block/text/tts_voice/visual_prompt/duration_s) in `render_payload` + additive `description`/`hashtags`; omit `scenes` when absent → flat (VSR-01 worker side). Ev: wiring test green.
- [x] 2.2 [RED→GREEN] `agency/tests/unit/test_video_edit_wiring.py` (new): Celery eager + mocked renderer client 201 + `fake_acomplete` → POST body carries scenes + curated fields (VSR-01, LLM-04-2 payload reach). Ev: zero-token, mocked HTTP. Cmd: `pytest agency/tests/unit/test_video_edit_wiring.py -q`. Rollback: WU2 boundary (revert node+task+wiring test).

## Phase 3: PR-B — Budget-Guarded LLM Director (WU3)

- [x] 3.1 [RED] `agency/tests/unit/test_video_director_guardian.py`: `fake_acomplete` (monkeypatch `agents.llm.acomplete`, pattern `test_ideation_crew.py:59-67`): within budget → router called, 4 fields parsed from strict JSON (CVD-01-1, LLM-02-3); over budget → `acomplete` NOT called, template output (CVD-02-1, LLM-04-2); all providers down → template, no exception propagates (CVD-02-2); Redis down → warn + continue (CVD-02-3). Ev: fail pre-change (no LLM path). Cmd: `pytest agency/tests/unit/test_video_director_guardian.py -q`. Rollback: test-only.
- [x] 3.2 [RED] D4 sync↔async bridge dedicated test: sync `run_video_director_crew` drives async curation via `asyncio.new_event_loop().run_until_complete` without clashing with a running loop (Celery-sync and node-async contexts). Ev: dedicated test proves bridge, zero-token (CVD-01-3). Same cmd. Rollback: test-only.
- [x] 3.3 [GREEN] `agency/agents/crews/video_director_crew.py`: `curate_video_metadata_llm` (async), budget gate `check_tenant_llm_budget` on `llm_spend:{tenant_id}` (mirrors `dm_response.py:62-72`; D5), strict parse (strip ``` fences, type-checked; failure → `curate_video_metadata`; D6), sync bridge (D4), template fallback. Ev: 3.1-3.2 green, zero-token. Same cmd. Rollback: WU3 boundary (crew + guardian tests). LOCK: director-only gate — do NOT retrofit the 4 legacy sites.

## Phase 4: PR-C — Prompt Context Injection (WU4)

- [x] 4.1 [RED] `agency/tests/unit/test_prompt_context.py` (new): `resolve_rum_threshold(niche)` — Redis 0.78 injected (CVD-03-1), miss → clamp default, no hardcoded constant (CVD-03-2); `build_trend_section(niche)` — `rag_cache["tendencia_{niche}"]` sanitized snippet ≤400 chars (CVD-04-1), miss → omitted, crew still outputs (CVD-04-2). Ev: zero-token, fail pre-change. Cmd: `pytest agency/tests/unit/test_prompt_context.py -q`. Rollback: test-only.
- [x] 4.2 [GREEN] `agency/agents/crews/prompt_context.py` (new): wrap `get_dynamic_threshold` (clamp [0.50,0.90], default 0.70) + sanitization wrapper over trend cache (D7). Ev: 4.1 green. Same cmd. Rollback: WU4 boundary.
- [x] 4.3 [GREEN] `agency/agents/crews/scriptwriting_crew.py` (seam :51-64) + `agency/agents/crews/video_prompt_crew.py` (seam :49-70): inject threshold + trend section into `user_prompt` (CVD-03/04). Ev: crew prompt-build tests assert seam content, zero-token. Cmd: `pytest agency/tests/unit/test_scriptwriting_crew.py agency/tests/unit/test_video_prompt_crew.py -q`. Rollback: WU4 boundary.

## Phase 5: Integration Guards

- [x] 5.1 [GREEN] `agency/tests/unit/test_llm_router.py`: exactly-5-sites scan — `acomplete()` invoked only from ideation/scriptwriting/video_prompt/dm_response/director; no `litellm.completion` in the 5 files (LLM-04-1). Ev: green (`10 passed, 1 skipped`, 8.02s). Cmd: `pytest agency/tests/unit/test_llm_router.py -q`. Rollback: test-only. **W-1 fixed in `a7626f8`**: `CALL_SITE_FILES` now includes `video_director_crew.py`; `test_exactly_five_acomplete_call_sites_across_files` asserts one `await llm.acomplete(` per file, `sum == 5`, and the director budget-gate guard.
- [x] 5.2 Guard: `git diff` of `agency/frontend/src/features/Media/views/MediaGalleryView.jsx` identical before/after apply (pre-existing local dirt; never staged/reverted). Cmd: `git diff --stat -- agency/frontend/src/features/Media/views/MediaGalleryView.jsx`. Ev: `6 insertions(+), 3 deletions(-)` only; PR commits touch zero frontend files.
- [x] 5.3 Full suite: `pytest -q` (CI parity `--cov=backend --cov-fail-under=50`); all 4 work-unit test files green, no real LLM spend (zero-token). Ev: WU+crew files `49 passed` (43.42s); complement `193 passed` (165.24s); `test_llm_router` `9 passed, 1 skipped`; composed `251 passed / 1 skipped` of 252 collected. Single-process full run exceeds 5-min cap (exit 124) — see W-2.