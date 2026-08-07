"""
metrics.py

Router para las Métricas de Rendimiento 72h y Clasificación RUM.
Conectado a SQLAlchemy Async ORM — devuelve datos reales del tenant autenticado.
Ante error de DB devuelve 503 explícito. Sin datos devuelve lista vacía.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends

logger = logging.getLogger(__name__)

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import VideoMetric
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    get_async_db = lambda: None

router = APIRouter(prefix="/api/v1/tenants", tags=["Metrics 72h"])


@router.get("/{tenant_id}/metrics")
async def get_metrics(
    tenant_id: str, db=Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """
    Retorna la lista de métricas por video para el tenant autenticado.
    Consulta VideoMetric desde el ORM async. Sin DB → lista vacía. Error → 503.
    """
    if not HAS_SQLALCHEMY or db is None:
        return []

    try:
        stmt = select(VideoMetric).where(VideoMetric.tenant_id == tenant_id)
        result = await db.execute(stmt)
        metrics_orm = result.scalars().all()
        return [
            {
                "video_id": m.video_id,
                "published_at": m.published_at.isoformat() if m.published_at else None,
                "metrics_72h": {
                    "views": m.views,
                    "followers_at_posting": m.followers_at_posting,
                    "ratio": round(m.views / m.followers_at_posting, 2)
                    if m.followers_at_posting
                    else 0.0,
                    "leads_generated": m.leads_generated,
                },
                "classification": m.classification,
                "action_taken": m.action_taken,
            }
            for m in metrics_orm
        ]
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error al consultar métricas en DB: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al obtener métricas.",
        )


@router.get("/{tenant_id}/metrics/72h")
async def get_metrics_72h(
    tenant_id: str, db=Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Retorna el resumen consolidado de métricas en la ventana de 72 horas.
    Agrega desde el ORM los videos publicados en las últimas 72h.
    Sin datos → {"status": "no_data"}. Error → 503.
    """
    if not HAS_SQLALCHEMY or db is None:
        return {"status": "no_data", "tenant_id": tenant_id, "window_hours": 72, "metrics": {}}

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
        stmt = (
            select(VideoMetric)
            .where(VideoMetric.tenant_id == tenant_id)
            .where(VideoMetric.published_at >= cutoff)
        )
        result = await db.execute(stmt)
        metrics_orm = result.scalars().all()

        if not metrics_orm:
            return {
                "status": "no_data",
                "tenant_id": tenant_id,
                "window_hours": 72,
                "metrics": {},
            }

        total_views = sum(m.views for m in metrics_orm)
        total_leads = sum(m.leads_generated for m in metrics_orm)
        avg_completion = (
            sum(m.completion_rate for m in metrics_orm if m.completion_rate) / len(metrics_orm)
            if metrics_orm
            else 0.0
        )
        avg_engagement = (
            sum(m.engagement_rate for m in metrics_orm if m.engagement_rate) / len(metrics_orm)
            if metrics_orm
            else 0.0
        )
        # Clasificación simple basada en ratio de views/leads: VIRAL si >10x
        classification = "VIRAL_WINNER" if total_views > 0 and total_leads / max(total_views, 1) > 0.001 else "VERDE"

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "window_hours": 72,
            "metrics": {
                "total_views": total_views,
                "total_leads": total_leads,
                "avg_completion_rate": round(avg_completion, 3),
                "avg_engagement_rate": round(avg_engagement, 4),
                "classification": classification,
                "videos_analyzed": len(metrics_orm),
            },
        }
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error al consolidar métricas 72h en DB: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al consolidar métricas 72h.",
        )
