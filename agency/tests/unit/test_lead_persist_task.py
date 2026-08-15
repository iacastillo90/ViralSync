"""
test_lead_persist_task.py

Pruebas TDD para el worker async de persistencia de leads de Instagram (S1a — DM Leads CRM).
Cubre REQ-DM-LEAD-01 (tenant resuelto), REQ-DM-LEAD-05 (idempotencia por hash) y el scoring
determinista (qualification_score + status). La clasificación vía dm_graph,
conversacion_history y el test de envío gateado se agregan en S1b.

Aislamiento: el SQLite :memory: (StaticPool) persiste entre tests del mismo proceso, así que
cada test usa tenant + ig_user_id únicos.
"""

import asyncio
import json
import uuid
from unittest.mock import patch

from sqlalchemy import select, func

from backend.db.session import init_db, AsyncSessionLocal
from backend.db.models import Tenant, Lead
from workers.lead_persist_task import persist_lead_core

_COMMENT_AUDIO = {
    "ig_user_id": "user_ig_777",
    # "comprar" -> classify_intent => purchase_intent; keyword AUDIO + señal "quiero"
    # -> score_lead => (90, Calificado).
    "mensaje_original": "¡Me encanta este micrófono! Quiero comprar el sistema con AUDIO por favor",
    "origen": "comment",
    "keyword": "AUDIO",
}


async def _seed_tenant(session, tenant_id: str, account_id: str = None) -> str:
    """Crea un tenant con instagram_business_account_id ÚNICO (aislamiento entre tests)."""
    account_id = account_id or f"acct_{tenant_id[:8]}"
    session.add(
        Tenant(
            id=tenant_id,
            name="Tenant B",
            instagram_business_account_id=account_id,
        )
    )
    await session.commit()
    return account_id


def _run(coro):
    return asyncio.run(coro)


async def _persist_fresh(tenant_id: str, lead_data: dict) -> dict:
    """Persiste un lead en un tenant recién creado (aislamiento entre tests)."""
    await init_db()
    async with AsyncSessionLocal() as session:
        await _seed_tenant(session, tenant_id)
    return await persist_lead_core(tenant_id, dict(lead_data))


def test_lead_persisted_with_resolved_tenant():
    """REQ-DM-LEAD-01: el lead persiste con el tenant resuelto (no 'default'),
    platform=instagram, status=Calificado y qualification_score>=60 (scoring S1a)."""
    tenant_id = str(uuid.uuid4())
    lead_data = {**_COMMENT_AUDIO, "ig_user_id": "user_ig_777"}

    result = _run(_persist_fresh(tenant_id, lead_data))
    assert result["status"] == "created"
    assert result["intent"] == "purchase_intent"

    async def _assert():
        async with AsyncSessionLocal() as session:
            lead = (
                await session.execute(
                    select(Lead).where(Lead.ig_user_id == "user_ig_777")
                )
            ).scalars().one()
            assert lead.tenant_id == tenant_id
            assert lead.platform == "instagram"
            assert lead.status == "Calificado"
            assert lead.qualification_score >= 60
            # El webhook no trae video: video_id queda NULL (migración 011).
            assert lead.video_id is None
            assert lead.dedup_hash is not None

    _run(_assert())


def test_repeated_webhook_does_not_duplicate():
    """REQ-DM-LEAD-05: mismo (user, message) -> el segundo webhook no inserta fila."""
    tenant_id = str(uuid.uuid4())
    lead_data = {**_COMMENT_AUDIO, "ig_user_id": "user_ig_dup_01"}

    async def _test():
        await init_db()
        async with AsyncSessionLocal() as session:
            await _seed_tenant(session, tenant_id)

        first = await persist_lead_core(tenant_id, lead_data)
        second = await persist_lead_core(tenant_id, lead_data)

        assert first["status"] == "created"
        assert second["status"] == "duplicate"
        assert second["lead_id"] == first["lead_id"]

        async with AsyncSessionLocal() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(Lead)
                    .where(Lead.ig_user_id == "user_ig_dup_01")
                )
            ).scalar_one()
            assert count == 1

    _run(_test())


def test_lead_persist_task_registered_and_core_reachable():
    """Contrato Celery: la task pública existe y delega en el core (mismo nombre de ruta)."""
    from workers.lead_persist_task import persist_instagram_lead

    assert persist_instagram_lead.name == "workers.lead_persist_task.persist_instagram_lead"
    assert callable(persist_instagram_lead.run)


class _FakeRedisClient:
    """Cliente Redis fake que registra los LPUSH para verificar el DLQ sin infra real."""

    def __init__(self):
        self.lpushed = []

    def lpush(self, key: str, value: str) -> int:
        self.lpushed.append((key, value))
        return 1


def test_terminal_failure_writes_payload_to_dlq():
    """RESILIENCE-001: al agotar retries, el payload fallido se escribe en Redis (lead_persist:dlq).

    Simula un fallo de DB (persist_lead_core levanta) con retries agotados
    (push_request con retries == max_retries) y verifica que el payload con
    tenant_id, lead_data, error, ts y attempts llegue al sink durable.
    """
    import redis as redis_module
    from workers.lead_persist_task import persist_instagram_lead

    fake_redis = _FakeRedisClient()
    tenant_id = str(uuid.uuid4())
    lead_data = {**_COMMENT_AUDIO, "ig_user_id": "user_ig_dlq"}

    persist_instagram_lead.push_request(
        id="task-dlq-1", args=(tenant_id, lead_data), retries=2
    )
    try:
        with patch.object(
            redis_module.Redis, "from_url", return_value=fake_redis
        ), patch(
            "workers.lead_persist_task.persist_lead_core",
            side_effect=RuntimeError("db down"),
        ):
            result = persist_instagram_lead.run(tenant_id, lead_data)
    finally:
        persist_instagram_lead.pop_request()

    # El fallo terminal sigue reportando "failed" honestamente...
    assert result["status"] == "failed"
    assert result["error"] == "db down"

    # ...pero el payload ya NO se pierde: queda en el sink durable bajo lead_persist:dlq.
    assert len(fake_redis.lpushed) == 1
    key, raw = fake_redis.lpushed[0]
    assert key == "lead_persist:dlq"
    payload = json.loads(raw)
    assert payload["tenant_id"] == tenant_id
    assert payload["lead_data"] == lead_data
    assert payload["error"] == "db down"
    assert payload["attempts"] == 3  # 1 intento inicial + 2 retries (max_retries=2)
    assert isinstance(payload["ts"], str) and payload["ts"]
