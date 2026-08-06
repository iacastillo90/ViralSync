"""
Nodo de ideación (AGENTS.md 7.1, 7.2, 7.7).

Orden de operaciones (barato -> caro, para no gastar tokens de más):
  1. Crew genera N ideas crudas contrastadas contra los 4 cuadrantes de
     competencia (on-nicho/off-nicho x on-plataforma/off-plataforma) usando
     la tool MCP de SearXNG — nunca inventa patrones sin verificarlos.
  2. Filtro 5/50 (gate binario, sin LLM de scoring): descarta antes de
     gastar en RUM.
  3. Scoring RUM completo solo a lo que sobrevivió el filtro.
  4. Se compara contra rum_threshold, calculado como percentil sobre el
     histórico de RUM del propio nicho (nunca una constante hardcodeada).
"""

from agents.crews.ideation_crew import build_ideation_crew
from agents.nodes import market_rum  # helper de persistencia/umbral (DB)


def _passes_5_50(idea: dict) -> bool:
    return bool(idea.get("entendible_nino_5_anos")) and bool(idea.get("interesa_50_de_100"))


def run(state: dict) -> dict:
    tenant_id = state["tenant_id"]
    niche = state["niche"]
    market_map = state.get("market_map", {})

    crew = build_ideation_crew(tenant_id=tenant_id, niche=niche, market_map=market_map)
    raw_ideas = crew.kickoff()  # lista de dicts: {"texto":..., "gancho":..., "entendible_nino_5_anos":..., "interesa_50_de_100":...}

    survivors = [i for i in raw_ideas if _passes_5_50(i)]

    threshold = market_rum.get_dynamic_threshold(tenant_id=tenant_id, niche=niche)

    scored = []
    for idea in survivors:
        u, i_, c, s, d, a = (
            idea["universalidad"],
            idea["intensidad"],
            idea["claridad"],
            idea["shareability"],
            idea["distribucion"],
            idea["alineacion"],
        )
        rum = u * i_ * c * s * d * a
        idea["rum_score"] = rum
        idea["passes_threshold"] = rum >= threshold
        scored.append(idea)

    return {
        "candidate_ideas": [i for i in scored if i["passes_threshold"]],
        "rum_threshold": threshold,
        "idea_approval_status": "pending",
    }
