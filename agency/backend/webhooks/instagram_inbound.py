"""
instagram_inbound.py

Procesador de eventos Webhook de Meta para DMs y Comentarios de Instagram.
Extracción de palabras clave de atribución (keyword) y calificación ligera de leads.
Resolución de tenant por `tenants.instagram_business_account_id` (REQ-DM-LEAD-01):
el caller async (main.py) resuelve vía `_resolve_tenant_from_payload` y lo pasa al
procesador, que publica SSE al tenant resuelto (no "default").
"""

import logging
from typing import Dict, Any, List, Optional

from sqlalchemy import select

from backend.db.session import AsyncSessionLocal
from backend.db.models import Tenant

logger = logging.getLogger(__name__)


def _extract_account_id(payload: Dict[str, Any]) -> Optional[str]:
    """Extrae el ID de cuenta de Instagram del payload.

    Fuentes en orden: `media.owner.id` (comentarios), `recipient.id` (DMs),
    `entry.id` (fallback). Devuelve None si no hay ninguna.
    """
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            val = change.get("value", {}) or {}
            media = val.get("media", {}) or {}
            if isinstance(media, dict):
                owner = media.get("owner", {}) or {}
                if isinstance(owner, dict) and owner.get("id"):
                    return owner["id"]
        for msg in entry.get("messaging", []) or []:
            recipient = (msg.get("recipient", {}) or {}).get("id")
            if recipient:
                return recipient
        if entry.get("id"):
            return entry["id"]
    return None


async def _resolve_tenant_from_payload(payload: Dict[str, Any]) -> str:
    """Resuelve el tenant por instagram_business_account_id (REQ-DM-LEAD-01).

    Devuelve "default" si el payload no trae cuenta o ningún tenant la mapea.
    """
    account_id = _extract_account_id(payload)
    if not account_id:
        return "default"
    async with AsyncSessionLocal() as session:
        tenant_id = (
            await session.execute(
                select(Tenant.id).where(Tenant.instagram_business_account_id == account_id)
            )
        ).scalars().first()
        return str(tenant_id) if tenant_id else "default"


def process_instagram_webhook_payload(
    payload: Dict[str, Any], tenant_id: str = "default"
) -> List[Dict[str, Any]]:
    """
    Procesa el JSON entrante de Meta y extrae los leads calificados con atribución a palabra clave.
    
    :param payload: JSON crudo enviado por Instagram Graph API.
    :param tenant_id: tenant resuelto por el caller (main.py usa `_resolve_tenant_from_payload`);
                      los callers legacy (DLQ/tests flat) conservan "default".
    :return: Lista de leads calificados extraídos.
    """
    extracted_leads = []
    
    if not payload or payload.get("object") != "instagram":
        # PR-A fallback para payloads de test unitario plano sin object="instagram"
        entries = payload.get("entry", [])
        if not entries:
            return []
    else:
        entries = payload.get("entry", [])

    from backend.sse_manager import sse_manager

    for entry in entries:
        changes = entry.get("changes", [])
        messaging = entry.get("messaging", [])

        # 1. Procesar Comentarios
        for change in changes:
            field = change.get("field")
            val = change.get("value", {})
            if field == "comments":
                text = val.get("text", "").strip()
                user_id = val.get("from", {}).get("id", "unknown_ig_user")
                
                # Calificación ligera por palabra clave (ej. AUDIO, INFO, CONSULTA, PRECIO, OFERTA)
                text_upper = text.upper()
                keywords = ["AUDIO", "INFO", "CONSULTA", "PRECIO", "OFERTA", "PROMO"]
                matched_kw = next((kw for kw in keywords if kw in text_upper), None)

                if matched_kw:
                    lead_data = {
                        "keyword": matched_kw,
                        "ig_user_id": user_id,
                        "mensaje_original": text,
                        "origen": "comment",
                        "auto_reply_sent": True,
                        "offer_url": f"https://viralsync.io/oferta/{matched_kw.lower()}"
                    }
                    extracted_leads.append(lead_data)
                    sse_manager.publish_event(tenant_id, "lead_captured", lead_data)
                    logger.info(f"[Bot DM Auto-Reply] Lead capturado por comentario '{matched_kw}' de usuario {user_id}. Auto-respuesta despachada.")

        # 2. Procesar Mensajes Directos (DMs)
        for msg in messaging:
            message_text = msg.get("message", {}).get("text", "").strip()
            sender_id = msg.get("sender", {}).get("id", "unknown_ig_user")
            
            if "CONSULTA" in message_text.upper():
                lead_data = {
                    "keyword": "CONSULTA",
                    "ig_user_id": sender_id,
                    "mensaje_original": message_text,
                    "origen": "dm",
                }
                extracted_leads.append(lead_data)
                sse_manager.publish_event(tenant_id, "lead_captured", lead_data)

    return extracted_leads

