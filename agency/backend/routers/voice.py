"""
voice.py

Router Voice Personas (S2a — REQ-VOICE-04):
- GET /api/v1/tenants/{tenant_id}/voice-personas → catálogo de personas activas
  (is_active=true) con voz por motor (edge_tts_voice + json2video_voice) y el
  mapa locale_voices para el render por idioma (REQ-VOICE-05).
- PATCH /api/v1/tenants/{tenant_id}/scripts/{script_id}/voice-persona con body
  {"voice_persona_id": uuid} → persiste la persona del guion en
  `scripts.voice_persona_id`.

El catálogo voice_personas es global (sin tenant_id, migración 012); el guard
Anti-IDOR se aplica a nivel de router desde main.py (dependencies=_TENANT_GUARD).
"""

import logging
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import VoicePersona, Script
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    get_async_db = lambda: None

router = APIRouter(prefix="/api/v1/tenants", tags=["Voice Personas"])


class VoicePersonaPatchReq(BaseModel):
    voice_persona_id: str


def _persona_to_dict(p) -> Dict[str, Any]:
    """Proyección de una fila VoicePersona al contrato de la API (REQ-VOICE-01/04)."""
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "edge_tts_voice": p.edge_tts_voice,
        "json2video_voice": p.json2video_voice,
        "locale_voices": p.locale_voices or {},
        "is_active": p.is_active,
    }


@router.get("/{tenant_id}/voice-personas")
async def list_voice_personas(
    tenant_id: str,
    db=Depends(get_async_db),
) -> List[Dict[str, Any]]:
    """Lista las personas de voz activas (is_active=true) con ambos voices por motor."""
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    try:
        result = await db.execute(
            select(VoicePersona)
            .where(VoicePersona.is_active.is_(True))
            .order_by(VoicePersona.name)
        )
        return [_persona_to_dict(p) for p in result.scalars().all()]
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error listando voice personas: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al listar personas de voz.",
        )


@router.patch("/{tenant_id}/scripts/{script_id}/voice-persona")
async def set_script_voice_persona(
    tenant_id: str,
    script_id: str,
    req: VoicePersonaPatchReq,
    db=Depends(get_async_db),
) -> Dict[str, Any]:
    """Persiste la persona de voz del guion (`scripts.voice_persona_id`).

    Valida que la persona exista en el catálogo (404) y que el guion pertenezca
    al tenant (404); ante error de DB responde 503 — nunca datos fabricados.
    """
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    try:
        persona = (
            await db.execute(
                select(VoicePersona).where(VoicePersona.id == req.voice_persona_id)
            )
        ).scalars().first()
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Persona de voz no encontrada.",
            )

        script = (
            await db.execute(
                select(Script).where(
                    Script.id == script_id, Script.tenant_id == tenant_id
                )
            )
        ).scalars().first()
        if not script:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guion no encontrado o no pertenece al tenant.",
            )

        script.voice_persona_id = persona.id
        await db.commit()
        await db.refresh(script)

        return {
            "script_id": script.id,
            "voice_persona_id": script.voice_persona_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"[{tenant_id}] Error asignando persona de voz a script {script_id}: {exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal al asignar la persona de voz.",
        )