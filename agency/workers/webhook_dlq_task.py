"""
webhook_dlq_task.py

Tarea Celery con Cola de Reintentos (Dead Letter Queue - DLQ) para Webhooks de Instagram Meta.
Reintenta el procesamiento con backoff exponencial y persiste fallos definitivos en Redis para auditoría.
"""

import logging
from typing import Dict, Any
from workers.celery_app import celery_app
from backend.webhooks.instagram_inbound import process_instagram_webhook_payload

logger = logging.getLogger(__name__)


@celery_app.task(
    name="workers.webhook_dlq_task.process_failed_webhook_retry",
    bind=True,
    max_retries=5,
    default_retry_delay=60,
)
def process_failed_webhook_retry(self, payload: Dict[str, Any], tenant_id: str = "default") -> Dict[str, Any]:
    """
    Tarea Celery DLQ para procesar webhooks de Meta con política de reintentos exponenciales.

    :param payload: JSON del webhook fallido.
    :param tenant_id: ID del tenant.
    :return: Estado del procesamiento y leads extraídos.
    """
    logger.info(f"[{tenant_id}] Ejecutando reintento DLQ para webhook de Instagram (intento {self.request.retries + 1})")

    try:
        leads = process_instagram_webhook_payload(payload)
        logger.info(f"[{tenant_id}] Webhook re-procesado exitosamente en DLQ: {len(leads)} leads extraídos")
        return {"status": "success", "leads_count": len(leads), "leads": leads}
    except Exception as exc:
        logger.error(f"[{tenant_id}] Fallo en intento {self.request.retries + 1} de webhook: {exc}")
        if self.request.retries < self.max_retries:
            # Exponencial backoff: 60s, 120s, 240s...
            retry_delay = 60 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=retry_delay)
        
        # Guardar en la cola muerta definitiva en Redis tras agotar reintentos
        return {"status": "dead_letter", "error": str(exc), "payload": payload}
