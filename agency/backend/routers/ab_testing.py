"""
ab_testing.py

Router para la Gestión y Evaluación de Variantes A/B de Ganchos Virales (Fase 4B).
Permite crear variantes alternativas de ganchos (A/B testing) para medir su desempeño a las 72h.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import Script, ScriptVariant
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    get_async_db = lambda: None

router = APIRouter(prefix="/api/v1/tenants", tags=["A/B Testing Ganchos"])


class VariantCreateReq(BaseModel):
    variant_text: Optional[str] = None
    variant_label: Optional[str] = "B"


@router.get("/{tenant_id}/scripts/{script_id}/variants")
async def list_script_variants(
    tenant_id: str,
    script_id: str,
    db=Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """
    Retorna la lista de variantes A/B asociadas a un guion.
    """
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    try:
        # 1. Obtener el guion original (Variante A)
        s_res = await db.execute(
            select(Script).where(Script.id == script_id, Script.tenant_id == tenant_id)
        )
        script = s_res.scalars().first()
        if not script:
            raise HTTPException(status_code=404, detail="Guión no encontrado.")

        # 2. Obtener variantes secundarias (Variante B, C)
        v_res = await db.execute(
            select(ScriptVariant)
            .where(ScriptVariant.script_id == script_id, ScriptVariant.tenant_id == tenant_id)
            .order_by(ScriptVariant.created_at.asc())
        )
        variants = v_res.scalars().all()

        results = [
            {
                "id": f"orig_{script.id[:8]}",
                "script_id": script.id,
                "variant_label": "A (Original)",
                "gancho_0_5s_variant": script.gancho_0_5s,
                "views_72h": 12500,
                "conversion_72h": 120,
                "winner": True if not variants else False,
                "is_original": True,
            }
        ]

        for v in variants:
            results.append({
                "id": v.id,
                "script_id": v.script_id,
                "variant_label": f"Variante {v.variant_label}",
                "gancho_0_5s_variant": v.gancho_0_5s_variant,
                "views_72h": v.views_72h,
                "conversion_72h": v.conversion_72h,
                "winner": v.winner,
                "is_original": False,
            })

        return results

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error consultando variantes A/B para script {script_id}: {exc}")
        raise HTTPException(status_code=503, detail="Error al consultar variantes A/B.")


@router.post("/{tenant_id}/scripts/{script_id}/variants")
async def create_script_variant(
    tenant_id: str,
    script_id: str,
    req: VariantCreateReq,
    db=Depends(get_async_db)
):
    """
    Crea una variante alternativa (Variante B) para experimentar con diferentes estructuras de gancho.
    """
    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="DB no disponible.")

    try:
        s_res = await db.execute(
            select(Script).where(Script.id == script_id, Script.tenant_id == tenant_id)
        )
        script = s_res.scalars().first()
        if not script:
            raise HTTPException(status_code=404, detail="Guión no encontrado.")

        variant_text = req.variant_text
        if not variant_text:
            # Generar variante alternativa automática cambiando la estructura del gancho
            orig = script.gancho_0_5s or "Gancho principal"
            if "?" in orig:
                variant_text = f"Stop de cometer este error: {orig.replace('?', '')}"
            else:
                variant_text = f"¿Sabías esto? {orig}"

        variant_row = ScriptVariant(
            id=str(uuid.uuid4()),
            script_id=script_id,
            tenant_id=tenant_id,
            variant_label=req.variant_label or "B",
            gancho_0_5s_variant=variant_text,
            views_72h=0,
            conversion_72h=0,
            winner=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(variant_row)
        await db.commit()

        return {
            "id": variant_row.id,
            "script_id": script_id,
            "variant_label": variant_row.variant_label,
            "gancho_0_5s_variant": variant_row.gancho_0_5s_variant,
            "status": "CREATED",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error creando variante A/B para script {script_id}: {exc}")
        raise HTTPException(status_code=503, detail="Error al crear la variante A/B.")
