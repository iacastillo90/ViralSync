"""
test_frontend_features_phase10.py

Pruebas unitarias para validar los módulos DDD de la Fase 10 (VideoPreview, LeadsInbound, Metrics72h).
"""

import os


def test_phase10_feature_files_exist():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
    
    publish_view = os.path.join(base_dir, "features", "VideoPreview", "views", "PublishApprovalView.jsx")
    leads_table = os.path.join(base_dir, "features", "LeadsInbound", "components", "LeadsTable.jsx")
    leads_view = os.path.join(base_dir, "features", "LeadsInbound", "views", "InboundLeadsView.jsx")
    metrics_card = os.path.join(base_dir, "features", "Metrics72h", "components", "MetricClassificationCard.jsx")
    metrics_view = os.path.join(base_dir, "features", "Metrics72h", "views", "MetricsDashboardView.jsx")
    
    assert os.path.exists(publish_view)
    assert os.path.exists(leads_table)
    assert os.path.exists(leads_view)
    assert os.path.exists(metrics_card)
    assert os.path.exists(metrics_view)
