"""
test_health_honesty.py

RED contract tests for the health-honesty change (REQ-PH-01..04).

Covers the 11 scenarios of the platform-health capability:
  PH-01-1..5 honest per-dependency probes with per-probe timeout caps,
  PH-02-1..3 truthful aggregation with 503-only-on-database-failure,
  PH-03-1..2 version from the single source backend.__version__,
  PH-04-1   compose Qdrant reachability (QDRANT_URL + healthcheck).

Zero-token only: probes are monkeypatched module-level seams or hang-factory
fakes; the compose check reads the raw YAML text (no docker, no network).
"""

import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import __version__ as backend_version
from backend import backend as backend_pkg
from backend.routers import health
from backend.main import app

client = TestClient(app)


async def _healthy_probe() -> str:
    return "healthy"


async def _unhealthy_db() -> str:
    return "unhealthy"


async def _degraded_redis() -> str:
    return "degraded"


async def _degraded_qdrant() -> str:
    return "degraded"


# --------------------------------------------------------------------------- #
# REQ-PH-01 — honest per-dependency probes
# --------------------------------------------------------------------------- #
def test_all_dependencies_healthy_reports_healthy(monkeypatch):
    """PH-01-1: every probe is actually invoked and reports healthy."""
    called = {"db": 0, "redis": 0, "qdrant": 0}

    async def db_probe():
        called["db"] += 1
        return "healthy"

    async def redis_probe():
        called["redis"] += 1
        return "healthy"

    async def qdrant_probe():
        called["qdrant"] += 1
        return "healthy"

    monkeypatch.setattr(health, "check_database", db_probe)
    monkeypatch.setattr(health, "check_redis", redis_probe)
    monkeypatch.setattr(health, "check_qdrant", qdrant_probe)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert data["redis"] == "healthy"
    assert data["qdrant"] == "healthy"
    # No fabricated assignments: each probe ran exactly once.
    assert called == {"db": 1, "redis": 1, "qdrant": 1}


def test_database_down_reports_unhealthy(monkeypatch):
    """PH-01-2: a failing database probe reports unhealthy."""
    monkeypatch.setattr(health, "check_database", lambda: _unhealthy_db())
    monkeypatch.setattr(health, "check_redis", _healthy_probe)
    monkeypatch.setattr(health, "check_qdrant", _healthy_probe)

    response = client.get("/health")

    assert response.json()["database"] == "unhealthy"
    assert response.json()["status"] == "unhealthy"


def test_redis_down_reports_degraded(monkeypatch):
    """PH-01-3: a failing Redis probe reports degraded (non-critical)."""
    monkeypatch.setattr(health, "check_database", _healthy_probe)
    monkeypatch.setattr(health, "check_redis", lambda: _degraded_redis())
    monkeypatch.setattr(health, "check_qdrant", _healthy_probe)

    response = client.get("/health")

    assert response.json()["redis"] == "degraded"
    assert response.json()["status"] == "degraded"


async def _degraded_redis() -> str:
    return "degraded"


def test_qdrant_down_reports_degraded(monkeypatch):
    """PH-01-4: a failing Qdrant probe reports degraded (non-critical)."""
    monkeypatch.setattr(health, "check_database", _healthy_probe)
    monkeypatch.setattr(health, "check_redis", _healthy_probe)
    monkeypatch.setattr(health, "check_qdrant", lambda: _degraded_qdrant())

    response = client.get("/health")

    assert response.json()["qdrant"] == "degraded"
    assert response.json()["status"] == "degraded"


async def _degraded_qdrant() -> str:
    return "degraded"


class _HangingConnection:
    """Fake SQLAlchemy connection whose execute() never answers."""

    async def execute(self, *args, **kwargs):
        await asyncio.sleep(3600)
        return None


class _HangingEngine:
    """Fake engine: connect() yields a hanging connection."""

    def connect(self):
        return _HangingContext()


class _HangingContext:
    async def __aenter__(self):
        return _HangingConnection()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _HangingRedis:
    """Fake Redis client whose ping() never answers."""

    async def ping(self):
        await asyncio.sleep(3600)

    async def aclose(self):
        return None


class _HangingQdrant:
    """Fake AsyncQdrantClient whose get_collections() never answers."""

    def __init__(self, *args, **kwargs):
        pass

    async def get_collections(self):
        await asyncio.sleep(3600)

    async def close(self):
        return None


@pytest.mark.anyio
async def test_timeout_caps_probe_no_hang(monkeypatch):
    """PH-01-5: a dependency that never answers resolves within its cap.

    Hang-factory fakes replace the client factories, then the REAL module-
    level probes are awaited: asyncio.wait_for must fire within each cap and
    the probe must resolve as degraded/unhealthy instead of hanging.
    """
    import redis.asyncio as redis_async
    import qdrant_client

    monkeypatch.setattr(health, "async_engine", _HangingEngine())
    monkeypatch.setattr(
        redis_async.Redis, "from_url", staticmethod(lambda url: _HangingRedis())
    )
    monkeypatch.setattr(qdrant_client, "AsyncQdrantClient", _HangingQdrant)

    started = time.monotonic()
    db_status = await health.check_database()
    db_elapsed = time.monotonic() - started

    started = time.monotonic()
    redis_status = await health.check_redis()
    redis_elapsed = time.monotonic() - started

    started = time.monotonic()
    qdrant_status = await health.check_qdrant()
    qdrant_elapsed = time.monotonic() - started

    assert db_status == "unhealthy"
    assert redis_status == "degraded"
    assert qdrant_status == "degraded"
    assert db_elapsed < 5.0  # db cap 2s + slack
    assert redis_elapsed < 3.5  # redis cap 1s + slack
    assert qdrant_elapsed < 6.5  # qdrant cap 3s + slack


# --------------------------------------------------------------------------- #
# REQ-PH-02 — honest aggregation + HTTP semantics
# --------------------------------------------------------------------------- #
def test_healthy_returns_200_with_all_keys_and_latency(monkeypatch):
    """PH-02-1: healthy returns 200 with all contract keys plus latency info."""
    monkeypatch.setattr(health, "check_database", _healthy_probe)
    monkeypatch.setattr(health, "check_redis", _healthy_probe)
    monkeypatch.setattr(health, "check_qdrant", _healthy_probe)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    for key in ("status", "version", "database", "redis", "qdrant"):
        assert key in data
    assert data["status"] == "healthy"
    assert isinstance(data.get("latency_ms"), (int, float))
    assert isinstance(data.get("checked_at"), str)


def test_database_down_returns_503_unhealthy(monkeypatch):
    """PH-02-2: database down returns HTTP 503 with overall unhealthy."""
    monkeypatch.setattr(health, "check_database", lambda: _unhealthy_db())
    monkeypatch.setattr(health, "check_redis", _healthy_probe)
    monkeypatch.setattr(health, "check_qdrant", _healthy_probe)

    response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "unhealthy"


def test_only_noncritical_down_returns_200_degraded(monkeypatch):
    """PH-02-3: only redis/qdrant down keeps HTTP 200 with status degraded."""
    monkeypatch.setattr(health, "check_database", _healthy_probe)
    monkeypatch.setattr(health, "check_redis", lambda: _degraded_redis())
    monkeypatch.setattr(health, "check_qdrant", lambda: _degraded_qdrant())

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] == "degraded"
    assert data["qdrant"] == "degraded"


# --------------------------------------------------------------------------- #
# REQ-PH-03 — version from a single source
# --------------------------------------------------------------------------- #
def test_health_version_matches_app_and_backend_version():
    """PH-03-1: health version == app version == backend.__version__."""
    response = client.get("/health")
    data = response.json()

    assert data["version"] == backend_version
    assert app.version == backend_version
    assert data["version"] == app.version


def test_version_change_propagates_without_hardcode(monkeypatch):
    """PH-03-2: bumping backend.__version__ propagates to /health.

    If the response version were hardcoded (or bound at import time), the
    monkeypatched value would not appear in the response.
    """
    monkeypatch.setattr(backend_pkg, "__version__", "9.9.9")

    response = client.get("/health")

    assert response.json()["version"] == "9.9.9"


# --------------------------------------------------------------------------- #
# REQ-PH-04 — compose honesty: probe reachability in-container
# --------------------------------------------------------------------------- #
def test_compose_qdrant_url_reaches_service():
    """PH-04-1: compose backend env points the Qdrant probe at qdrant:6333.

    Raw YAML text assertions (no docker): the backend service env provides
    QDRANT_URL=qdrant:6333 (replacing the unused QDRANT_HOST) and the qdrant
    service declares a bash /dev/tcp healthcheck against /readyz.
    """
    compose_path = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    text = compose_path.read_text(encoding="utf-8")

    assert "- QDRANT_URL=qdrant:6333" in text
    assert "- QDRANT_HOST=qdrant" not in text
    assert "/dev/tcp/127.0.0.1/6333" in text
    assert "/readyz" in text
    assert "image: qdrant/qdrant" in text
