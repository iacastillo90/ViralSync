"""
test_health_honesty.py

RED contract tests for health-honesty (REQ-PH-01..04): honest per-dependency
probes with timeout caps (PH-01-1..5), truthful aggregation with 503-only-on-
db-failure (PH-02-1..3), single-source version (PH-03-1..2), compose Qdrant
reachability (PH-04-1). Zero-token: probes are monkeypatched seams or
hang-factory fakes; compose is asserted as raw YAML text.
"""

import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend as backend_pkg
from backend import __version__ as backend_version
from backend.main import app
from backend.routers import health

client = TestClient(app)


async def _probe(status: str) -> str:
    return status


def _patch_probes(monkeypatch, db="healthy", redis="healthy", qdrant="healthy"):
    monkeypatch.setattr(health, "check_database", lambda: _probe(db))
    monkeypatch.setattr(health, "check_redis", lambda: _probe(redis))
    monkeypatch.setattr(health, "check_qdrant", lambda: _probe(qdrant))


def test_all_dependencies_healthy_reports_healthy(monkeypatch):
    """PH-01-1: every probe is actually invoked and reports healthy."""
    called = {"db": 0, "redis": 0, "qdrant": 0}

    async def counting(key):
        called[key] += 1
        return "healthy"

    monkeypatch.setattr(health, "check_database", lambda: counting("db"))
    monkeypatch.setattr(health, "check_redis", lambda: counting("redis"))
    monkeypatch.setattr(health, "check_qdrant", lambda: counting("qdrant"))

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == data["database"] == data["redis"] == data["qdrant"] == "healthy"
    assert called == {"db": 1, "redis": 1, "qdrant": 1}  # no fabricated assignments


def test_database_down_reports_unhealthy(monkeypatch):
    """PH-01-2: a failing database probe reports unhealthy."""
    _patch_probes(monkeypatch, db="unhealthy")
    data = client.get("/health").json()
    assert data["database"] == "unhealthy"
    assert data["status"] == "unhealthy"


def test_redis_down_reports_degraded(monkeypatch):
    """PH-01-3: a failing Redis probe reports degraded (non-critical)."""
    _patch_probes(monkeypatch, redis="degraded")
    data = client.get("/health").json()
    assert data["redis"] == "degraded"
    assert data["status"] == "degraded"


def test_qdrant_down_reports_degraded(monkeypatch):
    """PH-01-4: a failing Qdrant probe reports degraded (non-critical)."""
    _patch_probes(monkeypatch, qdrant="degraded")
    data = client.get("/health").json()
    assert data["qdrant"] == "degraded"
    assert data["status"] == "degraded"


class _HangingConnection:
    async def execute(self, *args, **kwargs):
        await asyncio.sleep(3600)


class _HangingContext:
    async def __aenter__(self):
        return _HangingConnection()

    async def __aexit__(self, *exc):
        return False


class _HangingEngine:
    def connect(self):
        return _HangingContext()


class _HangingRedis:
    async def ping(self):
        await asyncio.sleep(3600)

    async def aclose(self):
        pass


class _HangingQdrant:
    def __init__(self, *args, **kwargs):
        pass

    async def get_collections(self):
        await asyncio.sleep(3600)

    async def close(self):
        pass


@pytest.mark.anyio
async def test_timeout_caps_probe_no_hang(monkeypatch):
    """PH-01-5: a dependency that never answers resolves within its cap.

    Hang-factory fakes replace the client factories, then the REAL module-level
    probes are awaited: asyncio.wait_for fires within each cap and the probe
    resolves as degraded/unhealthy instead of hanging.
    """
    import redis.asyncio as redis_async
    import qdrant_client

    monkeypatch.setattr(health, "async_engine", _HangingEngine())
    monkeypatch.setattr(redis_async.Redis, "from_url", staticmethod(lambda url: _HangingRedis()))
    monkeypatch.setattr(qdrant_client, "AsyncQdrantClient", _HangingQdrant)

    started = time.monotonic()
    db = await health.check_database()
    db_t = time.monotonic() - started
    started = time.monotonic()
    redis = await health.check_redis()
    redis_t = time.monotonic() - started
    started = time.monotonic()
    qdrant = await health.check_qdrant()
    qdrant_t = time.monotonic() - started

    assert db == "unhealthy" and redis == "degraded" and qdrant == "degraded"
    assert db_t < 5.0 and redis_t < 3.5 and qdrant_t < 6.5  # caps: 2s/1s/3s


def test_healthy_returns_200_with_all_keys_and_latency(monkeypatch):
    """PH-02-1: healthy returns 200 with all contract keys plus latency info."""
    _patch_probes(monkeypatch)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    for key in ("status", "version", "database", "redis", "qdrant"):
        assert key in data
    assert isinstance(data.get("latency_ms"), (int, float))
    assert isinstance(data.get("checked_at"), str)


def test_database_down_returns_503_unhealthy(monkeypatch):
    """PH-02-2: database down returns HTTP 503 with overall unhealthy."""
    _patch_probes(monkeypatch, db="unhealthy")
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy" and data["database"] == "unhealthy"


def test_only_noncritical_down_returns_200_degraded(monkeypatch):
    """PH-02-3: only redis/qdrant down keeps HTTP 200 with status degraded."""
    _patch_probes(monkeypatch, redis="degraded", qdrant="degraded")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] == "degraded" and data["qdrant"] == "degraded"


def test_health_version_matches_app_and_backend_version():
    """PH-03-1: health version == app version == backend.__version__."""
    data = client.get("/health").json()
    assert data["version"] == backend_version == app.version


def test_version_change_propagates_without_hardcode(monkeypatch):
    """PH-03-2: bumping backend.__version__ propagates to /health.

    If the response version were hardcoded (or bound at import time), the
    monkeypatched value would not appear in the response.
    """
    monkeypatch.setattr(backend_pkg, "__version__", "9.9.9")
    assert client.get("/health").json()["version"] == "9.9.9"


def test_compose_qdrant_url_reaches_service():
    """PH-04-1: compose backend env points the Qdrant probe at qdrant:6333."""
    text = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text()
    assert "- QDRANT_URL=qdrant:6333" in text
    assert "- QDRANT_HOST=qdrant" not in text
    assert "/dev/tcp/127.0.0.1/6333" in text and "/readyz" in text
    assert "image: qdrant/qdrant" in text
