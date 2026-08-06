"""
Nodo de guion (AGENTS.md 7.3 PPP + 7.4 estructura de 4 bloques + 7.5 personaje de marca).

El personaje de marca (7.5) se recupera vía RAG (rag_mcp_server) y se
inyecta como contexto fijo — no se regenera por video, se genera una vez
por tenant en el onboarding y se reutiliza para mantener congruencia.

Regla explícita a reforzar en el prompt del guionista_agent: el bloque de
contexto (5s-30s) NUNCA debe adelantar la respuesta del bloque de
moraleja — su función es alargar retención, no informar.
"""

from agents.crews.scriptwriting_crew import build_scriptwriting_crew


def run(state: dict) -> dict:
    tenant_id = state["tenant_id"]
    idea = state["approved_idea"] or state["candidate_ideas"][0]

    crew = build_scriptwriting_crew(tenant_id=tenant_id, idea=idea)
    script = crew.kickoff()

    # Validación estructural mínima antes de pasar a producción
    required_blocks = {"gancho_0_5s", "contexto_5_30s", "moraleja_30_50s", "cta_50_60s"}
    missing = required_blocks - set(script.keys())
    if missing:
        return {"errors": [f"Guion incompleto, faltan bloques: {missing}"]}

    return {"script": script}
