"""
test_locust_script.py

Pruebas unitarias para validar la estructura del script de carga locustfile.py (REQ-LLT-01).
"""

import pytest
from tests.load.locustfile import ViralSyncTenantUser, TENANT_IDS


def test_locust_script_tenant_ids_count():
    """Verifica que el script de carga defina una piscina de tenants para pruebas."""
    assert len(TENANT_IDS) >= 10
    assert "tenant_loadtest_1" in TENANT_IDS


def test_locust_user_class_tasks():
    """Verifica las tareas configuradas en ViralSyncTenantUser."""
    assert hasattr(ViralSyncTenantUser, "check_health")
    assert hasattr(ViralSyncTenantUser, "fetch_ideas")
    assert hasattr(ViralSyncTenantUser, "trigger_graph_run")
