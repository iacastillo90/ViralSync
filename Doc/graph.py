"""
agents/graph.py

Ensambla el StateGraph completo de la agencia (LangGraph).

Un thread_id = un tenant_id: cada tenant tiene su propio hilo de ejecución
persistido en Postgres, lo que permite pausar en los checkpoints humanos
(interrupt_before) y reanudar horas/días después sin perder contexto.

Flujo (ver AGENTS.md sección 1 y 6):

    ingest_niche -> market_map -> ideation -> rum_scoring
        -> human_approval_idea (⏸ interrupt)
        -> scriptwriting
        -> video_edit
        -> human_approval_publish (⏸ interrupt)
        -> publish
        -> metrics_loop (72h, vía Celery beat — dispara re-entrada al grafo)

Reglas de AGENTS.md aplicadas aquí:
  - Todo nodo que publique, gaste presupuesto o escriba en nombre de un
    tenant tiene interrupt_before (sección 8).
  - Los umbrales de RUM y 5/50 no se hardcodean: se leen por nicho desde
    la base de datos (sección 7.1, 7.2).
  - El clasificador Rojo/Amarillo/Verde alimenta la ideación del mes
    siguiente (sección 7.8).
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from agents.nodes import (
    ideation,
    human_approval,
    scriptwriting,
    video_edit,
    publish,
)


# --------------------------------------------------------------------------- #
# Estado compartido del grafo
# --------------------------------------------------------------------------- #

class AgencyState(TypedDict, total=False):
    tenant_id: str
    niche: str

    # mapa de mercado (AGENTS.md 7.7): errores / deseos / objeciones / creencias falsas
    market_map: dict

    # candidatas generadas por el crew de ideación, cada una con su score RUM
    candidate_ideas: Annotated[list[dict], operator.add]

    # umbral RUM dinámico para este nicho (percentil sobre histórico, nunca fijo)
    rum_threshold: float

    approved_idea: dict | None
    idea_approval_status: Literal["pending", "approved", "rejected"]

    script: dict | None  # los 4 bloques (AGENTS.md 7.4)

    raw_video_uri: str | None
    edited_video_uri: str | None

    publish_approval_status: Literal["pending", "approved", "rejected"]
    published_post_id: str | None

    # clasificación tras el loop de métricas a 72h (AGENTS.md 7.8)
    classification: Literal["rojo", "amarillo", "verde", None]

    errors: Annotated[list[str], operator.add]


# --------------------------------------------------------------------------- #
# Nodos de control (no hacen trabajo de negocio, solo enrutan)
# --------------------------------------------------------------------------- #

def route_after_idea_approval(state: AgencyState) -> str:
    if state.get("idea_approval_status") == "approved":
        return "scriptwriting"
    if state.get("idea_approval_status") == "rejected":
        return "ideation"  # vuelve a generar ideas para este nicho
    return END  # sigue pausado esperando al humano


def route_after_publish_approval(state: AgencyState) -> str:
    if state.get("publish_approval_status") == "approved":
        return "publish"
    if state.get("publish_approval_status") == "rejected":
        return "video_edit"  # vuelve a editar
    return END


# --------------------------------------------------------------------------- #
# Construcción del grafo
# --------------------------------------------------------------------------- #

def build_agency_graph(checkpointer: PostgresSaver) -> StateGraph:
    graph = StateGraph(AgencyState)

    graph.add_node("ideation", ideation.run)                       # ideation.py: crew + Buscar_Tendencias_SearXNG + filtro 5/50 + RUM
    graph.add_node("human_approval_idea", human_approval.review_idea)
    graph.add_node("scriptwriting", scriptwriting.run)
    graph.add_node("video_edit", video_edit.run)                   # encola job de Celery, espera silencios/subs/B-roll/SFX
    graph.add_node("human_approval_publish", human_approval.review_publish)
    graph.add_node("publish", publish.run)                         # Instagram Graph API oficial — nunca browser-use

    graph.set_entry_point("ideation")

    graph.add_edge("ideation", "human_approval_idea")

    graph.add_conditional_edges(
        "human_approval_idea",
        route_after_idea_approval,
        {"scriptwriting": "scriptwriting", "ideation": "ideation", END: END},
    )

    graph.add_edge("scriptwriting", "video_edit")
    graph.add_edge("video_edit", "human_approval_publish")

    graph.add_conditional_edges(
        "human_approval_publish",
        route_after_publish_approval,
        {"publish": "publish", "video_edit": "video_edit", END: END},
    )

    graph.add_edge("publish", END)

    # Checkpoints humanos obligatorios (AGENTS.md sección 8): el grafo se
    # pausa ANTES de ejecutar estos nodos y espera una señal externa
    # (POST /tenants/{id}/approve) que actualiza idea_approval_status o
    # publish_approval_status y luego llama graph.invoke(None, config) para
    # reanudar el mismo thread_id.
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval_idea", "human_approval_publish", "publish"],
    )
    return compiled


def get_thread_config(tenant_id: str) -> dict:
    """thread_id = tenant_id -> persistencia de estado aislada por cliente."""
    return {"configurable": {"thread_id": tenant_id}}
