# Health Honesty — Spec

Delta covering the new capability `platform-health`: an honest, backward-compatible unified `/health` contract — real per-dependency probes (db/redis/qdrant) with timeouts gathered in parallel, truthful `healthy|degraded|unhealthy` aggregation with readiness HTTP semantics (503 only for critical db failure), and a single-source `__version__`. Behavior only; implementation is design's job.

## Capability: `platform-health` (new, add)

### Requirement: REQ-PH-01 — Honest per-dependency probes

**User Story**: As an operator, I want `/health` to actually probe PostgreSQL, Redis and Qdrant — each with its own timeout, run in parallel — so a green status means the dependency really answered.

**Motivo**: `health.py:30` hardcodes `db_status="healthy"` (PG never probed), `:42-46` assigns `qdrant_status="healthy"` without ever instantiating a client, and the only real probe (Redis) is sync-blocking.

The system MUST probe the database with a real `SELECT 1` through the async SQLAlchemy engine (`backend/db/session.py` `async_engine`) with a 2s timeout; MUST probe Redis with a real async ping (`redis.asyncio`) with a 1s timeout; MUST probe Qdrant with a real `get_collections` via `AsyncQdrantClient` with a 3s timeout. The three probes MUST run via `asyncio.gather` so total latency ≈ the slowest probe. Probes MUST be module-level functions acting as monkeypatch seams for tests. The system MUST NOT assign "healthy" without a successful probe, and MUST NOT hang past the per-probe timeout.

#### Scenario: PH-01-1 — all dependencies healthy

- GIVEN database, Redis and Qdrant all reachable and answering
- WHEN `/health` runs its probes
- THEN every per-dependency probe returns `healthy` and each probe was actually invoked (no fabricated assignments)

#### Scenario: PH-01-2 — database down

- GIVEN the database connection/`SELECT 1` fails
- WHEN `/health` probes
- THEN the database probe reports `unhealthy`

#### Scenario: PH-01-3 — Redis down

- GIVEN the Redis async ping fails
- WHEN `/health` probes
- THEN the Redis probe reports `degraded` (non-critical, memory-fallback)

#### Scenario: PH-01-4 — Qdrant down

- GIVEN `get_collections` fails (client or connection error)
- WHEN `/health` probes
- THEN the Qdrant probe reports `degraded` (non-critical, memory-fallback)

#### Scenario: PH-01-5 — probe timeout capped, no hang

- GIVEN a dependency that never answers within its cap (db 2s, redis 1s, qdrant 3s)
- WHEN the probe is awaited
- THEN it resolves within the cap as `degraded`/`unhealthy` (per criticality) and the endpoint never hangs

### Requirement: REQ-PH-02 — Honest aggregation + HTTP semantics

**User Story**: As an operator, I want `/health` to aggregate per-dependency status into `healthy|degraded|unhealthy` and return HTTP 503 only when the critical dependency (database) is down, so readiness is truthful.

**Motivo**: `:48` computes `overall_status` from `redis`+`db` only, ignoring Qdrant entirely; a dead database would still answer HTTP 200.

The system MUST report per-dependency status as `healthy|degraded|unhealthy` under the existing keys `database`, `redis`, `qdrant`. The overall `status` MUST be `healthy` iff all dependencies are healthy, `degraded` iff only non-critical dependencies (redis/qdrant) are down, and `unhealthy` iff the critical dependency (database) is down. HTTP MUST be 200 for `healthy` and `degraded`, and 503 for `unhealthy`. The response MAY include `latency_ms`/`checked_at`. The response keys `status`, `version`, `database`, `redis`, `qdrant` MUST be preserved.

#### Scenario: PH-02-1 — healthy returns 200 with all keys

- GIVEN all probes healthy
- WHEN `GET /health`
- THEN HTTP 200 with `status="healthy"` and the keys `status, version, database, redis, qdrant` present

#### Scenario: PH-02-2 — database down returns 503

- GIVEN the database probe reports `unhealthy` (Redis/Qdrant state irrelevant)
- WHEN `GET /health`
- THEN HTTP 503 with overall `status="unhealthy"`

#### Scenario: PH-02-3 — only redis/qdrant down returns 200 degraded

- GIVEN database healthy but redis and/or qdrant `degraded`
- WHEN `GET /health`
- THEN HTTP 200 with overall `status="degraded"` (503 must not fire)

### Requirement: REQ-PH-03 — Version from a single source

**User Story**: As a maintainer, I want `/health` version and the FastAPI app version to come from one source, so a version bump never goes stale or drifts.

**Motivo**: `version="1.0.0"` is hardcoded at `health.py:19` (model default) and `:52` (response) and again at `main.py:61` — three independent copies that can drift.

The system MUST define `__version__` in the new `backend/__init__.py` and MUST reference it from `health.py` (response `version`) and `main.py:61` (FastAPI `version=`). The version MUST NOT be hardcoded anywhere in the health response path.

#### Scenario: PH-03-1 — health version matches app version

- GIVEN `backend.__version__` = some value
- WHEN `GET /health` and the OpenAPI app info are read
- THEN the health `version` equals the app `version` equals `backend.__version__`

#### Scenario: PH-03-2 — changing __version__ propagates

- GIVEN `backend/__init__.py.__version__` is bumped to a new value
- WHEN `/health` and the app are inspected without further edits
- THEN both report the new value; no hardcoded copy remains

### Requirement: REQ-PH-04 — Compose honesty: probe reachability in-container

**User Story**: As an operator running docker-compose, I want the backend's Qdrant probe to reach the real `qdrant` service, so an honest probe does not false-fail inside the container.

**Motivo**: compose `:96` sets `QDRANT_HOST=qdrant`, which no code reads; the code reads `QDRANT_URL` (default `localhost:6333`), so in-container the probe would target the backend container itself and falsely fail.

The system MUST provide `QDRANT_URL=qdrant:6333` in the backend service environment in `docker-compose.yml` (replacing/augmenting the unused `QDRANT_HOST`), and the `qdrant` service MUST declare a healthcheck. The compose backend config MUST make the honest Qdrant probe succeed in-container.

#### Scenario: PH-04-1 — in-container probe reaches qdrant:6333

- GIVEN `docker-compose up` with the updated backend environment
- WHEN the backend runs its Qdrant probe inside the container
- THEN the probe connects to `qdrant:6333` (the compose service) and reports `healthy`, not a false failure against localhost

## Capability flags

| Capability | Flag | Kind |
|------------|------|------|
| `platform-health` | add | new spec |

## Traceability

| Requirement | Scenarios | Debt closed |
|-------------|-----------|-------------|
| REQ-PH-01 | PH-01-1 … PH-01-5 | health lies (db/qdrant never probed), sync-blocking redis |
| REQ-PH-02 | PH-02-1, PH-02-2, PH-02-3 | qdrant ignored in aggregation, no 503 on dead db |
| REQ-PH-03 | PH-03-1, PH-03-2 | version hardcoded (3 copies) |
| REQ-PH-04 | PH-04-1 | qdrant ignored (QDRANT_HOST unused; QDRANT_URL gap) |

## Risks / notes

- **503-on-degraded would break tests**: default test env has no redis/qdrant → `degraded` → MUST stay HTTP 200; 503 reserved for critical (db) failure (REQ-PH-02-3).
- **Zero-token constraint**: module-level probe seams + fakes (`redis.asyncio.from_url`, `AsyncQdrantClient`) test every status/timeout path; `FORCE_SQLITE=true` keeps the db probe passing on SQLite (`SELECT 1` is dialect-agnostic).
- **Version single source**: `backend/__init__.py` does not exist at HEAD — created by design; must not create circular imports (`main.py` already imports from `backend.*`).
- **Non-goals**: no `/ready` split, no liveness endpoint, no renderer/publisher `/health`, frontend, auth, or retry/backoff changes.
