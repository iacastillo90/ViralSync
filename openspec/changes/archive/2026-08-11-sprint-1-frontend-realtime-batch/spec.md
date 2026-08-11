# sprint-1-frontend-realtime-batch Specification Delta

## Purpose

Sprint 1: React components and views for Live Realtime SSE Activity Feed and Batch Product Media Ingestion in the Next.js Dashboard.

## Requirements

### Requirement: REQ-FE-01 — Live Realtime Activity Feed Component
The frontend MUST provide a `LiveActivityFeed` component that connects to `/realtime/sse/{tenant_id}` and renders incoming events (`lead_captured`, `rum_metrics_evaluated`, `audit_event_logged`, `product_media_ingested`).

#### Scenario: FE-01-1 — Component renders active event notifications
- GIVEN a valid `tenant_id`
- WHEN an SSE event is received
- THEN `LiveActivityFeed` appends the event item with timestamp, event label, and payload summary to the active list.

### Requirement: REQ-FE-02 — Batch Product Ingest View
The frontend MUST provide a `BatchIngestView` component for ingesting multiple product records at `POST /api/v1/tenants/{tenant_id}/products/batch`.

#### Scenario: FE-02-1 — Batch ingest submits array of products
- GIVEN a list of product items with name and description
- WHEN submitted by the user
- THEN a POST request is sent to `/api/v1/tenants/{tenant_id}/products/batch` and success feedback is displayed.
