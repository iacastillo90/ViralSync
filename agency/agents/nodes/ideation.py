"""
ideation.py

Nodo de Ideación de LangGraph (async).
Ejecuta la crew de ideación de 4 cuadrantes y persiste las candidatas vía DAO
(design D3/D8): tras producir el contenido, `insert_ideas` escribe una fila por
candidata y el `id` (UUID generado por el DAO) viaja de vuelta en cada dict de
state para que scriptwriting pueda FK y approve pueda UPDATE (REQ-PERSIST-02).

La escritura es parte de la unidad de trabajo del nodo: un fallo de DB se
propaga (REQ-PERSIST-02-2) — nunca un éxito state-only con errores tragados.
Con `product_image_url` en state se persiste también la fila `products`
(vía `upsert_product`) para el flujo IMAGE_TO_VIDEO (design D8 / PERSIST-05).
"""

import logging
from typing import Dict, Any
from agents.crews.ideation_crew import run_ideation_crew
from backend.db.daos import insert_ideas, upsert_product

logger = logging.getLogger(__name__)


async def node_ideation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que genera ideas de contenido viral para el tenant y las persiste."""
    tenant_id = state.get("tenant_id", "default_tenant")
    niche = state.get("niche", "Negocios B2B y SaaS")
    market_map = state.get("market_map", {})

    logger.info(f"[{tenant_id}] Ejecutando nodo 'ideation' para nicho '{niche}'")

    ideas = await run_ideation_crew(niche=niche, market_map=market_map)
    selected_idea = ideas[0] if ideas else {}

    # Persistencia real (PERSIST-02): una fila `ideas` por candidata. El id del
    # DAO se inyecta en cada dict + selected_idea (design D3). Un fallo de DB se
    # propaga (PERSIST-02-2), nunca un éxito state-only.
    if ideas:
        rows = await insert_ideas(tenant_id, ideas)
        for idea, row in zip(ideas, rows):
            idea["id"] = row.id
        selected_idea["id"] = ideas[0]["id"]

    # PERSIST-05 / D8: si el run viene con foto de producto (IMAGE_TO_VIDEO),
    # persiste la fila `products`; sin producto el pipeline sigue (TEXT_TO_VIDEO).
    product_image_url = state.get("product_image_url", "")
    if product_image_url:
        await upsert_product(
            tenant_id,
            {
                "name": state.get("product_name") or state.get("niche", "General"),
                "description": state.get("product_description", ""),
                "product_image_url": product_image_url,
            },
        )

    logs = state.get("logs", [])
    logs.append(f"[ideation] Generadas {len(ideas)} ideas RUM para tenant '{tenant_id}'")

    return {
        "ideas": ideas,
        "selected_idea": selected_idea,
        "logs": logs,
    }