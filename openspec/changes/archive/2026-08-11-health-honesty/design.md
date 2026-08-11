# Design: Health Honesty

## Technical Approach

Rewrite `agency/backend/routers/health.py` (56 → ~100 lines): three module-level async probe functions (`check_database`, `check_redis`, `check_qdrant`) — the monkeypatch seams — each wrapping a real client call in `asyncio.wait_for` with per-dep timeout (db 2s, redis 1s, qdrant 3s), run via `asyncio.gather` (total ≈ slowest). Aggregation: `unhealthy` iff db (critical) down; else `degraded` iff any non-critical down; else `healthy`. HTTP 503 only on `unhealthy`; keys preserved. Version from new `backend/__init__.py.__version__`; compose gets `QDRANT_URL=qdrant:6333` + healthcheck. Single slice, ~250 lines.

## Architecture Decisions

### D-1 Probe structure + async clients
| Option | Tradeoff | Decision |
|---|---|---|
| Keep sync `redis.Redis` + fabricated qdrant | Blocks loop; REQ-PH-01 forbids fake healthy | Reject |
| `redis.asyncio.from_url` + `AsyncQdrantClient` | New imports only; existing sync users untouched (`sse_manager`, `llm_budget_service`, `rag_cache`, `rag_mcp_server`) | **Adopt** — no `asyncio.to_thread` |

`check_database`: `wait_for(conn.execute(text("SELECT 1")), 2)` on `async_engine` (from `backend.db.session`; FORCE_SQLITE → real SQLite `SELECT 1`). `check_redis`: lazy `import redis.asyncio` (existing pattern), `from_url(REDIS_URL)`, `wait_for(ping(), 1)`, `aclose()`. `check_qdrant`: lazy `from qdrant_client import AsyncQdrantClient` (1.19.0 top-level export), `wait_for(get_collections(), 3)`, `close()`. Any exception (incl. `TimeoutError`) → db `unhealthy`, redis/qdrant `degraded`. Timeout constants module-level env-overridable.

### D-2 Version single source
Create `backend/__init__.py` (~3 lines): `__version__ = "1.0.0"` (value at `main.py:61`). `main.py:61` → `version=__version__`; `health.py` response uses it too. No circularity: `__init__.py` imports nothing; package init finishes before `main`/`health` bodies run.

### D-3 Zero-token test seams
Primary seam: monkeypatch the three module-level probes → aggregation/HTTP/keys, no network. Timeout path (PH-01-5): patch client factories to hang — fake `health.async_engine` (execute sleeps), `redis.asyncio.Redis.from_url` (ping sleeps), `qdrant_client.AsyncQdrantClient` (get_collections sleeps) — then await the REAL probe: `wait_for` fires within cap → degraded/unhealthy. PH-04-1 (compose, not pytest-runnable) → config test asserting `QDRANT_URL=qdrant:6333` + qdrant `healthcheck:` via raw YAML text (no new deps).

### D-4 Compose fix
`QDRANT_URL=qdrant:6333` replaces unused `QDRANT_HOST` (`docker-compose.yml:96`); code reads only `QDRANT_URL` (default `http://localhost:6333`). Healthcheck — `qdrant/qdrant` (debian:13-slim) ships **bash but no curl/wget/nc**:
`test: ["CMD", "bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/6333 && echo -e 'GET /readyz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' >&3 && grep -q '200' <&3"]`
`/dev/tcp` is a bash builtin (no binary); `/readyz` 200 only when storage ready; `grep '200'` sidesteps HTTP/1.0-vs-1.1. Same slice as code (mirrors storage-honesty D-6).

### D-5 Consumers/regression (verified @ HEAD ae7a189)
Only consumer `test_enterprise_phases_0_to_5.py:23-31` (200 + 4 keys): default test env (conftest FORCE_SQLITE=true) → db healthy (SQLite), redis/qdrant refused → degraded → **200**, green. CI runs pytest only; renderer/publisher own separate `/health` (untouched); nothing infra consumes backend `/health`. `auth.py:167` already whitelists `/health` public.

### D-6 Rollback + work units
Single PR, one revert: restores `health.py`/`main.py:61`, deletes `__init__.py` + new test, drops compose lines. No DDL; keys unchanged → old contract instantly restored. Units (strict TDD, RED first): ① `test_health_honesty.py` (~130) + fase_0 extension (~10) → RED; ② `__init__.py` + `main.py:61` (PH-03); ③ `health.py` (PH-01/02); ④ compose (PH-04); ⑤ full suite green (297 passed / 1 skipped + new). ~250 < 400 budget → no chaining.

## Data Flow

    GET /health → gather(check_database, check_redis, check_qdrant)  [wait_for-capped]
      db     → SELECT 1 (2s)        → healthy | unhealthy
      redis  → asyncio ping (1s)    → healthy | degraded
      qdrant → get_collections (3s) → healthy | degraded
    → unhealthy iff db≠healthy; degraded iff any≠healthy; else healthy
    → HTTP 503 iff unhealthy else 200; body {status, version, database, redis, qdrant, latency_ms, checked_at}

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `agency/backend/routers/health.py` | Modify | Async probes, per-dep status, 503 semantics, version import |
| `agency/backend/__init__.py` | Create | `__version__ = "1.0.0"` single source |
| `agency/backend/main.py:61` | Modify | `version="1.0.0"` → `__version__` |
| `agency/tests/unit/test_health_honesty.py` | Create | ~130 lines: 10 pytest scenarios + compose-config test |
| `agency/tests/unit/test_enterprise_phases_0_to_5.py` | Modify | Extend `test_fase_0_unified_health_check_endpoint` (~10) |
| `agency/docker-compose.yml` | Modify | `QDRANT_URL=qdrant:6333`, qdrant healthcheck |

## Interfaces / Contracts

```python
# backend/__init__.py
__version__ = "1.0.0"

# backend/routers/health.py — module-level probe seams
async def check_database() -> str   # healthy|unhealthy (2s cap)
async def check_redis() -> str      # healthy|degraded  (1s cap)
async def check_qdrant() -> str     # healthy|degraded  (3s cap)
def aggregate_status(results: dict[str, str]) -> str  # healthy|degraded|unhealthy

# GET /health -> 200 | 503; body: status, version, database, redis, qdrant
# (preserved) + optional latency_ms, checked_at
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | PH-01-1..5 | Patch probes for statuses; hang client factories for timeout caps |
| Unit | PH-02-1..3 | Real aggregation + 200/503 via TestClient, patched probes |
| Unit | PH-03-1..2 | `health.__version__ == app.version == backend.__version__` |
| Config | PH-04-1 | Raw-text assertions on docker-compose.yml (`QDRANT_URL`, healthcheck) |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. In-app FastAPI route change only; the compose healthcheck is declarative config, not code we execute.

## Migration / Rollout

No migration. Single-slice PR; revert-safe per D-6.

## Open Questions

None blocking. Backend `depends_on: qdrant: service_started` could become `service_healthy` now a healthcheck exists — deliberately out of scope (keeps slice minimal).
