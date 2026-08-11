"""
test_sprint1_frontend_batch.py

Pruebas unitarias de contrato (TDD) para el Sprint 1: Integración Frontend Realtime y Batch Ingest.
"""

from pathlib import Path


def test_live_activity_feed_component_exists():
    """REQ-FE-01: El componente LiveActivityFeed.jsx existe en frontend/src/components."""
    component_path = Path(__file__).parents[2] / "frontend" / "src" / "components" / "LiveActivityFeed.jsx"
    assert component_path.exists(), "LiveActivityFeed.jsx debe existir"


def test_batch_ingest_view_exists():
    """REQ-FE-02: La vista BatchIngestView.jsx existe en frontend/src/features/Ingestion/views."""
    view_path = Path(__file__).parents[2] / "frontend" / "src" / "features" / "Ingestion" / "views" / "BatchIngestView.jsx"
    assert view_path.exists(), "BatchIngestView.jsx debe existir"
