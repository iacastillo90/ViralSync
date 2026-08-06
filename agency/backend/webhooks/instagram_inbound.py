"""
backend/webhooks/instagram_inbound.py

Captura DMs y comentarios con palabra clave en tiempo real (AGENTS.md 7.9)
— el motor de conversión del sistema. El Reel no vende, esto es lo que
convierte atención en un lead calificado con atribución al video de origen.

Seguridad (AGENTS.md sección 8, regla explícita):
  "todo endpoint bajo /backend/webhooks/ debe validar la firma
   X-Hub-Signature-256 de Meta antes de procesar el payload, y el
   hub.verify_token del handshake inicial se guarda como variable de
   entorno, nunca en código."

Flujo:
  1. GET  /webhooks/instagram  -> handshake de verificación de Meta.
  2. POST /webhooks/instagram  -> validar firma -> extraer keyword ->
     agente calificador ligero (segundos, no un Crew completo) -> guardar
     lead con atribución completa -> notificar dashboard vía SSE.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.db import get_db_session
from backend.models import Campaign, Lead
from backend.realtime.sse_manager import sse_manager
from agents.qualifier.lead_qualifier import qualify_lead  # agente ligero, NO un Crew completo

router = APIRouter(prefix="/webhooks/instagram", tags=["webhooks"])

APP_SECRET = os.environ["INSTAGRAM_APP_SECRET"]
VERIFY_TOKEN = os.environ["INSTAGRAM_WEBHOOK_VERIFY_TOKEN"]  # nunca hardcodeado, ver AGENTS.md sección 8


@router.get("")
def verify_webhook(
    hub_mode: str | None = None,
    hub_challenge: str | None = None,
    hub_verify_token: str | None = None,
):
    """Handshake de verificación inicial que exige Meta al registrar el webhook."""
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verify token inválido")


def _valid_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Valida X-Hub-Signature-256: sha256=<hmac_hex> calculado con APP_SECRET
    sobre el body crudo. Comparación en tiempo constante (hmac.compare_digest)
    para evitar timing attacks.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


def _extract_keyword_and_text(entry: dict) -> tuple[str | None, str | None, str | None]:
    """
    Devuelve (texto_mensaje, ig_user_id, campo) desde un evento de comment
    o messaging (DM). Instagram Graph API envía estructuras distintas para
    cada uno — se normalizan aquí para que el resto del pipeline no le
    importe el origen.
    """
    changes = entry.get("changes", [])
    if changes:
        value = changes[0].get("value", {})
        texto = value.get("text") or value.get("comment", {}).get("text")
        ig_user_id = value.get("from", {}).get("id")
        return texto, ig_user_id, "comment"

    messaging = entry.get("messaging", [])
    if messaging:
        msg = messaging[0]
        texto = msg.get("message", {}).get("text")
        ig_user_id = msg.get("sender", {}).get("id")
        return texto, ig_user_id, "dm"

    return None, None, None


@router.post("")
async def receive_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None)):
    raw_body = await request.body()

    if not _valid_signature(raw_body, x_hub_signature_256):
        # Nunca se procesa un payload sin firma válida — trátese como
        # endpoint de autenticación (AGENTS.md sección 8).
        raise HTTPException(status_code=403, detail="Firma inválida")

    payload = await request.json()
    db: Session = get_db_session()

    for entry in payload.get("entry", []):
        texto, ig_user_id, origen = _extract_keyword_and_text(entry)
        if not texto or not ig_user_id:
            continue

        # El agente calificador responde en segundos: solo hace matching
        # de keyword contra campañas activas del tenant + arma el contexto
        # de atribución. NUNCA cierra la venta (AGENTS.md 7.9, paso 4).
        result = qualify_lead(texto=texto, entry=entry)
        if result is None:
            continue  # ninguna keyword de campaña activa coincidió — ruido, se descarta

        campaign: Campaign | None = (
            db.query(Campaign)
            .filter(Campaign.keyword == result.keyword, Campaign.status == "active")
            .first()
        )
        if campaign is None:
            continue

        lead = Lead(
            tenant_id=campaign.tenant_id,
            video_id=campaign.video_id,
            keyword=result.keyword,
            ig_user_id=ig_user_id,
            mensaje_original=texto,
            origen=origen,
            calificado_at=datetime.now(timezone.utc),
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        # Notifica al dashboard en tiempo real — el humano toma la
        # conversación real desde aquí (AGENTS.md 7.9, paso 4).
        await sse_manager.publish(
            tenant_id=str(campaign.tenant_id),
            event="new_lead",
            data={
                "lead_id": str(lead.id),
                "video_id": str(lead.video_id),
                "keyword": lead.keyword,
                "mensaje_original": lead.mensaje_original,
            },
        )

    return {"status": "ok"}
