"""
metrics.py

Router para las Métricas de Rendimiento 72h y Clasificación RUM.
Conectado a SQLAlchemy Async ORM — devuelve datos reales del tenant autenticado.

Contrato (REQ-API-4 / diseñ D4):
- GET /{tenant_id}/metrics → lista plana alineada con la DDL 002:
  [{video_id, views_72h, likes, comments, shares, ratio_relativo,
    classification, action_taken, captured_at}] — sin key anidada metrics_72h.
- GET /{tenant_id}/metrics/72h → agregado sobre la ventana de 72h filtrada por
  captured_at (la DDL 002 no tiene published_at):
  {status: success|no_data, tenant_id, window_hours: 72, metrics: {...}}.

Ante error de DB devuelve 503 explícito. Sin datos devuelve lista vacía /
{status: "no_data"} — nunca datos fabricados.
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

# Clases de clasificación 80/20 — espejo del CHECK (ROJO/AMARILLO/VERDE) de la DDL 002.
CLASSIFICATIONS = ("ROJO", "AMARILLO", "VERDE")


def _metric_to_flat_dict(m) -> Dict[str, Any]:
    """Proyección plana de una fila VideoMetric al contrato de la DDL 002."""
    return {
        "video_id": m.video_id,
        "views_72h": m.views_72h,
        "likes": m.likes,
        "comments": m.comments,
        "shares": m.shares,
        "ratio_relativo": float(m.ratio_relativo) if m.ratio_relativo is not None else None,
        "classification": m.classification,
        "action_taken": m.action_taken,
        "captured_at": m.captured_at.isoformat() if m.captured_at else None,
    }


@router.get("/{tenant_id}/metrics")
async def get_metrics(
    tenant_id: str, db=Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """
    Retorna la lista de métricas por video para el tenant autenticado.
    Consulta VideoMetric desde el ORM async. Sin datos → lista vacía. Error de DB → 503.
    """
    if not HAS_SQLALCHEMY or db is None:
        return []

    try:
        result = await db.execute(
            select(VideoMetric).where(VideoMetric.tenant_id == tenant_id)
        )
        metrics_orm = result.scalars().all()
        return [_metric_to_flat_dict(m) for m in metrics_orm]
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
    Agrega desde el ORM los videos con captured_at dentro de las últimas 72h
    (la DDL 002 no tiene published_at). Sin datos → {"status": "no_data"}. Error → 503.
    """
    if not HAS_SQLALCHEMY or db is None:
        return {"status": "no_data", "tenant_id": tenant_id, "window_hours": 72, "metrics": {}}

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
        result = await db.execute(
            select(VideoMetric)
            .where(VideoMetric.tenant_id == tenant_id)
            .where(VideoMetric.captured_at >= cutoff)
        )
        metrics_orm = result.scalars().all()

        no_data = {
            "status": "no_data",
            "tenant_id": tenant_id,
            "window_hours": 72,
            "metrics": {},
        }
        if not metrics_orm:
            return no_data

        total_views = sum(m.views_72h or 0 for m in metrics_orm)
        total_likes = sum(m.likes or 0 for m in metrics_orm)
        total_comments = sum(m.comments or 0 for m in metrics_orm)
        total_shares = sum(m.shares or 0 for m in metrics_orm)

        ratios = [float(m.ratio_relativo) for m in metrics_orm if m.ratio_relativo is not None]
        avg_ratio_relativo = round(sum(ratios) / len(ratios), 3) if ratios else None

        classification_distribution = {
            label: sum(1 for m in metrics_orm if (m.classification or "").upper() == label)
            for label in CLASSIFICATIONS
        }

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "window_hours": 72,
            "metrics": {
                "total_views": total_views,
                "total_likes": total_likes,
                "total_comments": total_comments,
                "total_shares": total_shares,
                "avg_ratio_relativo": avg_ratio_relativo,
                "videos_analyzed": len(metrics_orm),
                "classification_distribution": classification_distribution,
            },
        }
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error al consolidar métricas 72h en DB: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al consolidar métricas 72h.",
        )