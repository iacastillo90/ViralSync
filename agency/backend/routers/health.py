"""
health.py

Unified platform health check endpoint with honest per-dependency probes.

Each dependency (PostgreSQL/SQLite via the async SQLAlchemy engine, Redis via
redis.asyncio, Qdrant via AsyncQdrantClient) is probed with a real call capped
by asyncio.wait_for and gathered in parallel, so a green status means the
dependency really answered and the endpoint never hangs past the slowest cap.

Aggregation (REQ-PH-02): unhealthy iff the critical dependency (database) is
down; degraded iff only non-critical dependencies (redis/qdrant) are down;
healthy otherwise. HTTP 503 is returned only for unhealthy, 200 otherwise.
Version comes from the single source backend.__version__ (REQ-PH-03).
"""

import os
import asyncio
import time
from datetime import datetime, timezone

import backend
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from backend.db.session import async_engine

router = APIRouter(tags=["Health Check"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

# Per-probe timeout caps (seconds), env-overridable so operators can tune them.
DATABASE_TIMEOUT_SECONDS = float(os.getenv("HEALTH_DATABASE_TIMEOUT", "2"))
REDIS_TIMEOUT_SECONDS = float(os.getenv("HEALTH_REDIS_TIMEOUT", "1"))
QDRANT_TIMEOUT_SECONDS = float(os.getenv("HEALTH_QDRANT_TIMEOUT", "3"))


class HealthStatusResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    qdrant: str
    latency_ms: float | None = None
    checked_at: str | None = None


async def check_database() -> str:
    """Probe the database with a real SELECT 1, capped at the db timeout."""
    try:
        async with async_engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), DATABASE_TIMEOUT_SECONDS)
        return "healthy"
    except Exception:
        return "unhealthy"


async def check_redis() -> str:
    """Probe Redis with a real async ping, capped at the redis timeout."""
    try:
        import redis.asyncio as redis_async

        client = redis_async.Redis.from_url(REDIS_URL)
        try:
            await asyncio.wait_for(client.ping(), REDIS_TIMEOUT_SECONDS)
            return "healthy"
        finally:
            await client.aclose()
    except Exception:
        return "degraded"


async def check_qdrant() -> str:
    """Probe Qdrant with a real get_collections call, capped at the qdrant timeout."""
    try:
        from qdrant_client import AsyncQdrantClient

        client = AsyncQdrantClient(url=QDRANT_URL)
        try:
            await asyncio.wait_for(client.get_collections(), QDRANT_TIMEOUT_SECONDS)
            return "healthy"
        finally:
            await client.close()
    except Exception:
        return "degraded"


def aggregate_status(results: dict[str, str]) -> str:
    """Aggregate per-dependency statuses into healthy|degraded|unhealthy.

    The database is the critical dependency: any failure there is unhealthy.
    Non-critical dependencies (redis/qdrant) degrade the overall status but
    do not make the platform unhealthy.
    """
    if results.get("database") != "healthy":
        return "unhealthy"
    if any(v != "healthy" for dep, v in results.items() if dep != "database"):
        return "degraded"
    return "healthy"


@router.get("/health", response_model=HealthStatusResponse, status_code=status.HTTP_200_OK)
async def unified_health_check():
    """Run all probes in parallel and report the truthful aggregate status."""
    started = time.monotonic()
    database, redis_status, qdrant_status = await asyncio.gather(
        check_database(), check_redis(), check_qdrant()
    )
    overall_status = aggregate_status(
        {"database": database, "redis": redis_status, "qdrant": qdrant_status}
    )
    payload = {
        "status": overall_status,
        "version": backend.__version__,
        "database": database,
        "redis": redis_status,
        "qdrant": qdrant_status,
        "latency_ms": round((time.monotonic() - started) * 1000, 1),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if overall_status == "unhealthy":
        return JSONResponse(content=payload, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return payload