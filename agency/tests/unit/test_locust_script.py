"""
test_locust_script.py

Pruebas unitarias para validar la estructura del script de carga locustfile.py (REQ-LLT-01).
"""

import pytest

# Import perezoso DENTRO de cada test a propósito: `locust` ejecuta
# `gevent.monkey.patch_all()` al importarse, lo que corrompe el event loop
# de los e2e async (anyio) si ocurre durante la collection de pytest. Al
# diferir el import al momento de ejecución, collection queda limpia y los
# tests async corren primero; gevent solo se parchea al correr este archivo.


def test_locust_script_tenant_ids_count():
    """Verifica que el script de carga defina una piscina de tenants para pruebas."""
    pytest.importorskip("locust")
    from tests.load.locustfile import TENANT_IDS

    assert len(TENANT_IDS) >= 10
    assert "tenant_loadtest_1" in TENANT_IDS


def test_locust_user_class_tasks():
    """Verifica las tareas configuradas en ViralSyncTenantUser."""
    pytest.importorskip("locust")
    from tests.load.locustfile import ViralSyncTenantUser

    assert hasattr(ViralSyncTenantUser, "check_health")
    assert hasattr(ViralSyncTenantUser, "fetch_ideas")
    assert hasattr(ViralSyncTenantUser, "trigger_graph_run")
