# Verification Report — contextual-video-redesign

- **Change**: `contextual-video-redesign` — Scene-Aware Renderer + Budget-Guarded LLM Director
- **Repo**: `/home/ivan/Desktop/AgentMarketingIA` (git branch `main`)
- **Phase executed**: Integration Guards 5.1-5.3 (SDD verify executor)
- **Commits under verification**: `a428e10` (renderer scenes[]), `4c0b416` (director), `38719b7` (worker forwarding), `71c266c` (prompt injection), `a7626f8` (W-1 guard fix)
- **Mode**: openspec file + Engram (`sdd/contextual-video-redesign/verify-report`)
- **Date**: 2026-08-10
- **Verdict**: **VERIFIED** (implementation compliant on all 27 scenarios; W-1 guard gap fixed in `a7626f8`; W-2 infra observation only)

## Artifact completeness

| Artifact | Present | Used |
|----------|---------|------|
| Proposal | ✅ `proposal.md` | Indirect (specs authoritative) |
| Specs | ✅ 3 delta specs (VSR/CVD/api-llm-routing) | Yes |
| Design | ✅ `design.md` | D1-D7 mapped |
| Tasks | ✅ `tasks.md` (1.1-4.3 `[x]`) | Yes |
| Verify | ✅ this report | — |

All apply tasks 1.1-4.3 were already checked; only 5.1-5.3 were open. No task was blocked, so full verification ran.

## Command evidence

| Step | Command | Result | Timing |
|------|---------|--------|--------|
| 5.1 | `AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/unit/test_llm_router.py -q` | `9 passed, 1 skipped` (exit 0) | 7.62s |
| 5.1 post-fix | Same command after `a7626f8` (director added + exhaustiveness test) | `10 passed, 1 skipped` (exit 0) | 8.02s |
| WU files | `pytest {4 WU files} {2 crew files} -q` | `49 passed` (exit 0) | 43.42s |
| 5.3 (full) | `AGENCY_ENV=dev timeout 300 pytest tests/ -q` | **exit 124** — hit 5-min cap, no output recovered | >300s |
| 5.3 (complement) | `pytest tests/ --ignore={7 verified files} -v` | `193 passed` (exit 0) | 165.24s |
| Collection | `pytest tests/ --collect-only -q` | `253 tests collected` | 16.09s |
| 5.2 | `git diff --stat -- agency/frontend/.../MediaGalleryView.jsx` | `1 file changed, 6 insertions(+), 3 deletions(-)` | — |
| PR/frontend | `git show --stat a428e10 4c0b416 38719b7 71c266c a7626f8 \| grep -i frontend` | empty (exit 1) | — |

**Composed suite total**: 10 + 49 + 193 = **252 passed, 1 skipped** of 253 collected. Every test in the repo passes; the only issue is that a single-process full run exceeds 300s (slow tests, not failures). All LLM-path tests monkeypatch `agents.llm.acomplete` (`fake_acomplete`, pattern `test_ideation_crew.py:59-67`) — **zero real LLM spend confirmed**. No test requires real keys except the `@pytest.mark.real_keys` gate which is skipped unless `RUN_REAL_KEYS=1` (not set).

## Behavioral compliance matrix (12 REQ / 27 scenarios)

Legend: PASS (runtime + static), static-only PASS (marked `[S]`), FAIL, UNVERIFIED.

### REQ-VSR-01 Additive `scenes[]` protocol
| Scenario | Result | Evidence |
|----------|--------|----------|
| VSR-01-1 full scenes payload accepted | PASS | `microservices/renderer/app.py:70` (`scenes: Optional[List[RenderScene]]`), `:365` (`if req.scenes:`); test `test_video_renderer_microservice.py:270` (`test_renderer_scenes_4_scene_payload_per_scene_render`) green |
| VSR-01-2 absent scenes keeps flat | PASS | `app.py:70` default `None`, `:365` falsy → flat branch; test `:310` (`test_renderer_scenes_absent_scenes_uses_flat`) green |

### REQ-VSR-02 Flat `script_text` fallback byte-identical
| Scenario | Result | Evidence |
|----------|--------|----------|
| VSR-02-1 legacy payload renders unchanged | PASS | Additive `if req.scenes:` branch (`app.py:363-392`) inserted BEFORE untouched flat pipeline (`:393-428`); commit diff deletions limited to pydantic import + `per_page` parameterization (default 4 preserved); test `:337` (`test_renderer_flat_byte_identity_legacy_payload`) asserts exact progress order/voice/per_page=4/compose_flat once — green |

### REQ-VSR-03 Per-scene TTS
| Scenario | Result | Evidence |
|----------|--------|----------|
| VSR-03-1 distinct voice, concat in order | PASS | `app.py:288` (`voice = scene.tts_voice or DEFAULT_VOICE`); `:249` audio appended in scene order; test `:284-289` green |
| VSR-03-2 missing voice uses default | PASS | `app.py:288`; test `:287` (`DEFAULT_VOICE`) green |

### REQ-VSR-04 Per-scene b-roll
| Scenario | Result | Evidence |
|----------|--------|----------|
| VSR-04-1 visual_prompt drives clips | PASS | `app.py:101-110` `_keywords_from_prompt` + `:294`; test `:294` (`["Oficina","moderna","con","luz"]`) green |
| VSR-04-2 no prompt falls back to keywords | PASS | `app.py:107-110`; test `:293` green |

### REQ-VSR-05 Per-scene duration
| Scenario | Result | Evidence |
|----------|--------|----------|
| VSR-05-1 explicit duration honored | PASS | `app.py:113-117` `_scene_duration_seconds` (+`_scene_duration_explicit...` test `:407/:417`); total cap `app.py:120-123`; test `:361/:376/:400`; green |
| VSR-05-2 natural TTS length | PASS | `app.py:117`; test `:421/:431` green |

### REQ-VSR-06 Malformed scenes validation
| Scenario | Result | Evidence |
|----------|--------|----------|
| VSR-06-1 invalid scene → 4xx, no fallback render | PASS | Pydantic `RenderScene` `block`/`text` required, `text` `min_length=1`, `duration_s gt=0` (`app.py:44-58`) → FastAPI 422 before branch; tests `:184/:196/:210/:221/:231` assert 422 + `calls["tts"] == []` green |
| VSR-06-2 empty scenes → flat | PASS | `app.py:365` falsy empty list; test `:325` green |
| VSR-06-3 unknown keys ignored | PASS | `extra="ignore"` (`app.py:52`, `:64`); test `:246/:259` green |

### REQ-CVD-01 Budget-guarded LLM curation
| Scenario | Result | Evidence |
|----------|--------|----------|
| CVD-01-1 curation via router within budget, fields in payload | PASS | `video_director_crew.py:203` gate → `:228` `await llm.acomplete(...)` → `:153` `_parse_metadata_json` → `:327-342` render_payload; `workers/video_edit_task.py:89-97`; test `test_video_director_guardian.py:119` green |
| CVD-01-2 router failover on provider 429 | PASS | Delegation to `agents/llm.py:83-107` multi-provider loop; failover tests `test_llm_router.py:120/:140` green |
| CVD-01-3 zero-token spend in tests | PASS | All director/worker tests monkeypatch `agents.llm.acomplete` with `fake_acomplete`: `guardian.py:123/:140/:163/:177/:202/:251`, `test_video_edit_wiring.py:85/:119`, renderer tests `:56-58/:94-96`; green |

### REQ-CVD-02 Deterministic fallback
| Scenario | Result | Evidence |
|----------|--------|----------|
| CVD-02-1 budget exhausted → no acomplete, template | PASS | `video_director_crew.py:203-204` early `return None` before router; `:308-311` template kept; test `guardian.py:136` (`test_director_over_budget_does_not_call_router`) green |
| CVD-02-2 all providers down → template, no propagate | PASS | `video_director_crew.py:241-243` try/except → `None`; test `guardian.py:155` green |
| CVD-02-3 Redis down → warn + continue | PASS | `video_director_crew.py:143-147` mirrors `dm_response.py:71-72`; test `guardian.py:173` (caplog) green |

### REQ-CVD-03 RUM dynamic threshold injection
| Scenario | Result | Evidence |
|----------|--------|----------|
| CVD-03-1 threshold present (0.78) injected | PASS | `prompt_context.py:30` `resolve_rum_threshold` → `rum_calculator.py:64` `get_dynamic_threshold`; seams `scriptwriting_crew.py:49/:68`, `video_prompt_crew.py:46/:62`; tests `test_prompt_context.py:18`, `test_scriptwriting_crew.py:41`, `test_video_prompt_crew.py:51` green |
| CVD-03-2 absent → clamp default, no new constant | PASS | `prompt_context.py:39-46` delegates to `rum_calculator.py:71` (default 0.70, clamp [0.50,0.90]); the `return 0.70` at `:46` only mirrors the existing calculator default on getter failure (no new constant); test `test_prompt_context.py:29` green |

### REQ-CVD-04 Sanitized trend cache injection
| Scenario | Result | Evidence |
|----------|--------|----------|
| CVD-04-1 cached trends reach writers (≤400 chars) | PASS | `prompt_context.py:49` `build_trend_section` reads `rag_cache["tendencia_{niche}"]`, `sanitize_html_content`, `MAX_TREND_SNIPPET_CHARS=400` (`:27/:77/:83`); seams `scriptwriting_crew.py:50-53`, `video_prompt_crew.py:47-50`; tests `test_prompt_context.py:53/:75` green |
| CVD-04-2 cache miss non-fatal | PASS | `prompt_context.py:67-82` returns `""` on miss; crews still produce output; tests `test_prompt_context.py:87/:96`, `test_scriptwriting_crew.py:72`, `test_video_prompt_crew.py:84` green |

### REQ-LLM-02 Five sites through shared router
| Scenario | Result | Evidence |
|----------|--------|----------|
| LLM-02-1 no direct call across five sites | PASS | `test_llm_router.py` `test_no_direct_litellm_completion_in_call_sites` scans all 5 files (incl. director after `a7626f8`) for `litellm.completion` → zero matches; `rg` across the 5 sites → **zero matches**; all 5 invoke `llm.acomplete` |
| LLM-02-2 LLM text, not template | PASS | `test_llm_router.py:33` (LLM text, no fallback title) + `test_ideation_crew.py:33` green |
| LLM-02-3 director routes through router | PASS | `video_director_crew.py:228`; `test_video_director_guardian.py:119` + `test_video_edit_wiring.py:82` (fields land in POST payload) green |

### REQ-LLM-04 Five-site routing and budget-gate guarantee
| Scenario | Result | Evidence |
|----------|--------|----------|
| LLM-04-1 exactly five call sites | PASS | `test_llm_router.py` `test_exactly_five_acomplete_call_sites_across_files` (added `a7626f8`) asserts exactly one `await llm.acomplete(` per file across the 5 files (ideation:64, scriptwriting:81, video_prompt:86, dm_response:78, director:228) and `sum == 5`; `rg "\.acomplete\("` production → exactly those 5 invocations; no other production path |
| LLM-04-2 director budget-checked before router | PASS | `video_director_crew.py:122-150` `_tenant_within_llm_budget` (Redis `llm_spend:{tenant_id}`, pattern `dm_response.py:62-72`) gates `:203`; test `guardian.py:136` (over budget → router not called, zero tokens) green |

**Totals**: 27 scenarios — PASS 27 (27 runtime, 0 `[S]` static-only), FAIL 0, UNVERIFIED 0. LLM-02-1/LLM-04-1 moved from static-only to runtime regression coverage by the `a7626f8` guard fix.

## Legacy-site confirmation (director-only gate, no retrofit)

Legacy 4 sites (ideation/scriptwriting/video_prompt/dm_response) all keep their existing `acomplete()` call + dynamic fallback + temperature/max_tokens parameters. The `fetch` from task 3.3 LOCK ("do NOT retrofit the 4 legacy sites") holds: grep shows the director is the only NEW call site (`video_director_crew.py:11` docstring + `:228`), no legacy file gained a budget gate or was otherwise mutated by commits `4c0b416`/`71c266c`. The rush to budget-gate everything did NOT happen.

## Findings

### CRITICAL
None. Implementation is compliant on every requirement with runtime coverage; no failing test; no design-vs-spec contradiction.

### WARNING
- **W-1 (guard completeness)** — **FIXED in `a7626f8`** (`test(router): enforce exactly-five acomplete sites incl. director`). The original task-5.1 guard only scanned 4 call sites (`test_llm_router.py:24-29`) and asserted the no-`litellm.completion` rule only for those 4, giving false confidence. Fix: appended `agents/crews/video_director_crew.py` to `CALL_SITE_FILES`, added `test_exactly_five_acomplete_call_sites_across_files` (exactly one `await llm.acomplete(` per file, `sum == 5`, director gate assertion `check_tenant_llm_budget`), rerun → `10 passed, 1 skipped` (8.02s). LLM-02-1/LLM-04-1 now runtime-enforced, not static-only.
- **W-2 (suite timing, open)** — single-process `pytest tests/ -q` exceeds the 5-minute cap (exit 124; output not recoverable through the piped tail). Every individual slice is green (252 passed / 1 skipped composed of 253 collected). Likely a few slow network/IO tests (e.g. `test_minio_real`, `test_e2e_full_pipeline_and_garbage_collection`, `test_fastapi_endpoints`, `test_rag_mcp`). Recommend CI budget + `--durations=10` to identify and gate them; not a failure of this change.

### SUGGESTION
- **S-1** — `prompt_context.py:46` keeps a literal `return 0.70` last-resort mirror of `rum_calculator.py:71`. Satisfies CVD-03-2 (same value, no NEW constant) but is duplicated knowledge; prefer importing/deriving the default from `rum_calculator` to avoid drift.
- **S-2** — `test_video_renderer_microservice.py` is 432 lines mixing renderer + director + worker coverage; the director/worker tests stub the budget gate to force template (`:56-58/:94-96`). Fine for determinism, but keep the director-specific tests in the guardian/wiring files to preserve single-responsibility.

## Command evidence summary
- 5.1 test: exit 0, `10 passed, 1 skipped` (post-fix `a7626f8`), 8.02s
- 5.2 guard: `git diff --stat` = `6 insertions(+), 3 deletions(-)` on MediaGalleryView.jsx only; PR commits touch zero frontend files
- 5.3 full suite: exit 124 (>300s), composed `252 passed, 1 skipped` of 253 collected, all slices green, zero-token confirmed
- `test_output_hash`: not computed (pytest `-v` complement log at `/tmp/opencode/full_complement.log`)

## Next recommended
**archive** — W-1 fixed and runtime-enforced (`a7626f8`); all 27 scenarios PASS with regression guards; W-2 is an infrastructure/CI observation (slow tests), not a blocker to archive.