# api-publish-wiring Specification

## Purpose

Honest Instagram publish wiring: `/graph/run` injects the tenant's IG credentials (`ig_user_id`/`ig_access_token`) into graph state, `node_publish` calls the real publisher path (`:8002` HTTP or direct adapters), and the frontend forwards tokens + `product_image_url` in the graph-run body.

Credentials are request-scoped only — never persisted server-side. Real non-`token_` tokens drive the real Graph API flow; dev keeps the honest `token_` simulation; missing tokens raise the existing security error and MUST NOT fabricate a `published_post_id`. OAuth connect is explicitly out of scope (wiring only — real tokens come from a later OAuth change).

## Requirements

### Requirement: REQ-PUBLISH-01 — /graph/run injects IG credentials into state

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

### Requirement: REQ-PUBLISH-02 — node_publish calls the real publisher path (:8002 or adapters)

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

### Requirement: REQ-PUBLISH-03 — Frontend sends tokens + product_image_url

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