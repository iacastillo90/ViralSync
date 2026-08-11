# dashboard-sse-views-git-push Specification

## Purpose

Final Phases 1, 2 & 3: Realtime SSE Integration in Dashboard Views (`PipelineMonitorView.jsx` & `InboundLeadsView.jsx`), Architecture & Codebase Health Executive Report, and Git Push Remote Synchronization.

## Requirements

### Requirement: REQ-FE-05 — Live SSE Event Stream in Dashboard Views
The frontend dashboard views MUST listen to EventSource `/realtime/sse/{tenantId}` and dynamically update pipeline state and lead rows upon event arrival (`lead_captured`, `node_progress`).

#### Scenario: FE-05-1 — Inbound leads view prepends SSE captured lead
- GIVEN a user viewing `InboundLeadsView`
- WHEN a `lead_captured` event arrives via SSE
- THEN a new lead row is prepended to the active lead state without page refresh.
