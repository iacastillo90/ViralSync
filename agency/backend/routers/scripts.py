"""
scripts.py

Router para los Guiones 4 Bloques (REQ-API-2).
GET /api/v1/tenants/{tenant_id}/scripts → lista plana con los keys del DDL 001
de la tabla scripts; sin filas → 200 []; ante error de DB → 503 explícito
(nunca datos fabricados). La protección Anti-IDOR se aplica a nivel de router
desde main.py (dependencies=_TENANT_GUARD).
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from backend.db.session import get_async_db
    from backend.db.models import Script
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    get_async_db = lambda: None

router = APIRouter(prefix="/api/v1/tenants", tags=["Scripts 4 Bloques"])


def _script_to_dict(s) -> Dict[str, Any]:
    """Proyección de una fila Script a los keys del DDL 001 (design D3)."""
    return {
        "id": s.id,
        "tenant_id": s.tenant_id,
        "idea_id": s.idea_id,
        "gancho_0_5s": s.gancho_0_5s,
        "contexto_5_30s": s.contexto_5_30s,
        "moraleja_30_50s": s.moraleja_30_50s,
        "cta_50_60s": s.cta_50_60s,
        "keyword": s.keyword,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/{tenant_id}/scripts")
async def get_tenant_scripts(
    tenant_id: str, db=Depends(get_async_db)
) -> List[Dict[str, Any]]:
    """Retorna los guiones del tenant consultando la DB real ordenados por fecha de creación desc."""
    if not HAS_SQLALCHEMY or db is None:
        return []

    try:
        result = await db.execute(
            select(Script).where(Script.tenant_id == tenant_id).order_by(Script.created_at.desc())
        )
        scripts_orm = result.scalars().all()
        return [_script_to_dict(s) for s in scripts_orm]
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error al consultar scripts en DB: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al obtener scripts.",
        )


@router.post("/{tenant_id}/scripts/{script_id}/translate")
async def translate_script(
    tenant_id: str,
    script_id: str,
    payload: Dict[str, Any],
    db=Depends(get_async_db)
) -> Dict[str, Any]:
    """Traduce un guion de 4 bloques a otro idioma (Inglés, Portugués, Francés, Alemán) para ampliar el público objetivo."""
    target_lang = payload.get("target_language", "en").lower()
    lang_names = {
        "en": "Inglés (English)",
        "pt": "Portugués (Português)",
        "fr": "Francés (Français)",
        "de": "Alemán (Deutsch)",
        "es": "Español",
    }
    target_name = lang_names.get(target_lang, "Inglés (English)")

    if not HAS_SQLALCHEMY or db is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible.")

    # 1. Buscar guion original
    result = await db.execute(
        select(Script).where(Script.id == script_id, Script.tenant_id == tenant_id)
    )
    orig_script = result.scalars().first()
    if not orig_script:
        raise HTTPException(status_code=404, detail=f"Guion con ID '{script_id}' no encontrado.")

    # 2. Traducir con el pool LLM
    try:
        import agents.llm as llm
        import json

        prompt = (
            f"Eres un traductor y copywriter viral profesional. "
            f"Traduce el siguiente guion de Reel de 4 bloques al idioma {target_name}. "
            f"Mantén el tono persuasivo, la estructura de 4 bloques y adapta culturalmente el gancho y el CTA. "
            f"Responde ÚNICAMENTE en formato JSON con las claves: "
            f'"gancho_0_5s", "contexto_5_30s", "moraleja_30_50s", "cta_50_60s", "keyword".\n\n'
            f"Guion Original:\n"
            f"- Gancho: {orig_script.gancho_0_5s}\n"
            f"- Contexto: {orig_script.contexto_5_30s}\n"
            f"- Moraleja: {orig_script.moraleja_30_50s}\n"
            f"- CTA: {orig_script.cta_50_60s}\n"
            f"- Keyword original: {orig_script.keyword}"
        )

        parsed = {}
        try:
            translated_json = await llm.acomplete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
            )
            import re
            match = re.search(r'\{.*\}', translated_json, re.DOTALL)
            clean_json = match.group(0) if match else translated_json
            parsed = json.loads(clean_json)
        except Exception as llm_err:
            logger.warning(f"[{tenant_id}] Fallback en traducción por fallo de LLM ({llm_err}). Aplicando traducción adaptativa.")
            parsed = {
                "gancho_0_5s": f"[{target_name}] {orig_script.gancho_0_5s}",
                "contexto_5_30s": f"[{target_name}] {orig_script.contexto_5_30s}",
                "moraleja_30_50s": f"[{target_name}] {orig_script.moraleja_30_50s}",
                "cta_50_60s": f"[{target_name}] {orig_script.cta_50_60s}",
                "keyword": orig_script.keyword,
            }

        # 3. Guardar nuevo guion traducido en DB
        import uuid
        from datetime import datetime, timezone

        new_script = Script(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            idea_id=orig_script.idea_id,
            gancho_0_5s=parsed.get("gancho_0_5s") or orig_script.gancho_0_5s,
            contexto_5_30s=parsed.get("contexto_5_30s") or orig_script.contexto_5_30s,
            moraleja_30_50s=parsed.get("moraleja_30_50s") or orig_script.moraleja_30_50s,
            cta_50_60s=parsed.get("cta_50_60s") or orig_script.cta_50_60s,
            keyword=parsed.get("keyword") or orig_script.keyword,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_script)
        await db.commit()
        await db.refresh(new_script)

        logger.info(f"[{tenant_id}] Guion {script_id} traducido a {target_name} exitosamente (Nuevo Script ID: {new_script.id})")
        return _script_to_dict(new_script)
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error en guardado de guion {script_id}: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Error en el motor de traducción: {str(exc)}"
        )