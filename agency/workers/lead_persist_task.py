"""
lead_persist_task.py

Worker Celery async de persistencia de leads de Instagram (S1 — DM Leads CRM).
REQ-DM-LEAD-01/04/05/06: persiste el lead con el tenant resuelto (nunca "default"),
idempotencia por `dedup_hash`, scoring determinista (lead_scoring) y clasificación
best-effort vía `dm_graph` persistida como JSON en `conversacion_history`.

El envío queda GATEADO (decisión usuario P3): `node_send_dm_reply` NO se toca —
el flujo S1 solo persiste + scorea + clasifica. Cualquier fallo del grafo, Qdrant o
LLM degrada a `classify_intent` (reglas) sin romper la persistencia.
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from workers.celery_app import celery_app, REDIS_URL
from backend.db.session import AsyncSessionLocal
from backend.db.models import Lead
from backend.services.lead_scoring import score_lead
from agents import dm_graph as dm_graph_module
from agents.nodes.dm_response import classify_intent

logger = logging.getLogger(__name__)

# Sink durable para fallos terminales (RESILIENCE-001): lista en Redis que conserva
# los payloads no persistidos para auditoría/replay posterior (patrón DLQ).
_DLQ_KEY = "lead_persist:dlq"


def _push_to_dlq(
    tenant_id: str, lead_data: Dict[str, Any], error: str, attempts: int
) -> None:
    """Escribe el payload fallido en el DLQ de Redis (best-effort).

    Tras agotar `max_retries` el mensaje se ackea y el lead se perdería sin este
    sink durable. Patrón del repo (metrics_loop/llm_budget): `redis.Redis.from_url`
    con import lazy y socket_timeout corto; si Redis falla, se loguea y el task
    retorna "failed" igual (el DLQ no debe romper el flujo de error).
    """
    try:
        import redis

        r = redis.Redis.from_url(REDIS_URL, socket_timeout=1.0)
        payload = {
            "tenant_id": tenant_id,
            "lead_data": lead_data,
            "error": error,
            "ts": datetime.utcnow().isoformat(),
            "attempts": attempts,
        }
        r.lpush(_DLQ_KEY, json.dumps(payload, ensure_ascii=False))
        logger.error("[%s] Payload fallido enviado a DLQ %s (attempts=%s).", tenant_id, _DLQ_KEY, attempts)
    except Exception as dlq_exc:  # noqa: BLE001 - best-effort: el DLQ no debe romper el flujo
        logger.error(
            "[%s] No se pudo escribir el DLQ %s: %s",
            tenant_id, _DLQ_KEY, dlq_exc, exc_info=True,
        )


def _dedup_hash(ig_user_id: str, message: str) -> str:
    """Hash determinista de idempotencia: mismo (usuario, mensaje) -> mismo lead."""
    raw = f"{ig_user_id}|{message}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_intent(lead: Lead) -> Optional[str]:
    """Extrae el intent de la última clasificación persistida (si existe)."""
    try:
        history = json.loads(lead.conversacion_history) if lead.conversacion_history else []
        if isinstance(history, list) and history:
            return history[-1].get("intent")
    except (ValueError, TypeError):
        pass
    return None


async def _run_dm_classification(
    tenant_id: str, lead_id: str, message: str
) -> Dict[str, Any]:
    """Ejecuta el dm_graph con state mínimo y devuelve intent/confidence.

    Best-effort: cualquier fallo (LLM, Qdrant, grafo) degrada a `classify_intent`
    con confianza de respaldo. Nunca rompe la persistencia del lead.
    """
    try:
        graph = dm_graph_module.build_dm_graph()
        result = await graph.ainvoke(
            {
                "tenant_id": tenant_id,
                "lead_id": lead_id,
                "incoming_message": message,
            }
        )
        return {
            "intent": result.get("intent") or classify_intent(message),
            "confidence": float(result.get("confidence_score") or 0.0),
            "reply_text": result.get("reply_text", ""),
        }
    except Exception as exc:  # noqa: BLE001 - best-effort: fallback sin romper persistencia
        logger.warning(
            "[%s] dm_graph falló (%s); usando classify_intent de respaldo.", tenant_id, exc
        )
        return {"intent": classify_intent(message), "confidence": 0.0, "reply_text": ""}


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
    :return: dict con status created/duplicate y metadata de la clasificación.
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
            return {
                "status": "duplicate",
                "lead_id": str(existing.id),
                "intent": _read_intent(existing),
            }

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

    # 3. Clasificación best-effort vía dm_graph (REQ-DM-LEAD-04) -> intent para el score.
    classification = await _run_dm_classification(tenant_id, lead_id, message)
    intent = classification.get("intent") or "unclear"

    # 4. Scoring determinista (REQ-DM-LEAD-03) + update + historial.
    score, status = score_lead(message, intent)
    history_entry = {
        "intent": intent,
        "confidence": classification.get("confidence", 0.0),
        "ts": datetime.utcnow().isoformat(),
    }
    async with AsyncSessionLocal() as session:
        lead = await session.get(Lead, lead_id)
        if lead is not None:
            lead.qualification_score = score
            lead.status = status
            lead.conversacion_history = json.dumps([history_entry], ensure_ascii=False)
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
        # RESILIENCE-001: retries agotados -> el mensaje se ackea; el payload NO se
        # pierde, va al sink durable en Redis (lead_persist:dlq) para auditoría/replay.
        _push_to_dlq(tenant_id, lead_data, str(exc), attempts=self.request.retries + 1)
        return {"status": "failed", "error": str(exc)}
