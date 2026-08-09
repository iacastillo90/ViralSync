# Pipeline Production Gaps — Spec

Delta covering four capabilities: new `api-llm-routing`, new `pipeline-persistence-writes`, new `api-publish-wiring`, and a MODIFIED requirement (REQ-API-06) in `api-ideas-scripts-brain-get`. Behavior is specified; implementation is design's job.

## Requirements

### Capability: `api-llm-routing` (new, add)

#### Requirement: REQ-LLM-01 — Shared multi-provider LLM router (agents/llm.py)

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

#### Requirement: REQ-LLM-02 — Replace the 4 direct call sites

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

#### Requirement: REQ-LLM-03 — Proxy up; default provider proven by test

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

### Capability: `pipeline-persistence-writes` (new, add)

#### Requirement: REQ-PERSIST-01 — Migration 004 + Product ORM

**User Story**: As an operator, I want a `products` table and a matching `Product` ORM so product data (name, description, `product_image_url`) is persisted per tenant.

**Motivo**: No `products` table exists in migrations 001-003; `product_image_url` is produced by product-ingest but never stored.

The system MUST add migration `004_*.sql` creating `products` (tenant FK, name, description, `product_image_url`, created_at) and a `Product` ORM model mapping exactly those columns (following the DDL-as-truth convention in `models.py`).

#### Scenario: PERSIST-01-1 — products table exists after 004

- GIVEN Postgres with migrations 001-003 applied
- WHEN migration 004 applies
- THEN a `products` table exists with `tenant_id` FK and `product_image_url` column

#### Scenario: PERSIST-01-2 — ORM/DDL column parity

- GIVEN the `Product` model imported
- WHEN its `__table__.columns` keys are collected
- THEN the set matches the 004 DDL exactly (column read-back test, per `backend-video-metric-ddl-alignment` pattern)

#### Requirement: REQ-PERSIST-02 — Graph run writes real ideas/scripts/videos rows

**User Story**: As a user, I want each graph run to persist candidates, the approved script, and the video record via async DAOs, so `GET /ideas` and `GET /scripts` show real rows instead of `[]`.

**Motivo**: Tables and async ORM exist and are functional; nothing writes (8 tenants, 0 rows). Nodes only update in-memory state (`ideation.py:14-33`, `scriptwriting.py:15-30`).

The system MUST write, via async DAOs on the existing session: an `ideas` row per generated candidate; a `scripts` row (FK to the approved idea) once the script is generated; and a `videos` row (FK to the script) capturing raw/edited URIs and publish status.

#### Scenario: PERSIST-02-1 — rows land in the real tables

- GIVEN a completed graph run for a tenant
- WHEN the run finishes
- THEN `ideas` has one row per candidate, `scripts` has one row referencing the approved idea, and `videos` has one row referencing the script
- AND the rows are visible via `psql` and via the existing GETs

#### Scenario: PERSIST-02-2 — write failure is honest

- GIVEN a DAO write raises (DB error)
- WHEN the node runs
- THEN the node fails honestly with the error surfaced in logs (no silent state-only success)

#### Requirement: REQ-PERSIST-03 — approve_idea is a real DB commit

**User Story**: As a user, I want clicking Aprobar to set `approval_status` on the idea row, so the DB, the graph, and the UI agree.

**Motivo**: `approve_idea` (`graph_execution.py:67-102`) is an honest no-op — it broadcasts SSE and resumes the graph but never persists. This reverses that semantics (see REQ-API-06 MODIFIED).

The system MUST, on `POST /{tenant_id}/ideas/approve` with `status=approved|rejected`, update the matching `ideas.approval_status` row and resume the graph from its checkpoint.

#### Scenario: PERSIST-03-1 — approval commits

- GIVEN a pending `ideas` row with a real UUID
- WHEN `POST /api/v1/tenants/{tid}/ideas/approve` `{idea_id, status: "approved"}`
- THEN the row's `approval_status` becomes `approved` (asserted via psql/SQLite)
- AND the graph resumes at the idea checkpoint

#### Scenario: PERSIST-03-2 — rejection commits too

- GIVEN the same endpoint with `status: "rejected"`
- WHEN it runs
- THEN the row's `approval_status` becomes `rejected` and no idea is promoted to scriptwriting

#### Requirement: REQ-PERSIST-04 — Postgres checkpointer (state survives restart)

**User Story**: As an operator, I want graph state persisted in Postgres (via `langgraph-checkpoint-postgres`, its own table), so an interrupted run resumes after a backend restart.

**Motivo**: `graph_execution.py:12,20-21` uses a global `MemorySaver`; all state is lost on restart. MemorySaver sessions are deliberately not migrated (non-goal).

The system MUST compile the graph with a Postgres-backed checkpointer keyed by `thread_id = tenant_id`; a paused run MUST be resumable from the same thread after a backend restart.

#### Scenario: PERSIST-04-1 — resume after restart

- GIVEN a run paused at `human_approval_idea`
- WHEN the backend restarts and the same thread_id resumes
- THEN execution continues from the checkpoint with prior state intact

#### Scenario: PERSIST-04-2 — old in-memory sessions discarded

- GIVEN pre-change MemorySaver history
- WHEN the saver is swapped to Postgres
- THEN no migration of those sessions is attempted (documented, non-goal)

#### Requirement: REQ-PERSIST-05 — product data flows ingest → state → DB (data wiring only)

**User Story**: As a user, I want the `product_image_url` captured at product-ingest to reach graph state and persist, so the render path can later switch to IMAGE_TO_VIDEO.

**Motivo**: `product_image_url` exists in `AgencyState` (`graph.py:30`) but nothing populates it; the frontend never forwards the ingest result. LLM-composed video metadata (title/narrative) is explicitly OUT of scope — reserved extension point.

The system MUST accept `product_image_url` on `/graph/run`, place it in graph state, and persist it with the `products` row; the pipeline MUST continue normally when it is absent.

#### Scenario: PERSIST-05-1 — image URL persists with the product

- GIVEN a product-ingest response with `product_image_url`
- WHEN `/graph/run` starts and the product is persisted
- THEN the `products` row stores the URL and state carries it downstream

#### Scenario: PERSIST-05-2 — no product: graceful TEXT_TO_VIDEO

- GIVEN no product ingested (`product_image_url` empty)
- WHEN the graph runs
- THEN the pipeline completes without error on the text-to-video path

### Capability: `api-publish-wiring` (new, add)

#### Requirement: REQ-PUBLISH-01 — /graph/run injects IG credentials into state

**User Story**: As a user, I want the `ig_user_id`/`ig_access_token` I hold for a tenant to reach graph state, so publish can act on them.

**Motivo**: `GraphRunRequest` (`graph_execution.py:24-33`) already declares the fields, but the frontend sends only `{force_reideation: true}` (`PipelineMonitorView.jsx:17-20`), so they are always `None`.

The system MUST accept `ig_user_id`/`ig_access_token` on `POST /{tenant_id}/graph/run` and inject them into the initial graph state for `node_publish`; credentials MUST NOT be persisted server-side (request-scoped only).

#### Scenario: PUBLISH-01-1 — tokens reach node_publish

- GIVEN a `/graph/run` request with `ig_user_id` and `ig_access_token`
- WHEN the graph executes
- THEN `node_publish` receives both values from state

#### Scenario: PUBLISH-01-2 — absent tokens are honest

- GIVEN a request with no IG credentials
- WHEN the graph reaches publish
- THEN publish fails honestly with the token-absent error — no simulated publish

#### Requirement: REQ-PUBLISH-02 — node_publish calls the real publisher path (:8002 or adapters)

**User Story**: As an operator, I want `node_publish` wired to the ready publisher contract (microservice HTTP :8002 or direct adapters), so a real token yields a real Graph API publish and dev simulation stays scoped to `token_`-prefixed values.

**Motivo**: The full IG flow exists (`adapters.py:49-76`, media → poll → media_publish, v19.0); the microservice (`publisher/app.py:41-65`, `POST /publish`) is defined on :8002 in compose but never wired from the graph.

The system MUST connect `node_publish` to the publisher contract when `ig_user_id`/`ig_access_token` are present: real non-`token_` tokens MUST drive the real Graph API flow; in dev, tokens starting with `token_` MAY keep the existing honest simulation; missing tokens MUST raise the existing security error and MUST NOT fabricate a `published_post_id`.

#### Scenario: PUBLISH-02-1 — valid real token publishes for real

- GIVEN `ig_user_id` and a real (non-`token_`) `ig_access_token` in state
- WHEN `node_publish` runs
- THEN it calls the publisher (:8002 HTTP or direct adapters) and returns the real `published_post_id` from the Graph API

#### Scenario: PUBLISH-02-2 — dev simulated token stays honest

- GIVEN `AGENCY_ENV=dev` and a token starting with `token_`
- WHEN `node_publish` runs
- THEN it returns the dev-simulated id (existing `adapters.py` behavior), clearly scoped to dev

#### Scenario: PUBLISH-02-3 — no token: no fake id

- GIVEN no `ig_user_id` or no `ig_access_token`
- WHEN `node_publish` runs
- THEN the security error is raised and no `published_post_id` is invented

#### Requirement: REQ-PUBLISH-03 — Frontend sends tokens + product_image_url

**User Story**: As a user, I want PipelineMonitor/ProductIngestModal to forward the tenant's IG credentials (from session) and the ingest `product_image_url` in the graph-run body, so the backend wiring above actually receives them.

**Motivo**: Honest wiring requires the client to send what the API already accepts.

The system SHOULD send `ig_user_id`/`ig_access_token` (from the user's session, when present) and `product_image_url` in the `/graph/run` body instead of only `{force_reideation}`.

#### Scenario: PUBLISH-03-1 — session credentials forwarded

- GIVEN a tenant session that holds IG credentials
- WHEN PipelineMonitor triggers `/graph/run`
- THEN the body includes `ig_user_id`/`ig_access_token` (not only `force_reideation`)

#### Scenario: PUBLISH-03-2 — no credentials: run still starts

- GIVEN no stored IG credentials
- WHEN the frontend triggers `/graph/run`
- THEN the body omits credentials and the run starts, failing honestly at publish per REQ-PUBLISH-01

### Capability: `api-ideas-scripts-brain-get` (MODIFIED)

#### Requirement: REQ-API-06 (MODIFIED) — Approve/publish: real commits; no fabricated ids

(Previously: both approve endpoints returned `202` queued-intent no-ops writing nothing — the semantic this change reverses for idea approval.)

`POST /{tenant_id}/ideas/approve` MUST perform a real `ideas.approval_status` UPDATE (per REQ-PERSIST-03). `POST /{tenant_id}/publish/approve` MUST NOT fabricate `published_post_id`/`ig_reel_*`; it MUST only resume publish when valid tokens exist in state, and MUST surface an honest error otherwise. Neither endpoint MAY invent identifiers.

#### Scenario: API-06-1 (updated) — approve commits for real

- GIVEN a pending `ideas` row
- WHEN `POST /{tid}/ideas/approve` `{idea_id, status: "approved"}`
- THEN the response signals the committed approval (202 accepted + resume, per existing SSE contract)
- AND the row's `approval_status` is `approved` in the DB (no-op removed)

#### Scenario: API-06-2 (updated) — publish approval without tokens is honest

- GIVEN no IG credentials in state
- WHEN `POST /{tid}/publish/approve`
- THEN the response contains no `published_post_id` or fabricated resource
- AND publish does not pretend to run (honest queued/error state)

## Capability flags

| Capability | Flag | Kind |
|------------|------|------|
| `api-llm-routing` | add | new spec |
| `pipeline-persistence-writes` | add | new spec |
| `api-publish-wiring` | add | new spec |
| `api-ideas-scripts-brain-get` | update | REQ-API-06 modified (delta merged at archive) |

## Traceability

| Requirement | Scenarios |
|-------------|-----------|
| REQ-LLM-01 | LLM-01-1, LLM-01-2, LLM-01-3 |
| REQ-LLM-02 | LLM-02-1, LLM-02-2 |
| REQ-LLM-03 | LLM-03-1, LLM-03-2 |
| REQ-PERSIST-01 | PERSIST-01-1, PERSIST-01-2 |
| REQ-PERSIST-02 | PERSIST-02-1, PERSIST-02-2 |
| REQ-PERSIST-03 | PERSIST-03-1, PERSIST-03-2 |
| REQ-PERSIST-04 | PERSIST-04-1, PERSIST-04-2 |
| REQ-PERSIST-05 | PERSIST-05-1, PERSIST-05-2 |
| REQ-PUBLISH-01 | PUBLISH-01-1, PUBLISH-01-2 |
| REQ-PUBLISH-02 | PUBLISH-02-1, PUBLISH-02-2, PUBLISH-02-3 |
| REQ-PUBLISH-03 | PUBLISH-03-1, PUBLISH-03-2 |
| REQ-API-06 (mod) | API-06-1, API-06-2 |

## Risks / notes

- **Provider reality at verify time (High)**: Gemini is 429ing and Groq/OpenRouter are unproven for this app; the default must be fixed from a real test, never pre-claimed (REQ-LLM-03-2).
- **Graph contract change (Med)**: nodes gain DB writes (sync → async/DAO); mitigated by isolated DAOs and per-node tests.
- **Checkpointer swap (Low)**: MemorySaver sessions are discarded by design; no migration attempted (REQ-PERSIST-04-2).
- **OAuth explicitly out of scope**: no Meta OAuth connect endpoint in this change — wiring only; real publish requires real tokens that only a later change (OAuth connect) can mint.
- **Video design LLM out of scope**: metadata/title/narrative composition and LLM population of `product_image_url` are post-change; this spec reserves the data plumbing only (REQ-PERSIST-05).
- **No secrets**: artifacts reference env var names only (`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `TEST_INSTAGRAM_ACCESS_TOKEN`).
- **Scope note**: `dm_response.py` is a call-site replacement (REQ-LLM-02) but its DM graph/persistence is untouched by G-B/G-C.
