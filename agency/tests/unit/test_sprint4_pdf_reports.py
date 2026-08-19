"""
test_sprint4_pdf_reports.py

Pruebas unitarias para el Generador de Reportes de ROI & Métricas RUM en PDF binario real (ReportLab).
"""

import asyncio
from backend.reports.pdf_generator import generate_tenant_roi_pdf_report, build_tenant_pdf_bytes


def test_generate_tenant_roi_pdf_report():
    """REQ-REP-01: Generación de metadatos de reporte PDF para el tenant."""
    metrics_summary = {
        "status": "success",
        "tenant_id": "tenant_pdf_test",
        "window_hours": 72,
        "metrics": {
            "total_views": 15000,
            "videos_analyzed": 5,
            "avg_ratio_relativo": 3.4,
            "classification_distribution": {"ROJO": 0, "AMARILLO": 2, "VERDE": 3},
        },
    }
    report = generate_tenant_roi_pdf_report("tenant_pdf_test", metrics_summary)
    assert report["tenant_id"] == "tenant_pdf_test"
    assert report["content_type"] == "application/pdf"
    assert report["summary"]["total_views"] == 15000
    assert report["summary"]["distribution"]["VERDE"] == 3


def test_build_tenant_pdf_bytes():
    """REQ-REP-01: Generación de flujo binario PDF (%PDF-1.4) con ReportLab."""
    metrics_summary = {
        "status": "success",
        "tenant_id": "tenant_pdf_binary_test",
        "window_hours": 72,
        "metrics": {
            "total_views": 45000,
            "total_likes": 3200,
            "total_comments": 480,
            "total_shares": 150,
            "videos_analyzed": 8,
            "avg_ratio_relativo": 4.2,
            "classification_distribution": {"ROJO": 1, "AMARILLO": 2, "VERDE": 5},
        },
    }
    pdf_bytes = build_tenant_pdf_bytes("tenant_pdf_binary_test", metrics_summary)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF-1.4")
