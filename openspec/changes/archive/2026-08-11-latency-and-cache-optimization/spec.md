# latency-and-cache-optimization Specification Delta

## Purpose

Phase 1 Latency & Response Time Optimization: Enable LiteLLM proxy response caching via Redis, implement async non-blocking search in SearXNG MCP (`asearxng_search_sanitized`), gather async tasks concurrently in ideation/scriptwriting crews, and eliminate 1.0s timeout polling loops in FastAPI SSE streaming.

## Requirements

### Requirement: REQ-LAT-01 — Async Non-blocking SearXNG Web Search
The SearXNG MCP module MUST expose an asynchronous function `asearxng_search_sanitized` using `httpx.AsyncClient` that does not block the asyncio event loop during web search operations.

#### Scenario: LAT-01-1 — Async SearXNG search executes without blocking event loop
- GIVEN a valid search query
- WHEN `await asearxng_search_sanitized(query)` is called
- THEN it completes asynchronously returning sanitized search results or synthetic fallback without blocking concurrent tasks.

### Requirement: REQ-LAT-02 — Non-polling SSE Realtime Endpoint
The `/realtime/sse/{tenant_id}` endpoint MUST receive event payloads directly from `sse_manager` subscriptions without running a 1.0s `asyncio.wait_for` timeout polling loop.

#### Scenario: LAT-02-1 — SSE endpoint yields events as they arrive
- GIVEN a client subscribed to `/realtime/sse/{tenant_id}`
- WHEN a payload is published to `sse_manager`
- THEN the SSE generator yields the event immediately and closes gracefully upon client disconnection without unnecessary 1.0s timeout wake-ups.

### Requirement: REQ-LAT-03 — LiteLLM Gateway Caching Config
The LiteLLM configuration in `staging` and `production` MUST specify `cache_type: redis` under `router_settings` / `litellm_settings` to enable response caching for prompt completions across tenants.

#### Scenario: LAT-03-1 — Cache settings configured in production gateway YAML
- GIVEN `litellm_config.production.yaml`
- WHEN parsed by LiteLLM Proxy
- THEN cache settings reference Redis cache for prompt completions.
