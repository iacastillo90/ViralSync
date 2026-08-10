# contextual-video-director Specification

## Purpose

Replace the deterministic "Video Director" metadata guardian (`agents/crews/video_director_crew.py:111` — template titles, heuristic RUM gate, keyword extraction) with a budget-guarded contextual LLM director. The director curates `title`/`description`/`hashtags`/`keywords` via the shared router (`agents/llm.py:113` `acomplete()`), gated by `check_tenant_llm_budget` (pattern `agents/nodes/dm_response.py:62-69`), and injects the RUM dynamic threshold (Redis `rum_threshold:{niche}`) + sanitized trend cache (`rag_cache["tendencia_{niche}"]`) into prompts. It never writes on the tenant's behalf — the publish checkpoint downstream remains the write gate.

## Requirements

### Requirement: REQ-CVD-01 — Budget-guarded LLM metadata curation

The director MUST, when the tenant budget allows, call the shared router `acomplete()` (`agents/llm.py:113`) to curate `title`/`description`/`hashtags`/`keywords` for the render payload. The response MUST be plain text parsed into those four fields. The call MUST be gated by `check_tenant_llm_budget` reading accumulated spend from Redis (`llm_spend:{tenant_id}`), mirroring `dm_response.py:62-69`.

#### Scenario: CVD-01-1 — curation via shared router within budget

- GIVEN tenant spend below the monthly LLM limit
- WHEN the director runs for a validated script
- THEN it calls `acomplete()` and parses curated title/description/hashtags/keywords
- AND the fields land in `render_payload`

#### Scenario: CVD-01-2 — router failover on provider 429

- GIVEN the first provider rate-limits
- WHEN the director requests curation
- THEN the shared router tries subsequent providers and returns the first success
- AND the curated fields come from LLM output, not the template

#### Scenario: CVD-01-3 — zero-token spend in tests

- GIVEN the director unit test
- WHEN it runs with a `fake_acomplete` seam
- THEN the router is invoked async-only and no real provider spends tokens

### Requirement: REQ-CVD-02 — Deterministic fallback when budget exhausted or router unavailable

The director MUST NOT spend when the tenant is over budget: it MUST short-circuit to the existing deterministic curation (template `curate_video_metadata`, `video_director_crew.py:66`). It MUST also fall back to that path when the router fails entirely (all providers down), preserving today's offline-safe behavior.

#### Scenario: CVD-02-1 — budget exhausted falls back

- GIVEN accumulated tenant spend above the monthly LLM limit
- WHEN the director runs
- THEN it does NOT call `acomplete()`
- AND it returns template-based title/description/hashtags/keywords

#### Scenario: CVD-02-2 — all providers down falls back

- GIVEN every router provider fails or rate-limits
- WHEN the director runs
- THEN it returns the deterministic template curation
- AND no exception propagates to `video_edit_task.py`

#### Scenario: CVD-02-3 — Redis unavailable behaves like dm_response

- GIVEN Redis cannot be reached for the budget check
- WHEN the director runs
- THEN it logs a warning and continues (guard skipped), matching `dm_response.py:71-72`

### Requirement: REQ-CVD-03 — RUM dynamic threshold injection into prompts

The system MUST inject the niche's RUM dynamic threshold (Redis `rum_threshold:{niche}`, clamped [0.50, 0.90] — `agents/criterion/rum_calculator.py:64`) into the scriptwriting and video_prompt LLM prompts as an explicit quality target. The threshold MUST come from Redis, never a hardcoded global.

#### Scenario: CVD-03-1 — threshold present is injected

- GIVEN `rum_threshold:{niche}` holds 0.78 in Redis
- WHEN scriptwriting/video_prompt prompts are built
- THEN the prompt states 0.78 as the target RUM threshold

#### Scenario: CVD-03-2 — threshold absent uses computed clamp

- GIVEN no Redis entry for the niche
- WHEN the threshold is resolved
- THEN the existing clamp default is used and no hardcoded constant is introduced

### Requirement: REQ-CVD-04 — Sanitized trend cache injection into prompts

The system MUST read the daily-scraped trend cache `rag_cache["tendencia_{niche}"]` (written by `trend_scraper_task.py`) and inject sanitized trend snippets (≤400 chars via the sanitization wrapper) into scriptwriting/video_prompt prompts. Cache miss MUST NOT fail the crew.

#### Scenario: CVD-04-1 — cached trends reach the writers

- GIVEN `rag_cache["tendencia_b2b"]` holds sanitized trend documents
- WHEN scriptwriting/video_prompt prompts are built for niche `b2b`
- THEN the prompt includes the sanitized trend snippets

#### Scenario: CVD-04-2 — cache miss is non-fatal

- GIVEN no cache entry for the niche
- WHEN the prompt is built
- THEN the trend section is omitted
- AND the crew still produces its output