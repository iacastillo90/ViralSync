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
from backend.db.daos import insert_script

logger = logging.getLogger(__name__)


async def node_scriptwriting(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que genera el guion en 4 bloques y lo persiste."""
    tenant_id = state.get("tenant_id", "default_tenant")
    selected_idea = state.get("selected_idea", {})
    niche_ppp = state.get("niche_ppp", "")

    logger.info(f"[{tenant_id}] Ejecutando nodo 'scriptwriting'")

    # D-D (REQ-PTT-03, defensa en profundidad): sin `selected_idea.id` no hay
    # idea aprobada para FK → error honesto ANTES de llamar a insert_script
    # (nunca IntegrityError por idea_id NULL).
    if not selected_idea.get("id"):
        raise ValueError(
            f"[{tenant_id}] selected_idea sin 'id': no hay idea aprobada para FK."
        )

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

    logs = state.get("logs", [])
    logs.append(f"[scriptwriting] Guion de 4 bloques generado con palabra clave '{script.get('keyword')}'")

    return {
        "script": script,
        "logs": logs,
    }