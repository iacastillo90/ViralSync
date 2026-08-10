# Delta for api-llm-routing

## MODIFIED Requirements

### Requirement: REQ-LLM-02 — Replace the direct call sites through the shared router

**User Story**: As a developer, I want the five LLM call sites (ideation, scriptwriting, video prompting, DM response, and the video director's metadata curation) to call the shared router, so routing policy lives in one place and template fallback only fires when every provider fails.

**Motivo**: Centralizes config and removes per-site `litellm.completion` divergence (temperature/max_tokens per site stay as parameters). The video director gains an LLM curation call in `contextual-video-redesign`, so it becomes the fifth call site and MUST use the router instead of introducing a direct call.

The system MUST route ideation, scriptwriting, video prompting, DM-response generation, and video-director metadata curation through REQ-LLM-01. Direct `litellm.completion` imports in `ideation_crew.py`, `scriptwriting_crew.py`, `video_prompt_crew.py`, `dm_response.py`, and `video_director_crew.py` MUST NOT exist; every one of these sites MUST call the shared router's `acomplete()`.

(Previously: the requirement enumerated four call sites — ideation, scriptwriting, video prompting, DM response — and prohibited direct `litellm.completion` in those four files.)

#### Scenario: LLM-02-1 — no direct call remains across five sites

- GIVEN the shipped change
- WHEN `ideation_crew.py`, `scriptwriting_crew.py`, `video_prompt_crew.py`, `dm_response.py`, `video_director_crew.py` are scanned
- THEN each imports and calls the shared router (`acomplete()`)
- AND no `litellm.completion` direct call remains in any of them

#### Scenario: LLM-02-2 — LLM text, not template, when a provider responds

- GIVEN a responding provider and a real niche
- WHEN the ideation crew runs
- THEN candidate ideas come from the LLM response (no fallback title like "3 Errores Críticos…")

#### Scenario: LLM-02-3 — director curation routes through the shared router

- GIVEN tenant budget available and a validated script
- WHEN the video director curates title/description/hashtags/keywords
- THEN the curation calls the shared router's `acomplete()`
- AND the parsed fields land in `render_payload` (no direct completion call)

## ADDED Requirements

### Requirement: REQ-LLM-04 — Five-site routing and budget-gate guarantee

The system MUST enumerate exactly five production LLM call sites: ideation (`ideation_crew.py:64`), scriptwriting (`scriptwriting_crew.py:67`), video prompting (`video_prompt_crew.py:73`), DM reply (`dm_response.py:78`), and video-director curation. Every public entry point of the router's `acomplete()` MUST be reachable from these sites and no other production path. Any call site that spends tenant budget MUST pass the per-tenant budget guard (`check_tenant_llm_budget` in `backend/services/llm_budget_service.py:71`, pattern `dm_response.py:62-69`) before invoking the router; the director is one such budgeted site (see `contextual-video-director`).

#### Scenario: LLM-04-1 — exactly five call sites

- GIVEN the production codebase
- WHEN all `acomplete()` invocations are located
- THEN there are exactly five call sites
- AND none of them calls `litellm.completion` directly

#### Scenario: LLM-04-2 — director budget-checked before router

- GIVEN tenant spend above the monthly limit
- WHEN the video director runs
- THEN `check_tenant_llm_budget` blocks the router call
- AND no LLM tokens are spent for that tenant