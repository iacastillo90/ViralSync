# enterprise-4-events Specification Delta

## Purpose

Implement 4 new enterprise lifecycle events for ViralSync: Inbound Lead Capture SSE Event (`lead_captured`), 72h RUM Recalibration Event (`rum_metrics_evaluated`), Multi-Tenant Security Audit Event (`audit_event_logged`), and Batch Product Media Ingestion Event (`product_media_ingested`).

## Requirements

### Requirement: REQ-EVT-01 — Inbound Lead Capture Event (`lead_captured`)
The Instagram Webhook processor MUST publish a `lead_captured` event via `sse_manager` whenever a qualified lead is extracted from a comment or DM.

#### Scenario: EVT-01-1 — Lead capture emits SSE event
- GIVEN a valid webhook payload containing a keyword match
- WHEN `process_instagram_webhook_payload` processes the lead
- THEN `sse_manager.publish_event` is called with event type `"lead_captured"` and lead payload.

### Requirement: REQ-EVT-02 — 72h RUM Recalibration Event (`rum_metrics_evaluated`)
The RUM learning task MUST publish a `rum_metrics_evaluated` event via `sse_manager` upon completing the 72h metrics evaluation loop.

#### Scenario: EVT-02-1 — RUM evaluation emits SSE event
- GIVEN a video metric evaluated at 72h
- WHEN `process_rum_learning_loop` completes calculation
- THEN `sse_manager.publish_event` is called with event type `"rum_metrics_evaluated"`.

### Requirement: REQ-EVT-03 — Audit Governance Event (`audit_event_logged`)
The audit logger MUST publish an `audit_event_logged` event via `sse_manager` for security-sensitive administrative actions.

#### Scenario: EVT-03-1 — Audit log emits SSE event
- GIVEN an administrative audit log call (e.g., budget exceeded or human approval)
- WHEN `log_audit_event` is invoked
- THEN an SSE event `"audit_event_logged"` is dispatched for the target tenant.

### Requirement: REQ-EVT-04 — Batch Product Media Ingestion Event (`product_media_ingested`)
The ingestion router MUST provide a `POST /tenants/{tenant_id}/products/batch` endpoint that accepts multiple product records and publishes a `product_media_ingested` event.

#### Scenario: EVT-04-1 — Batch product ingest emits SSE event
- GIVEN a list of products in `POST /tenants/{tenant_id}/products/batch`
- WHEN products are persisted via DAO
- THEN `sse_manager.publish_event` is called with event type `"product_media_ingested"`.
