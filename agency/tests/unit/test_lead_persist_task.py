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
import uuid

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
