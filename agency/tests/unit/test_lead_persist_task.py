"""
test_lead_persist_task.py

Pruebas TDD para el worker async de persistencia de leads de Instagram (S1 — DM Leads CRM).
Cubre REQ-DM-LEAD-01 (tenant resuelto), REQ-DM-LEAD-04 (clasificación en conversacion_history),
REQ-DM-LEAD-05 (idempotencia por hash) y REQ-DM-LEAD-06 (envío gateado: sin Graph API ni
pending_manual). El core async se testea directamente (patrón asyncio.run de la suite).

Aislamiento: el SQLite :memory: (StaticPool) persiste entre tests del mismo proceso, así que
cada test usa tenant + ig_user_id únicos. El LLM se parchea a "offline" en los tests que corren
el grafo: ese es exactamente el escenario de fallback del diseño (Qdrant/LLM caídos), y evita
llamadas de red reales con las keys del .env.
"""

import asyncio
import json
import uuid
from unittest.mock import patch, AsyncMock

import pytest

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

_QUESTION_MSG = {
    "ig_user_id": "user_q1",
    "mensaje_original": "¿cómo funciona el servicio?",
    "origen": "comment",
    "keyword": "CONSULTA",
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


@patch("agents.llm.acomplete", side_effect=RuntimeError("LLM offline"))
def test_lead_persisted_with_resolved_tenant(_mock_llm):
    """REQ-DM-LEAD-01: el lead persiste con el tenant resuelto (no 'default'),
    platform=instagram, status=Calificado y qualification_score>=60."""
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


@patch("agents.llm.acomplete", side_effect=RuntimeError("LLM offline"))
def test_repeated_webhook_does_not_duplicate(_mock_llm):
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


@patch("agents.llm.acomplete", side_effect=RuntimeError("LLM offline"))
def test_classification_persisted_in_conversacion_history(_mock_llm):
    """REQ-DM-LEAD-04: la clasificación del dm_graph queda en conversacion_history."""
    tenant_id = str(uuid.uuid4())
    lead_data = {**_COMMENT_AUDIO, "ig_user_id": "user_ig_cls_02"}

    result = _run(_persist_fresh(tenant_id, lead_data))
    assert result["status"] == "created"
    assert result["intent"] == "purchase_intent"

    async def _assert():
        async with AsyncSessionLocal() as session:
            lead = (
                await session.execute(
                    select(Lead).where(Lead.ig_user_id == "user_ig_cls_02")
                )
            ).scalars().one()
            history = json.loads(lead.conversacion_history)
            assert isinstance(history, list) and len(history) >= 1
            assert history[0]["intent"] == "purchase_intent"
            assert "confidence" in history[0]

    _run(_assert())


@patch("agents.dm_graph.build_dm_graph", side_effect=RuntimeError("graph roto"))
def test_dm_graph_failure_falls_back_and_keeps_persistence(_mock_graph):
    """REQ-DM-LEAD-04: si el dm_graph falla, se usa classify_intent y la persistencia NO se rompe."""
    tenant_id = str(uuid.uuid4())
    lead_data = {**_COMMENT_AUDIO, "ig_user_id": "user_ig_fbk_03"}

    result = _run(_persist_fresh(tenant_id, lead_data))
    assert result["status"] == "created"

    async def _assert():
        async with AsyncSessionLocal() as session:
            lead = (
                await session.execute(
                    select(Lead).where(Lead.ig_user_id == "user_ig_fbk_03")
                )
            ).scalars().one()
            history = json.loads(lead.conversacion_history)
            assert history[0]["intent"] == "purchase_intent"

    _run(_assert())


@patch("agents.llm.acomplete", side_effect=RuntimeError("LLM offline"))
def test_no_dm_send_side_effects(_mock_llm):
    """REQ-DM-LEAD-06: el flujo S1 no produce envío simulado ni pending_manual.
    Para intent 'question' el grafo ruta al send node: se ejecuta (solo log + SSE,
    sin llamada Graph API) y el resultado no contiene estado simulado de envío."""
    from agents.dm_graph import node_send_dm_reply

    tenant_id = str(uuid.uuid4())
    lead_data = {**_QUESTION_MSG, "ig_user_id": "user_q1"}

    async def _test():
        await init_db()
        async with AsyncSessionLocal() as session:
            await _seed_tenant(session, tenant_id)

        # Envuelve el send node real (log + SSE) para registrar su invocación sin
        # alterar su comportamiento: probar el wiring sin side-effects externos.
        send_node = AsyncMock(wraps=node_send_dm_reply)
        with patch("agents.dm_graph.node_send_dm_reply", new=send_node):
            result = await persist_lead_core(tenant_id, lead_data)
        assert result["status"] == "created"
        assert send_node.await_count == 1
        assert "pending_manual" not in json.dumps(result)

        async with AsyncSessionLocal() as session:
            lead = (
                await session.execute(select(Lead).where(Lead.ig_user_id == "user_q1"))
            ).scalars().one()
            assert "pending_manual" not in (lead.conversacion_history or "")

    _run(_test())


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


def test_lead_persist_task_registered_and_core_reachable():
    """Contrato Celery: la task pública existe y delega en el core (mismo nombre de ruta)."""
    from workers.lead_persist_task import persist_instagram_lead

    assert persist_instagram_lead.name == "workers.lead_persist_task.persist_instagram_lead"
    assert callable(persist_instagram_lead.run)


@patch("agents.llm.acomplete", side_effect=RuntimeError("LLM offline"))
def test_webhook_payload_resolves_tenant_and_persists(_mock_llm):
    """T-S1-06: payload con media.owner.id -> tenant_b (no 'default'); el lead persiste con ese tenant."""
    from backend.webhooks.instagram_inbound import (
        process_instagram_webhook_payload,
        _resolve_tenant_from_payload,
    )

    tenant_b = str(uuid.uuid4())

    async def _test():
        await init_db()
        async with AsyncSessionLocal() as session:
            account_id = await _seed_tenant(session, tenant_b)

        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "entry_t6",
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "comment_t6",
                                "text": "¡Me encanta! Quiero comprar el sistema con AUDIO por favor",
                                "media": {"owner": {"id": account_id}},
                                "from": {"id": "user_ig_t6"},
                            },
                        }
                    ],
                }
            ],
        }

        tenant_id = await _resolve_tenant_from_payload(payload)
        assert tenant_id == tenant_b

        leads = process_instagram_webhook_payload(payload, tenant_id=tenant_id)
        assert len(leads) == 1
        assert leads[0]["keyword"] == "AUDIO"

        result = await persist_lead_core(tenant_id, leads[0])
        assert result["status"] == "created"

        async with AsyncSessionLocal() as session:
            lead = (
                await session.execute(
                    select(Lead).where(Lead.ig_user_id == "user_ig_t6")
                )
            ).scalars().one()
            assert lead.tenant_id == tenant_b
            assert lead.keyword == "AUDIO"

    _run(_test())


def test_webhook_payload_without_account_falls_back_to_default():
    """T-S1-06: payload flat (sin cuenta mapeable) -> _resolve_tenant_from_payload => 'default'."""
    from backend.webhooks.instagram_inbound import _resolve_tenant_from_payload

    flat_payload = {
        "object": "instagram",
        "entry": [{"id": "entry_x", "changes": [{"field": "comments", "value": {"text": "hola"}}]}],
    }

    async def _test():
        await init_db()
        tenant_id = await _resolve_tenant_from_payload(flat_payload)
        assert tenant_id == "default"

    _run(_test())


@patch("agents.llm.acomplete", side_effect=RuntimeError("LLM offline"))
def test_webhook_endpoint_enqueues_worker_and_returns_200(_mock_llm):
    """T-S1-07: POST /webhooks/instagram -> 200 inmediato y el worker (eager) persiste
    el lead con el tenant resuelto por cuenta (flujo webhook -> worker completo)."""
    from httpx import AsyncClient, ASGITransport
    from backend.main import app

    tenant_b = str(uuid.uuid4())
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "entry_e2e",
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comment_e2e",
                            "text": "Quiero comprar el sistema con AUDIO por favor",
                            "media": {"owner": {"id": None}},
                            "from": {"id": "user_ig_e2e"},
                        },
                    }
                ],
            }
        ],
    }

    async def _test():
        await init_db()
        async with AsyncSessionLocal() as session:
            account_id = await _seed_tenant(session, tenant_b)
        payload["entry"][0]["changes"][0]["value"]["media"]["owner"]["id"] = account_id

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post("/webhooks/instagram", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["processed_leads_count"] == 1

        async with AsyncSessionLocal() as session:
            lead = (
                await session.execute(
                    select(Lead).where(Lead.ig_user_id == "user_ig_e2e")
                )
            ).scalars().one()
            assert lead.tenant_id == tenant_b
            assert lead.keyword == "AUDIO"

    _run(_test())


def test_webhook_endpoint_returns_500_on_sync_failure_not_ack():
    """RESILIENCE-001: ante fallo síncrono el endpoint NO responde 200 queued_dlq;
    responde 500 para que Meta reintente (redelivery) y el lead no se pierda."""
    from httpx import AsyncClient, ASGITransport
    from backend.main import app

    tenant_c = str(uuid.uuid4())
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "entry_fail",
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comment_fail",
                            "text": "Quiero AUDIO",
                            "media": {"owner": {"id": "acct_fail"}},
                            "from": {"id": "user_ig_fail"},
                        },
                    }
                ],
            }
        ],
    }

    async def _test():
        await init_db()
        with patch(
            "backend.webhooks.instagram_inbound._resolve_tenant_from_payload",
            side_effect=RuntimeError("db down"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.post("/webhooks/instagram", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert "Error en procesamiento síncrono" in data["detail"]

    _run(_test())


@patch("agents.llm.acomplete", side_effect=RuntimeError("LLM offline"))
def test_retry_after_partial_insert_recovers_classification(_mock_llm):
    """RELIABILITY-001: un lead con el INSERT commiteado pero sin clasificación
    (fallo entre los dos commits) se recupera en el redelivery: se clasifica,
    se scorea y se persiste sobre la MISMA fila, en vez de quedar 'duplicate'
    para siempre con status='Nuevo'/score 0/sin historial."""
    tenant_id = str(uuid.uuid4())
    lead_data = {**_COMMENT_AUDIO, "ig_user_id": "user_ig_recover_01"}

    async def _test():
        await init_db()
        async with AsyncSessionLocal() as session:
            await _seed_tenant(session, tenant_id)

        # --- Ventana de fallo: el INSERT commitea, pero la fase de clasificación
        # (y por tanto el UPDATE con score/status/history) levanta y nunca corre.
        with patch(
            "workers.lead_persist_task._run_dm_classification",
            side_effect=RuntimeError("db down during classification"),
        ):
            with pytest.raises(RuntimeError):
                await persist_lead_core(tenant_id, lead_data)

        # El lead quedó a medio persistir: 'Nuevo', score 0, sin historial.
        async with AsyncSessionLocal() as session:
            half = (
                await session.execute(
                    select(Lead).where(Lead.ig_user_id == "user_ig_recover_01")
                )
            ).scalars().one()
            assert half.status == "Nuevo"
            assert half.qualification_score == 0
            assert half.conversacion_history is None
            half_id = str(half.id)

        # --- Redelivery: la clasificación ya funciona y el dedup NO debe reportar
        # 'duplicate' sin más: debe COMPLETAR el lead (mismo lead_id, sin fila nueva).
        second = await persist_lead_core(tenant_id, lead_data)
        assert second["status"] == "duplicate"
        assert second.get("recovered") is True
        assert second["lead_id"] == half_id
        assert second["intent"] == "purchase_intent"
        assert second["qualification_score"] >= 60
        assert second["lead_status"] == "Calificado"

        async with AsyncSessionLocal() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(Lead)
                    .where(Lead.ig_user_id == "user_ig_recover_01")
                )
            ).scalars().one()
            assert count == 1  # sin fila duplicada

            lead = (
                await session.execute(
                    select(Lead).where(Lead.ig_user_id == "user_ig_recover_01")
                )
            ).scalars().one()
            assert str(lead.id) == half_id
            assert lead.status == "Calificado"
            assert lead.qualification_score >= 60
            history = json.loads(lead.conversacion_history)
            assert isinstance(history, list) and len(history) == 1
            assert history[0]["intent"] == "purchase_intent"

    _run(_test())
