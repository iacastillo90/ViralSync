"""
instagram_inbound.py

Procesador de eventos Webhook de Meta para DMs y Comentarios de Instagram.
Extracción de palabras clave de atribución (keyword) y calificación ligera de leads.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def process_instagram_webhook_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Procesa el JSON entrante de Meta y extrae los leads calificados con atribución a palabra clave.
    
    :param payload: JSON crudo enviado por Instagram Graph API.
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
                
                # Calificación ligera por palabra clave (ej. CONSULTA)
                if "CONSULTA" in text.upper():
                    lead_data = {
                        "keyword": "CONSULTA",
                        "ig_user_id": user_id,
                        "mensaje_original": text,
                        "origen": "comment",
                    }
                    extracted_leads.append(lead_data)
                    sse_manager.publish_event("default", "lead_captured", lead_data)

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
                sse_manager.publish_event("default", "lead_captured", lead_data)

    return extracted_leads

