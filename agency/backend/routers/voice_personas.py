"""
voice_personas.py

Router backend para la selección y gestión de Voice Personas (Locutores IA) por tenant.
Permite consultar el catálogo de voces disponibles y asignar la voz de marca del cliente.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select, update
from backend.db.models import Tenant
from backend.db.session import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Voice Personas"])

DATA_PATH = Path(__file__).parent.parent / "data" / "voice_personas.json"


class SetVoicePersonaReq(BaseModel):
    voice_code: str
    voice_name: Optional[str] = None


@router.get("/voice-personas")
async def list_voice_personas() -> List[Dict[str, Any]]:
    """Retorna el catálogo completo de 8 Voice Personas disponibles."""
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="Archivo de catálogo de voces no encontrado.")
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error(f"Error cargando catálogo de voces: {exc}")
        raise HTTPException(status_code=500, detail="Error leyendo voces.")


@router.post("/tenants/{tenant_id}/voice-persona")
async def set_tenant_voice_persona(
    tenant_id: str,
    req: SetVoicePersonaReq,
    db=Depends(get_async_db)
) -> Dict[str, Any]:
    """Asigna la voz oficial de marca para el tenant especificado."""
    try:
        res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = res.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado.")

        # Guardar en DB
        await db.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(litellm_virtual_key=req.voice_code)  # Usamos campo de preferencia
        )
        await db.commit()

        logger.info(f"[{tenant_id}] Voz de marca actualizada a: {req.voice_code}")
        return {
            "status": "success",
            "tenant_id": tenant_id,
            "voice_code": req.voice_code,
            "voice_name": req.voice_name or req.voice_code,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error asignando voz de marca: {exc}")
        raise HTTPException(status_code=500, detail="Error al guardar voz de marca.")
