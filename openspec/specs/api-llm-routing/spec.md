# api-llm-routing Specification

## Purpose

Shared multi-provider LLM router for the whole pipeline loop. Every LLM call goes through one router with real failover (gemini → groq → openrouter → ollama) so a single provider's quota cannot silently degrade content to templates, and the default provider is fixed from a real-key test during verify — never pre-claimed.

Replaces the 4 direct `litellm.completion()` call sites (`ideation_crew.py`, `scriptwriting_crew.py`, `video_prompt_crew.py`, `dm_response.py`) which used one default model and degraded to static templates on Gemini 429s; brings the LiteLLM proxy up on `:4000` so the gateway fallback pool (`gateway/litellm_config.{dev,staging,production}.yaml`) stops being dead code.

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

### Requirement: REQ-LLM-02 — Replace the 4 direct call sites

**User Story**: As a developer, I want the four crews/nodes to call the shared router, so routing policy lives in one place and template fallback only fires when every provider fails.

**Motivo**: Centralizes config and removes per-site `litellm.completion` divergence (temperature/max_tokens per site stay as parameters).

The system MUST route ideation, scriptwriting, video prompting, and DM-response generation through REQ-LLM-01. Direct `litellm.completion` imports in those four files MUST be removed.

#### Scenario: LLM-02-1 — no direct call remains

- GIVEN the shipped change
- WHEN `ideation_crew.py`, `scriptwriting_crew.py`, `video_prompt_crew.py`, `dm_response.py` are scanned
- THEN each imports and calls the shared router, and no `litellm.completion` call remains in them

#### Scenario: LLM-02-2 — LLM text, not template, when a provider responds

- GIVEN a responding provider and a real niche
- WHEN the ideation crew runs
- THEN candidate ideas come from the LLM response (no fallback title like "3 Errores Críticos…")

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