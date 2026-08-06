"""
test_frontend_infra.py

Pruebas unitarias para validar la existencia e integridad del middleware y componentes de infraestructura.
"""

import os


def test_frontend_infra_files_exist():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
    
    middleware_file = os.path.join(base_dir, "middleware.js")
    tenant_store = os.path.join(base_dir, "stores", "useTenantStore.js")
    api_config = os.path.join(base_dir, "services", "apiConfig.js")
    header_file = os.path.join(base_dir, "components", "layout", "Header.jsx")
    sidebar_file = os.path.join(base_dir, "components", "layout", "Sidebar.jsx")
    
    assert os.path.exists(middleware_file)
    assert os.path.exists(tenant_store)
    assert os.path.exists(api_config)
    assert os.path.exists(header_file)
    assert os.path.exists(sidebar_file)
