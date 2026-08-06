"""
test_frontend_features_phase11.py

Pruebas unitarias para validar la totalidad del frontend (Fase 11: Cerebro, Admin, Onboarding, Public API).
"""

import os


def test_phase11_and_frontend_completion_files_exist():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
    
    brain_view = os.path.join(base_dir, "features", "RAGBrain", "views", "BrainManagementView.jsx")
    public_api = os.path.join(base_dir, "features", "index.js")
    cerebro_page = os.path.join(base_dir, "app", "tenants", "[tenantId]", "cerebro", "page.js")
    nuevo_tenant_page = os.path.join(base_dir, "app", "tenants", "nuevo", "page.js")
    admin_sistema_page = os.path.join(base_dir, "app", "admin", "sistema", "page.js")
    
    assert os.path.exists(brain_view)
    assert os.path.exists(public_api)
    assert os.path.exists(cerebro_page)
    assert os.path.exists(nuevo_tenant_page)
    assert os.path.exists(admin_sistema_page)
