"""
test_sse_redis_pubsub.py

Pruebas unitarias para verificar la suscripción y emisión Pub/Sub multi-réplica de SSEManager (REQ-SRP-01/02).
"""

import pytest
import asyncio
from backend.sse_manager import sse_manager


@pytest.mark.anyio
async def test_sse_subscribe_and_unsubscribe():
    """Verifica el ciclo de suscripción y desuscripción local en SSEManager."""
    tenant_id = "tenant_test_sse"
    queue = sse_manager.subscribe(tenant_id)
    
    assert tenant_id in sse_manager._listeners
    assert queue in sse_manager._listeners[tenant_id]
    
    sse_manager.unsubscribe(tenant_id, queue)
    assert tenant_id not in sse_manager._listeners


@pytest.mark.anyio
async def test_sse_publish_local_fallback():
    """Verifica que emitir un evento con publish entregue el payload a las colas activas."""
    tenant_id = "tenant_test_pub"
    queue = sse_manager.subscribe(tenant_id)
    
    await sse_manager.publish(tenant_id, "node_start", {"node": "ideation"})
    
    payload = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert "event: node_start" in payload
    assert "ideation" in payload
    
    sse_manager.unsubscribe(tenant_id, queue)


@pytest.mark.anyio
async def test_emit_graph_error_with_code():
    """Verifica que emit_graph_error incluya el campo opcional 'code'."""
    tenant_id = "tenant_test_err"
    queue = sse_manager.subscribe(tenant_id)
    
    await sse_manager.emit_graph_error(tenant_id, "Sin candidatos RUM", code="no_candidates")
    
    payload = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert "event: graph_error" in payload
    assert "no_candidates" in payload
    assert "Sin candidatos RUM" in payload
    
    sse_manager.unsubscribe(tenant_id, queue)
