# Archive Report: contextual-video-redesign

- **Change**: contextual-video-redesign — Scene-Aware Renderer + Budget-Guarded LLM Director
- **Archived at**: 2026-08-10
- **Status**: archived
- **Mode**: openspec filesystem + Engram (archive-report mirrored to `sdd/contextual-video-redesign/archive-report`)
- **Implementation commits**: `a428e10` (renderer scenes[]), `4c0b416` (director), `38719b7` (worker forwarding), `71c266c` (prompt injection), `a7626f8` (W-1 guard fix)
- **Delivery**: auto-forecast, chained stacked-to-main; review_budget_lines 400; size:exception APPROVED. PR chain NOT pushed — user opens PRs per slice (PR-A renderer → PR-B worker+director → PR-C prompts).

## Executive Summary

The pipeline previously spent LLM budget generating a 4-scene cinematic storyboard the renderer never consumed, and the "Video Director" was deterministic template-craft with zero LLM or niche context. This change closed both gaps with additive, deploy-safe slices:

- **Additive `scenes[]` render contract** (`video-scene-render-contract`): `RenderRequest` accepts optional `scenes[]` (block/text required; tts_voice/visual_prompt/duration_s optional); the renderer renders per scene (per-scene TTS, b-roll, duration, total cap) while the flat `script_text` path stays byte-identical for legacy payloads — old worker → new renderer and new worker → old renderer both safe. `video_edit_task.py` now forwards the existing `video_storyboard` into `render_payload["scenes"]`, so the storyboard's scene work is finally consumed instead of discarded.
- **Budget-guarded contextual LLM director** (`contextual-video-director`): `run_video_director_crew` curates title/description/hashtags/keywords via the shared router `llm.acomplete()` gated by `check_tenant_llm_budget` (Redis `llm_spend:{tenant_id}`, dm_response pattern) with deterministic template fallback on over-budget / all-providers-down / Redis-down; strict JSON parse with `curate_video_metadata` fallback. Director-only gate — the 4 legacy sites were NOT retrofitted (LOCK held).
- **RUM/trend context injection**: `resolve_rum_threshold(niche)` (Redis dynamic threshold, clamp [0.50,0.90], no new hardcoded constant) and `build_trend_section(niche)` (sanitized `rag_cache["tendencia_{niche}"]` ≤400 chars, `""` on miss) injected at the scriptwriting/video_prompt prompt seams.
- **Quality**: all tests zero-token (monkeypatched `agents.llm.acomplete`, no real LLM spend); **253-test suite green** (252 passed / 1 skipped composed) with the 5-site router guard runtime-enforced. `MediaGalleryView.jsx` untouched (pre-existing local dirt only, never staged).

## Task Completion Gate

- [x] All implementation tasks checked in `tasks.md` (1.1–5.3, 13/13 `[x]`) — no stale unchecked tasks. `tasks.md` is retained as-is as the historical record of the change (repo convention: archived tasks.md is not rewritten with an "archived" header; see prior archives).
- [x] No open CRITICAL findings: verify verdict **VERIFIED**, 27/27 scenarios PASS (27 runtime, 0 static-only, 0 FAIL, 0 UNVERIFIED). W-1 (guard completeness) FIXED in `a7626f8`; W-2 is an infrastructure observation, not a change defect.
- [x] Review receipt gate: this change ran under auto-forecast stacked-to-main with no opened PRs and therefore no native review transaction/ledger artifacts (`reviews/`) — consistent with the un-pushed PR chain. Orchestrator launch context (implementation + verification COMPLETE, VERIFIED verdict) is the recorded gate for this archive.
- [x] All required artifacts present and archived (proposal, exploration, 3 delta specs, design, tasks, verify-report).

## Specs Synced (delta → base)

| Domain | Action | Details |
|--------|--------|---------|
| video-scene-render-contract | Created | `openspec/specs/video-scene-render-contract/spec.md` — REQ-VSR-01..06, scenarios VSR-01-1..VSR-06-3 (6 reqs, 11 scenarios). New canonical spec (new domain). |
| contextual-video-director | Created | `openspec/specs/contextual-video-director/spec.md` — REQ-CVD-01..04, scenarios CVD-01-1..CVD-04-2 (4 reqs, 10 scenarios). New canonical spec (new domain). |
| api-llm-routing | Updated | `openspec/specs/api-llm-routing/spec.md` — **MODIFIED** REQ-LLM-02 (four → five call sites, director added; scenarios LLM-02-1/2/3 rewritten; delta's "(Previously…)" diff note dropped from the merged requirement) + **ADDED** REQ-LLM-04 (five-site + budget-gate guarantee, scenarios LLM-04-1/04-2). REQ-LLM-01 and REQ-LLM-03 preserved untouched. Purpose second paragraph updated to mention the fifth call site (consistency edit matching the merged requirement, per prior archive convention). |

## Verification Evidence (linkage)

- **Verify report**: `verify-report.md` (archived below) + Engram obs **#237** (`obs-5ddeb36cd6b1017a`). Verdict **VERIFIED** — all 27 scenarios PASS.
- Runtime evidence: 5.1 post-fix `test_llm_router.py` → `10 passed, 1 skipped` (8.02s); WU+crew files → `49 passed`; complement → `193 passed`; composed **252 passed, 1 skipped of 253 collected**. Single-process `pytest tests/ -q` exceeds the 5-min cap (exit 124) — W-2, infra only.
- Guards: `git diff --stat` on MediaGalleryView.jsx = `6 insertions(+), 3 deletions(-)` (pre-existing) and zero frontend files touched by commits `a428e10 4c0b416 38719b7 71c266c a7626f8`.
- Zero LLM spend: every LLM-path test monkeypatches `agents.llm.acomplete` (`fake_acomplete`); only skip = `@pytest.mark.real_keys` gate (not set).

## Engram Traceability

| Artifact | Obs | Sync |
|----------|-----|------|
| explore | #227 (`obs-5da4cca6c61020f3`) | — |
| proposal | #229 (`obs-bbcb2be2158de05f`) | — |
| spec (3 domains) | #230 (`obs-c92dc3a38fc76302`) | — |
| design | #231 (`obs-a460eb496492ccae`) | — |
| tasks | #233 (`obs-7d68bb035a005a00`) | — |
| apply-progress | #234 (`obs-ff368688ebc7a68f`) | merged into this report |
| verify-report | #237 (`obs-5ddeb36cd6b1017a`) | merged into this report |
| renderer test harness (discovery) | #235 (`obs-f8debfc397a805df`) | — |
| **archive-report** | saved this phase | 3 delta specs merged into `openspec/specs/`; folder → `openspec/changes/archive/2026-08-10-contextual-video-redesign/` |

## Archive Contents

- `archive-report.md` (this file) ✅
- `exploration.md` ✅
- `proposal.md` ✅
- `specs/video-scene-render-contract/spec.md` ✅
- `specs/contextual-video-director/spec.md` ✅
- `specs/api-llm-routing/spec.md` ✅ (delta)
- `design.md` ✅
- `tasks.md` ✅ (13/13 tasks complete, historical record)
- `verify-report.md` ✅

## Commit / Uncommitted Consistency Notes

- Archive operations made **zero commits**: synced specs + archived change folder left uncommitted, consistent with the change folder being untracked since propose (openspec artifacts were never committed by prior phases). The delta-spec sync is pure file placement — no commit required. All archive artifacts and the three synced main specs are ready to be committed together with the user's PR slices (suggest `docs(openspec): archive contextual-video-redesign with consolidated delta specs`, mirroring `23f1195`).
- No production code touched; `agency/frontend/.../MediaGalleryView.jsx` pre-existing dirt untouched.

## Forward-Looking Notes

- **W-2 (open, infra)**: single-process `pytest tests/ -q` exceeds 5 min (exit 124); all slices green. Recommend CI budget + `--durations=10` to identify and gate slow network/IO tests (`test_minio_real`, `test_e2e_full_pipeline_and_garbage_collection`, `test_fastapi_endpoints`, `test_rag_mcp`).
- **S-1**: `prompt_context.py:46` keeps a literal `return 0.70` last-resort mirror of `rum_calculator.py:71` — fine for CVD-03-2 (no new constant) but prefer deriving the default from `rum_calculator` to avoid drift.
- **S-2**: `test_video_renderer_microservice.py` (432 lines) mixes renderer/director/worker coverage; keep director-specific tests in the guardian/wiring files for single-responsibility.
- **PR chain not pushed**: user can open PRs per slice (PR-A `a428e10`, PR-B `38719b7`+`4c0b416`, PR-C `71c266c`, + W-1 fix `a7626f8`), stacking to `main`; the archived openspec docs can ride along as a final `docs(openspec)` commit.

## Next Recommended

**none** — change closed. No unarchived work remains on this change; the next change may target W-2 (CI timing budget) and S-1/S-2 (prompt-context default derivation; test-file single-responsibility) as follow-ups if desired.

## Reconciliation Notes

- No stale-checkbox reconciliation needed (`tasks.md` 13/13 `[x]`).
- No destructive merge: only MODIFIED (REQ-LLM-02 full replacement, difference-annotations stripped) and ADDED (REQ-LLM-04) applied to the existing `api-llm-routing` spec; all requirements not mentioned in the delta preserved.
- No CRITICAL verification findings; no intentional partial archive; no deviations from the archive contract.