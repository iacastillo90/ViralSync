"""
lead_persist_task.py

Worker Celery async de persistencia de leads de Instagram (S1a — DM Leads CRM).
REQ-DM-LEAD-01/05: persiste el lead con el tenant resuelto (nunca "default"),
idempotencia por `dedup_hash` (sha256 de user|mensaje) y scoring determinista
(`lead_scoring`) con intent por reglas (`classify_intent`).

La clasificación vía `dm_graph` y su persistencia en `conversacion_history` se
agregan en S1b (wiring del grafo). El envío queda GATEADO (decisión usuario P3):
`node_send_dm_reply` NO se toca — el flujo S1 solo persiste + scorea.
"""

import asyncio
import hashlib
import logging
import uuid
from typing import Any, Dict

from sqlalchemy import select

from workers.celery_app import celery_app
from backend.db.session import AsyncSessionLocal
from backend.db.models import Lead
from backend.services.lead_scoring import score_lead
from agents.nodes.dm_response import classify_intent

logger = logging.getLogger(__name__)


def _dedup_hash(ig_user_id: str, message: str) -> str:
    """Hash determinista de idempotencia: mismo (usuario, mensaje) -> mismo lead."""
    raw = f"{ig_user_id}|{message}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _run_async(coro):
    """Ejecuta un coroutine de forma síncrona (patrón graph_execution_task).

    Con Celery Eager dentro de un request async (tests) ya hay un event loop
    corriendo y `asyncio.run` lanzaría RuntimeError; en ese caso se ejecuta el
    coroutine en un hilo con su propio loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def persist_lead_core(tenant_id: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """Core async de persistencia del lead (testeable, patrón de la suite).

    :param tenant_id: tenant ya resuelto por el webhook (account -> tenant).
    :param lead_data: {ig_user_id, mensaje_original, origen, keyword}.
    :return: dict con status created/duplicate y metadata del scoring.
    """
    ig_user_id = str(lead_data.get("ig_user_id") or "")
    message = str(lead_data.get("mensaje_original") or "")
    keyword = str(lead_data.get("keyword") or "")
    origin = str(lead_data.get("origen") or "comment")

    dedup = _dedup_hash(ig_user_id, message)

    # 1. Idempotencia por hash (REQ-DM-LEAD-05): redelivery de Meta no duplica.
    async with AsyncSessionLocal() as session:
        existing = (
            await session.execute(select(Lead).where(Lead.dedup_hash == dedup))
        ).scalars().first()
        if existing is not None:
            logger.info(
                "[%s] Webhook duplicado para lead '%s' (hash %s). Retornando existente.",
                tenant_id, existing.id, dedup[:12],
            )
            return {"status": "duplicate", "lead_id": str(existing.id)}

        # 2. INSERT Lead con status inicial 'Nuevo' (el webhook no trae video: video_id NULL).
        lead_id = str(uuid.uuid4())
        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            video_id=None,
            keyword=keyword,
            ig_user_id=ig_user_id,
            mensaje_original=message,
            origen=origin,
            status="Nuevo",
            qualification_score=0,
            platform="instagram",
            dedup_hash=dedup,
        )
        session.add(lead)
        await session.commit()

    # 3. Scoring determinista (REQ-DM-LEAD-03): intent por reglas; la clasificación
    #    del dm_graph y el historial conversacion_history se agregan en S1b.
    intent = classify_intent(message)
    score, status = score_lead(message, intent)

    # 4. Update con el score y status calificados.
    async with AsyncSessionLocal() as session:
        lead = await session.get(Lead, lead_id)
        if lead is not None:
            lead.qualification_score = score
            lead.status = status
            await session.commit()

    logger.info(
        "[%s] Lead '%s' persistido: intent=%s score=%s status=%s",
        tenant_id, lead_id, intent, score, status,
    )
    return {
        "status": "created",
        "lead_id": lead_id,
        "intent": intent,
        "qualification_score": score,
        "lead_status": status,
    }


@celery_app.task(
    name="workers.lead_persist_task.persist_instagram_lead",
    bind=True,
    max_retries=2,
)
def persist_instagram_lead(self, tenant_id: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """Task Celery (cola `webhooks`) que persiste un lead de Instagram (REQ-DM-LEAD-01)."""
    logger.info("[%s] Ejecutando persist_instagram_lead en Celery Worker...", tenant_id)
    try:
        return _run_async(persist_lead_core(tenant_id, lead_data))
    except Exception as exc:  # noqa: BLE001 - retry transitorio + respuesta honesta
        logger.error("[%s] Error en persist_instagram_lead: %s", tenant_id, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5) from exc
        return {"status": "failed", "error": str(exc)}
