# e2e-simulation-production-hardening Specification

## Purpose

Phase A & B: Full Lifecycle End-to-End Simulation with Event Verification (Phase A) and Production Infrastructure Hardening with Docker Compose Multi-Worker Segregation and Automated PostgreSQL Backups (Phase B).

## Requirements

### Requirement: REQ-E2E-01 — Full Lifecycle End-to-End Simulation
The test suite MUST include a comprehensive E2E integration test `test_full_pipeline_with_events.py` executing all 10 stages of the ViralSync content & lead gen lifecycle with zero regressions.

#### Scenario: E2E-01-1 — Complete lifecycle executes successfully
- GIVEN a new tenant onboarding
- WHEN the entire pipeline (Ingestion -> LangGraph -> Human Approvals -> Rendering -> Publish -> RUM 72h -> Inbound Lead -> Sales DM) runs
- THEN all state transitions complete successfully, DB records persist, and SSE events are dispatched.

### Requirement: REQ-PROD-01 — Multi-Worker Queue Segregation & Backup Automation
The production Docker Compose config MUST define segregated Celery worker services (`celery_video_worker`, `celery_metrics_worker`) and automated PostgreSQL backups via `postgres_backup.sh`.

#### Scenario: PROD-01-1 — Docker Compose validates multi-worker configuration
- GIVEN `agency/docker-compose.production.yml`
- WHEN parsed by Docker Compose
- THEN `celery_video_worker` and `celery_metrics_worker` consume dedicated queues with resource limits and backup automation is present.
