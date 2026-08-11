# Proposal: Health Honesty

## Intent

The unified `/health` endpoint lies (HEAD ae7a189): `health.py:30` hardcodes `db_status="healthy"` (PG never probed), `:42-46` assigns `qdrant_status="healthy"` without a client, `:48` ignores qdrant in aggregation, `:19/:52` hardcode `version="1.0.0"` (also `main.py:61`); only Redis is truly pinged, sync-blocking. Goal: an honest, backward-compatible health contract.

## Scope

### In Scope (LOCKED)

- Rewrite `health.py`: async probes — `SELECT 1` (2s), `redis.asyncio` ping (1s), `AsyncQdrantClient.get_collections` (3s) — via `asyncio.gather` (total ≈ slowest).
- Per-dep `healthy|degraded|unhealthy` + optional `latency_ms`/`checked_at`. Healthy iff all healthy; degraded iff only non-critical down (redis/qdrant have memory fallbacks); unhealthy iff critical (db) down.
- HTTP 200 for healthy/degraded; 503 ONLY for unhealthy. Keys unchanged (`status, version, database, redis, qdrant`).
- Version from single source `backend/__init__.py.__version__` (created; `main.py:61` references it).
- Module-level probe functions as zero-token monkeypatch seams.
- docker-compose: `QDRANT_URL=qdrant:6333` (code reads QDRANT_URL; compose sets unused QDRANT_HOST) + qdrant healthcheck (D-6 precedent).

### Out of Scope

- No `/ready` split or liveness endpoint; no renderer/publisher `/health`, frontend, auth, or retry/backoff changes.

## Capabilities

### New Capabilities

- `platform-health`: honest unified `/health` contract — real per-dep probes, `healthy|degraded|unhealthy`, HTTP 200/503 readiness, single-source version.

### Modified Capabilities

- None (no existing openspec spec references `/health`).

## Approach

Single slice, no chaining (~230–280 lines): `health.py` rewrite (~100) + `backend/__init__.py` (~5) + `main.py:61` edit + new `test_health_honesty.py` (~130) + extend `test_fase_0` (~10) + compose (~4). Sole consumer `test_enterprise_phases_0_to_5.py:23-31` asserts 200 + 4 keys — stays green (test env: no redis/qdrant → degraded → 200).

## Affected Areas

| Area | Impact | Change |
|------|--------|--------|
| `agency/backend/routers/health.py` | Modified | Honest async probes, per-dep status, version import |
| `agency/backend/__init__.py` | New | `__version__` single source |
| `agency/backend/main.py:61` | Modified | `version="1.0.0"` → `__version__` |
| `agency/tests/unit/test_health_honesty.py` | New | Seams, statuses, 503, timeouts |
| `agency/tests/unit/test_enterprise_phases_0_to_5.py:23-31` | Modified | Extend assertions (~10) |
| `agency/docker-compose.yml` | Modified | `QDRANT_URL=qdrant:6333` + healthcheck |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 503-on-degraded breaks unit test | Med | 503 only when critical (db) unhealthy |
| Sync-blocking probes | Med | Async clients + gather |
| Qdrant probe fails in-container | Med | `QDRANT_URL=qdrant:6333` in same slice |
| DB probe adds round-trip | Low | pool_pre_ping + pool 10; parallel gather |

## Rollback Plan

`git revert` the slice: restore `health.py`/`main.py:61`, delete `__init__.py` version + new test, remove compose env line. No destructive DDL; keys unchanged → old contract restores instantly.

## Dependencies

- redis-py 5.0.8 (`redis.asyncio`), qdrant-client 1.19.0 (`AsyncQdrantClient`), SQLAlchemy async engine — all present.

## Success Criteria

- [ ] `/health` probes db/redis/qdrant with timeouts, gathered; zero fake "healthy" assignments
- [ ] `healthy|degraded|unhealthy` semantics; 503 only when db unhealthy
- [ ] `version` from `backend.__version__`, never hardcoded
- [ ] baseline 297 passed / 1 skipped stays green

## Open Questions

1. Degraded HTTP code: **200** (503 breaks the only unit test in default env).
2. Sync vs async probes: **async** (no loop blocking; perf).
3. Compose QDRANT_URL fix: **yes** (probe honesty in-container).
4. Version source: **`backend/__init__.py.__version__`**.
