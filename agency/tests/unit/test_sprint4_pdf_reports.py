"""
test_sprint4_pdf_reports.py

Pruebas unitarias de contrato (TDD) para el Sprint 4: Generador de Reportes de ROI & Métricas RUM en PDF.
"""

from backend.reports.pdf_generator import generate_tenant_roi_pdf_report


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
