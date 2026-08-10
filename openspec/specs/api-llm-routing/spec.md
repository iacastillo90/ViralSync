# api-llm-routing Specification

## Purpose

Shared multi-provider LLM router for the whole pipeline loop. Every LLM call goes through one router with real failover (gemini → groq → openrouter → ollama) so a single provider's quota cannot silently degrade content to templates, and the default provider is fixed from a real-key test during verify — never pre-claimed.

Replaces the direct `litellm.completion()` call sites (`ideation_crew.py`, `scriptwriting_crew.py`, `video_prompt_crew.py`, `dm_response.py`) which used one default model and degraded to static templates on Gemini 429s; `contextual-video-redesign` added the video director's metadata curation as the fifth call site through the same router. Brings the LiteLLM proxy up on `:4000` so the gateway fallback pool (`gateway/litellm_config.{dev,staging,production}.yaml`) stops being dead code.

## Requirements

### Requirement: REQ-LLM-01 — Shared multi-provider LLM router (agents/llm.py)

**User Story**: As an operator, I want every LLM call in the loop to go through one router with real failover (gemini → groq → openrouter → ollama), so a single provider's quota cannot silently degrade content to templates.

**Motivo**: The 4 call sites call `litellm.completion()` directly with one default model (`ideation_crew.py:72-83`, `scriptwriting_crew.py:75-84`, `video_prompt_crew.py:81-90`, `dm_response.py:84-95`). Gemini 429s today (`generate_content_free_tier_requests, limit: 20`) and crews fall back to static templates. The gateway fallback pool (`gateway/litellm_config.{dev,staging,production}.yaml`) is dead code while the proxy never runs.

The system MUST expose a shared router helper that attempts providers in order and returns the first successful completion. When at least one provider responds, the returned text MUST be LLM-generated (no template substitution).

#### Scenario: LLM-01-1 — context-aware completion with no template

- GIVEN the router with at least one responding provider (real key)
- WHEN a crew requests a completion with its system/user prompt
- THEN the router returns the completion from the first healthy provider
- AND the caller's template fallback is not used

#### Scenario: LLM-01-2 — fallback on gemini 429

- GIVEN the first provider (gemini) returns `429 Too Many Requests`
- WHEN the router resolves
- THEN it tries the next provider (groq), then openrouter
- AND returns the completion of the first that responds

#### Scenario: LLM-01-3 — all providers fail: honest failure

- GIVEN every configured provider fails or rate-limits
- WHEN the router resolves
- THEN it surfaces an honest error naming the reason (logged)
- AND the caller MAY use its existing template fallback

### Requirement: REQ-LLM-02 — Route the five call sites through the shared router

**User Story**: As a developer, I want the five LLM call sites (ideation, scriptwriting, video prompting, DM response, and the video director's metadata curation) to call the shared router, so routing policy lives in one place and template fallback only fires when every provider fails.

**Motivo**: Centralizes config and removes per-site `litellm.completion` divergence (temperature/max_tokens per site stay as parameters). The video director gains an LLM curation call in `contextual-video-redesign`, so it becomes the fifth call site and MUST use the router instead of introducing a direct call.

The system MUST route ideation, scriptwriting, video prompting, DM-response generation, and video-director metadata curation through REQ-LLM-01. Direct `litellm.completion` imports in `ideation_crew.py`, `scriptwriting_crew.py`, `video_prompt_crew.py`, `dm_response.py`, and `video_director_crew.py` MUST NOT exist; every one of these sites MUST call the shared router's `acomplete()`.

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

### Requirement: REQ-LLM-03 — Proxy up; default provider proven by test

**User Story**: As an operator, I want `docker compose up litellm` to bring the proxy up on :4000 with the gateway config, and the default provider validated against real credentials during verify — not pre-claimed.

**Motivo**: The proposal must not assert a provider works; Gemini is 429ing and Groq/OpenRouter are unproven for this app.

The system MUST start the `litellm` compose service (:4000, `--config /app/config/litellm_config.${AGENCY_ENV}.yaml`). The default provider SHOULD be fixed only after a verify-time `curl`/test with real keys proves at least one responds.

#### Scenario: LLM-03-1 — proxy reachable

- GIVEN `docker compose up litellm`
- WHEN the service health is checked
- THEN :4000 is reachable and the gateway config for the current env loads

#### Scenario: LLM-03-2 — default chosen from evidence

- GIVEN real GEMINI/GROQ/OPENROUTER keys in the environment
- WHEN verify runs a real completion through the router
- THEN the default provider is set from the observed responding provider (or the chain, if no single one is reliable)

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