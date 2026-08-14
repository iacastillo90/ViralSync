"""
scriptwriting.py

Nodo de Guionismo de LangGraph.
Ejecuta la crew de guionismo de 4 bloques a partir de la idea aprobada y
persiste el guion vía DAO (design D3): `insert_script` escribe la fila `scripts`
con FK a la idea aprobada y el `id` resultante se inyecta en `script["id"]` de
state para que `node_video_edit` pueda FK la fila `videos` (REQ-PERSIST-02).
"""

import logging
from typing import Dict, Any
from agents.crews.scriptwriting_crew import run_scriptwriting_crew
from backend.db.daos import insert_script, get_script_by_idea

logger = logging.getLogger(__name__)


def _script_row_to_dict(row) -> Dict[str, Any]:
    """Proyección de una fila Script al dict de los 4 bloques (mismo shape que
    devuelve `run_scriptwriting_crew`, design D3) para reutilizar un guion
    existente en la reactivación sin romper el contrato con node_video_edit."""
    return {
        "id": row.id,
        "idea_id": row.idea_id,
        "gancho_0_5s": row.gancho_0_5s,
        "contexto_5_30s": row.contexto_5_30s,
        "moraleja_30_50s": row.moraleja_30_50s,
        "cta_50_60s": row.cta_50_60s,
        "keyword": row.keyword,
    }


def _resolve_selected_idea(state: Dict[str, Any]) -> Dict[str, Any]:
    """Resuelve la idea a guionear.

    PHASE-2: el resume de `approve_idea` inyecta `selected_idea_id` (UUID de la
    idea aprobada). Si llega, se busca el dict COMPLETO dentro de `state["ideas"]`
    para que la crew use el texto/gancho de ESA idea y el FK apunte a ella.
    Fallback sin señal explícita: `state["selected_idea"]` (ideas[0] de ideation).
    """
    selected_idea = state.get("selected_idea", {})
    selected_idea_id = state.get("selected_idea_id")
    if selected_idea_id:
        for idea in state.get("ideas") or []:
            if str(idea.get("id")) == str(selected_idea_id):
                return idea
        logger.warning(
            f"[{state.get('tenant_id', 'default_tenant')}] selected_idea_id "
            f"'{selected_idea_id}' sin match en state['ideas']; fallback a "
            f"selected_idea actual."
        )
    # Defensa: si por un flujo legacy selected_idea llegara como id string
    # (front), normalizar a dict antes de llamar a .get("id").
    if isinstance(selected_idea, str):
        selected_idea = {"id": selected_idea}
    return selected_idea


async def node_scriptwriting(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que genera el guion en 4 bloques y lo persiste."""
    tenant_id = state.get("tenant_id", "default_tenant")
    selected_idea = _resolve_selected_idea(state)
    niche_ppp = state.get("niche_ppp", "")

    logger.info(f"[{tenant_id}] Ejecutando nodo 'scriptwriting'")

    # D-D (REQ-PTT-03, defensa en profundidad): sin `selected_idea.id` no hay
    # idea aprobada para FK → error honesto ANTES de llamar a insert_script
    # (nunca IntegrityError por idea_id NULL).
    if not selected_idea.get("id"):
        raise ValueError(
            f"[{tenant_id}] selected_idea sin 'id': no hay idea aprobada para FK."
        )

    logs = state.get("logs", [])

    # PHASE-2 (dedup reactivación): si la idea ya tiene guion (corrida ya
    # terminada re-aprobada), se reutiliza — no se duplica fila ni se gasta LLM.
    existing = await get_script_by_idea(tenant_id, selected_idea.get("id"))
    if existing is not None:
        script = _script_row_to_dict(existing)
        logs.append(
            f"[scriptwriting] Guion existente reutilizado para idea '{selected_idea.get('id')}' (dedup reactivación)"
        )
        logger.info(f"[{tenant_id}] Guion reutilizado para idea '{selected_idea.get('id')}'")
        return {
            "script": script,
            "selected_idea": selected_idea,
            "logs": logs,
        }

    script = await run_scriptwriting_crew(
        idea=selected_idea, 
        niche_ppp=niche_ppp,
        product_name=state.get("product_name"),
        product_description=state.get("product_description"),
        target_duration=state.get("target_duration", 30),
    )

    # Persistencia real (PERSIST-02): fila `scripts` FK a la idea aprobada. Un
    # fallo de DB se propaga (PERSIST-02-2). El id del guion se inyecta en state
    # para que video_edit pueda FK (design D3).
    row = await insert_script(tenant_id, selected_idea.get("id"), script)
    script["id"] = row.id

    logs.append(f"[scriptwriting] Guion de 4 bloques generado con palabra clave '{script.get('keyword')}'")

    return {
        "script": script,
        "selected_idea": selected_idea,
        "logs": logs,
    }