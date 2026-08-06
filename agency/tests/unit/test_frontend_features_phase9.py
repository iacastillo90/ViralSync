"""
test_frontend_features_phase9.py

Pruebas unitarias para validar los módulos DDD de la Fase 9 (Pipeline, Ideación, Guionismo).
"""

import os


def test_phase9_feature_files_exist():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
    
    pipeline_view = os.path.join(base_dir, "features", "Pipeline", "views", "PipelineMonitorView.jsx")
    ideation_chart = os.path.join(base_dir, "features", "Ideation", "components", "RUMBreakdownBarChart.jsx")
    ideation_view = os.path.join(base_dir, "features", "Ideation", "views", "IdeaApprovalView.jsx")
    script_reader = os.path.join(base_dir, "features", "Scriptwriting", "components", "Script4BlockReader.jsx")
    script_view = os.path.join(base_dir, "features", "Scriptwriting", "views", "ScriptInspectorView.jsx")
    
    assert os.path.exists(pipeline_view)
    assert os.path.exists(ideation_chart)
    assert os.path.exists(ideation_view)
    assert os.path.exists(script_reader)
    assert os.path.exists(script_view)
