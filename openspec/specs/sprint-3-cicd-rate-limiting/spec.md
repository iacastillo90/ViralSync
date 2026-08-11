# sprint-3-cicd-rate-limiting Specification

## Purpose

Sprint 3: CI/CD Workflow Hardening and Dynamic Tenant Tier Rate Limiting (`free`, `pro`, `enterprise`).

## Requirements

### Requirement: REQ-RAT-01 — Dynamic Tenant Tier Rate Limiting
The rate limiter MUST return request limits based on the tenant's subscription tier (`free`: 60, `pro`: 300, `enterprise`: 1000 requests/min).

#### Scenario: RAT-01-1 — Rate limit tiers returned
- GIVEN a valid tenant tier name
- WHEN `get_tenant_tier_rate_limit(tier)` is called
- THEN the corresponding quota per minute is returned.
