"""
metrics.py

Router para las Métricas de Rendimiento 72h y Clasificación RUM.
"""

from typing import List, Dict, Any
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/tenants", tags=["Metrics 72h"])


@router.get("/{tenant_id}/metrics")
async def get_metrics(tenant_id: str) -> List[Dict[str, Any]]:
    """Retorna la lista de métricas por video a 72 horas para clasificación RUM."""
    return [
        {
            "video_id": "video-55",
            "published_at": "2026-08-03T10:00:00Z",
            "metrics_72h": {
                "views": 150000,
                "followers_at_posting": 10000,
                "ratio": 15.0,
                "leads_generated": 142,
            },
            "classification": "VERDE",
            "action_taken": "Encolado para 3 variaciones en próximo batch.",
        },
        {
            "video_id": "video-56",
            "published_at": "2026-08-03T14:00:00Z",
            "metrics_72h": {
                "views": 4500,
                "followers_at_posting": 10000,
                "ratio": 0.45,
                "leads_generated": 2,
            },
            "classification": "ROJO",
            "action_taken": "Idea descartada.",
        },
    ]


@router.get("/{tenant_id}/metrics/72h")
async def get_metrics_72h(tenant_id: str) -> Dict[str, Any]:
    """Retorna el resumen consolidado a 72 horas."""
    return {
        "status": "success",
        "tenant_id": tenant_id,
        "window_hours": 72,
        "metrics": {
            "total_views": 14500,
            "avg_watch_time": 38.5,
            "completion_rate": 0.68,
            "engagement_rate": 0.084,
            "classification": "VIRAL_WINNER",
            "rum_adjustment_delta": +0.05,
        },
    }
