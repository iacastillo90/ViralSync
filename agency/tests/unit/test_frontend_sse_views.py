"""
test_frontend_sse_views.py

Pruebas unitarias de contrato (TDD) para la Fase 1: Integración SSE en Vistas de Pipeline e Inbound Leads.
"""

from pathlib import Path


def test_pipeline_monitor_view_exists():
    """REQ-FE-03: PipelineMonitorView.jsx existe en frontend/src/features/Pipeline/views."""
    view_path = Path(__file__).parents[2] / "frontend" / "src" / "features" / "Pipeline" / "views" / "PipelineMonitorView.jsx"
    assert view_path.exists(), "PipelineMonitorView.jsx debe existir"
    content = view_path.read_text(encoding="utf-8")
    assert "useSSEStream" in content


def test_inbound_leads_view_exists_with_sse():
    """REQ-FE-04: InboundLeadsView.jsx escucha eventos SSE lead_captured."""
    view_path = Path(__file__).parents[2] / "frontend" / "src" / "features" / "LeadsInbound" / "views" / "InboundLeadsView.jsx"
    assert view_path.exists(), "InboundLeadsView.jsx debe existir"
    content = view_path.read_text(encoding="utf-8")
    assert "EventSource" in content
    assert "lead_captured" in content
