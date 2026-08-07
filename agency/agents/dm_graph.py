"""
dm_graph.py

StateGraph compilado de LangGraph para el procesamiento conversacional de DMs de Instagram.
Gestiona el flujo completo: Consulta RAG -> Clasificación de Confianza -> Auto-Respuesta / Takeover Humano.
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from agents.nodes.dm_response import DMState, node_dm_response
from backend.sse_manager import emit_node_progress

logger = logging.getLogger(__name__)


async def node_send_dm_reply(state: DMState) -> DMState:
    """Envía la respuesta automática generada por el bot al cliente."""
    logger.info(f"[{state['tenant_id']}] Respuesta automática enviada al lead '{state['lead_id']}': {state['reply_text'][:50]}...")
    emit_node_progress(state['tenant_id'], "send_dm_reply", "completed")
    return state


async def node_human_takeover(state: DMState) -> DMState:
    """Pausa la automatización del bot e inicia la notificación de takeover a operador humano."""
    logger.warning(f"[{state['tenant_id']}] Handoff activado para lead '{state['lead_id']}'. Notificando al Dashboard de Inbound Leads...")
    emit_node_progress(state['tenant_id'], "human_approval_takeover", "running")
    return state


def route_after_dm_response(state: DMState) -> str:
    """Enrutador condicional post-respuesta de DM."""
    if state.get("requires_human", False):
        return "human_takeover"
    return "send_dm_reply"


def build_dm_graph():
    """Compila la máquina de estados LangGraph para DMs."""
    workflow = StateGraph(DMState)

    workflow.add_node("dm_response", node_dm_response)
    workflow.add_node("send_dm_reply", node_send_dm_reply)
    workflow.add_node("human_takeover", node_human_takeover)

    workflow.set_entry_point("dm_response")

    workflow.add_conditional_edges(
        "dm_response",
        route_after_dm_response,
        {
            "human_takeover": "human_takeover",
            "send_dm_reply": "send_dm_reply",
        },
    )

    workflow.add_edge("send_dm_reply", END)
    workflow.add_edge("human_takeover", END)

    return workflow.compile()
