# docker-lockfile-db-bootstrap Specification

## Purpose

Stabilizes the ViralSync `agency/` stack: the image must build, the Python dependency set must match directly-imported libraries, a fresh Postgres must provision the full migration schema, DB init must be wired and idempotent, and the pytest suite must be 100% green.

## Requirements

### Requirement: Docker Image Builds from `agency/` Context

The `agency/Dockerfile` MUST build successfully from build context `agency/`; every `COPY` source path MUST resolve inside that context (or the context must be corrected so the paths resolve).

#### Scenario: Build succeeds from corrected context

- GIVEN the build context is `agency/` and `requirements.txt` resolves within it
- WHEN `docker build .` runs from `agency/`
- THEN the image builds with 0 fatal errors
- AND every `COPY` source path (requirements file, `agency/` tree) exists in context

#### Scenario: COPY path boundary is honored

- GIVEN a `COPY` references a path absent from the selected build context
- WHEN the build is invoked
- THEN it fails with a clear "not in build context" error, signaling the context mismatch

### Requirement: Lockfile Matches requirements.txt and Direct-Import Policy

`requirements.lock` MUST be regenerated from `requirements.txt` and MUST include `litellm`, `asyncpg`, `aiosqlite`, `sqlalchemy[asyncio]`, `tenacity`, `pyjwt`, `python-jose`; it MUST stay green against the prune test policy.

#### Scenario: Lockfile is a complete compile of requirements.txt

- GIVEN `requirements.txt` is the source of truth
- WHEN `uv pip compile requirements.txt -o requirements.lock` runs
- THEN every `requirements.txt` entry resolves to a pinned entry in the lock
- AND `litellm`, `asyncpg`, `aiosqlite`, `sqlalchemy`, `tenacity`, `pyjwt`, `python-jose` are all present in the lock

#### Scenario: Lockfile stays green after recompile

- GIVEN the lockfile was just regenerated
- WHEN the prune/dependency tests run against it
- THEN no policy assertion fails due to missing or pruned dependencies

### Requirement: Direct-Dependency Policy Asserted

`test_deps_prune.py` MUST treat `litellm`, `asyncpg`, `aiosqlite`, `sqlalchemy[asyncio]`, `tenacity`, `pyjwt`, `python-jose` as DIRECT dependencies (code imports them directly) and MUST assert them present, not absent.

#### Scenario: Direct dependencies are declared and pinned

- GIVEN code imports litellm, asyncpg, aiosqlite, sqlalchemy[asyncio], tenacity, pyjwt, python-jose directly
- WHEN the prune tests run against `requirements.txt`
- THEN each is declared exactly once with a `~=`/`==` pin
- AND none of them appears in the pruned/absent set

#### Scenario: Truly dead dependencies stay pruned

- GIVEN packages with zero imports across `backend/`, `agents/`, `workers/`, `knowledge/`, `gateway/`, `migrations/`
- WHEN the prune tests run
- THEN they assert those packages are absent from `requirements.txt`

### Requirement: Fresh Postgres Yields the Full Migration Schema

A fresh Postgres provisioned via `docker-compose` MUST yield every table defined in `migrations/001_init_schema.sql` and `migrations/002_add_video_metrics_and_fix_leads.sql`: `tenants`, `niches`, `market_maps`, `rum_thresholds`, `ideas`, `scripts`, `videos`, `campaigns`, `leads`, `llm_usage_log`, `video_metrics`.

#### Scenario: Fresh DB has the complete schema

- GIVEN a fresh empty Postgres provisioned via `docker-compose`
- WHEN schema provisioning runs once and `\dt` lists tables
- THEN all tables above exist, including `video_metrics` from migration 002

#### Scenario: Leads table carries migration 002 extensions

- GIVEN migration 002 has run
- WHEN `leads` columns are inspected
- THEN `operator_id`, `conversacion_history`, `updated_at` exist alongside base columns

### Requirement: DB Init Is Wired and Idempotent

DB initialization MUST be wired to startup (`init_db()` / `Base.metadata.create_all` on startup, or a real `alembic upgrade head`) and MUST be idempotent.

#### Scenario: Schema initializes on startup

- GIVEN the backend starts with an empty Postgres
- WHEN the app initializes
- THEN the full schema is created (0 tables before, expected table set after)

#### Scenario: Re-running init does not error

- GIVEN an already-initialized database
- WHEN init runs again
- THEN it succeeds without error (via `IF NOT EXISTS` / `create_all` semantics)

### Requirement: Pytest Suite Is 100% Green

The pytest suite MUST collect fully with 0 failures and 0 errors (baseline today: 97 passed, 3 failed, 1 error). This requires fixing the `dm_response.py` typing import (`List`/`Optional`/`Tuple` from `typing`, not `tenacity`), aligning `test_deps_prune.py` to the direct-dep policy, and making the e2e takeover return 200.

#### Scenario: dm_response imports cleanly

- GIVEN `agents/nodes/dm_response.py` imports `List`, `Optional`, `Tuple` from `typing`
- WHEN pytest collects the test suite
- THEN collection/import succeeds with no error

#### Scenario: E2E takeover returns 200

- GIVEN an authenticated tenant and an existing lead
- WHEN `POST /api/v1/tenants/{tenant_id}/leads/{lead_id}/takeover` runs in `test_full_pipeline.py`
- THEN the response is 200 with `{"status": "handled_by_human"}`, not 503

#### Scenario: Full suite is green

- GIVEN all test files in `tests/`
- WHEN `pytest` runs
- THEN all tests collect, 0 fail, 0 errors
