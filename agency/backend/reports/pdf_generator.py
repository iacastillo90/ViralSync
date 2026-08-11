"""
pdf_generator.py

Servicio de Generación de Reportes Ejecutivos PDF de ROI y Métricas RUM a 72h.
Produce un reporte en formato PDF/dict estructurado para descarga desde la API REST.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)


def generate_tenant_roi_pdf_report(tenant_id: str, metrics_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Genera la estructura de datos y metadatos del reporte ejecutivo en PDF para el tenant."""
    logger.info(f"[{tenant_id}] Generando reporte ejecutivo en PDF...")

    metrics = metrics_summary.get("metrics", {})
    distribution = metrics.get("classification_distribution", {"ROJO": 0, "AMARILLO": 0, "VERDE": 0})

    report_metadata = {
        "title": f"Reporte de Rendimiento ViralSync - Tenant {tenant_id}",
        "tenant_id": tenant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_views": metrics.get("total_views", 0),
            "videos_analyzed": metrics.get("videos_analyzed", 0),
            "avg_ratio_relativo": metrics.get("avg_ratio_relativo", 1.0),
            "distribution": distribution,
        },
        "content_type": "application/pdf",
        "filename": f"viralsync_report_{tenant_id}.pdf",
    }

    return report_metadata
