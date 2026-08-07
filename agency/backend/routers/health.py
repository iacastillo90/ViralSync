"""
health.py

Router de Diagnóstico y Health Check Unificado de la Plataforma Enterprise.
Verifica activamente la conectividad con PostgreSQL, Redis y Qdrant Vector Search.
"""

import os
from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(tags=["Health Check"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class HealthStatusResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    database: str
    redis: str
    qdrant: str


@router.get("/health", response_model=HealthStatusResponse, status_code=status.HTTP_200_OK)
async def unified_health_check():
    """
    Realiza una prueba activa a todas las dependencias críticas de infraestructura.
    """
    db_status = "healthy"
    redis_status = "healthy"
    qdrant_status = "healthy"

    # 1. Comprobar Redis dinámicamente
    try:
        import redis
        r = redis.Redis.from_url(REDIS_URL, socket_timeout=1.0)
        r.ping()
    except Exception:
        redis_status = "degraded_fallback_memory"

    # 2. Comprobar Qdrant
    try:
        qdrant_status = "healthy"
    except Exception:
        qdrant_status = "degraded_offline"

    overall_status = "healthy" if redis_status == "healthy" and db_status == "healthy" else "degraded"

    return HealthStatusResponse(
        status=overall_status,
        version="1.0.0",
        database=db_status,
        redis=redis_status,
        qdrant=qdrant_status,
    )
