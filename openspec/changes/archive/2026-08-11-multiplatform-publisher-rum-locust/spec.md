# multiplatform-publisher-rum-locust Specification Delta

## Purpose

Phases 1, 2 & 3: Multi-Platform Publisher Adapters (TikTok & YouTube Shorts), Interactive RUM Visualization & RAG Brain Management in Next.js, and Locust Load Test Harness.

## Requirements

### Requirement: REQ-PUB-02 — Multi-Platform Video Publisher Adapters
The Publisher microservice MUST support publishing video payloads to `"instagram"`, `"tiktok"`, and `"youtube_shorts"` targets.

#### Scenario: PUB-02-1 — TikTok & YouTube Shorts publishing succeeds
- GIVEN a valid video payload with target `"tiktok"` or `"youtube_shorts"`
- WHEN `POST /publish` is called on the publisher microservice
- THEN the appropriate platform publisher adapter handles the request and returns a valid publication status.

### Requirement: REQ-RUM-02 — RUM Breakdown Visualization & Brain Management UI
The frontend MUST provide components for visualizing 6-variable RUM scores (`RUMBreakdownBarChart.jsx`) and managing RAG knowledge documents (`BrainManagementView.jsx`).

#### Scenario: RUM-02-1 — Components render variable breakdown
- GIVEN RUM score breakdown parameters ($U, I, C, S, D, A$)
- WHEN `RUMBreakdownBarChart` renders
- THEN bars are styled according to performance thresholds.

### Requirement: REQ-LOAD-01 — Locust Load Test Harness
The codebase MUST provide a `locustfile.py` script to simulate concurrent SSE connections and REST API traffic for load certification.

#### Scenario: LOAD-01-1 — Locust scenario executes load loop
- GIVEN the Locust load testing environment
- WHEN `locustfile.py` runs
- THEN virtual users generate simulated traffic to `/health`, `/metrics`, and `/realtime/sse`.
