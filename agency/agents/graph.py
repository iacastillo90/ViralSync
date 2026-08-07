"""
graph.py

Orquestador Principal StateGraph de LangGraph para ViralSync.
Aislamiento Multi-Tenant: thread_id = tenant_id.
Checkpoints Manuales: interrupt_before=["human_approval_idea", "human_approval_publish"]
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from agents.nodes.ideation import node_ideation
from agents.nodes.human_approval import (
    node_human_approval_idea,
    node_human_approval_publish,
)
from agents.nodes.scriptwriting import node_scriptwriting
from agents.nodes.video_edit import node_video_edit
from agents.nodes.publish import node_publish

class AgencyState(TypedDict, total=False):
    """Estado global del flujo de trabajo de la agencia para un tenant."""
    tenant_id: str
    niche: str
    niche_ppp: str
    market_map: Dict[str, Any]
    ideas: List[Dict[str, Any]]
    selected_idea: Dict[str, Any]
    idea_approved: bool
    script: Dict[str, Any]
    product_image_url: str
    business_type: str
    video_storyboard: List[Dict[str, Any]]
    raw_video_uri: str
    edited_video_uri: str
    publish_approved: bool
    published_post_id: str
    logs: List[str]

def build_agency_graph(checkpointer=None):
    """
    Construye y retorna el StateGraph compilado de la agencia con checkpoints humanos.
    """
    builder = StateGraph(AgencyState)

    # 1. Registrar nodos
    builder.add_node("ideation", node_ideation)
    builder.add_node("human_approval_idea", node_human_approval_idea)
    builder.add_node("scriptwriting", node_scriptwriting)
    builder.add_node("video_edit", node_video_edit)
    builder.add_node("human_approval_publish", node_human_approval_publish)
    builder.add_node("publish", node_publish)

    # 2. Conectar aristas secuenciales
    builder.set_entry_point("ideation")
    builder.add_edge("ideation", "human_approval_idea")
    builder.add_edge("human_approval_idea", "scriptwriting")
    builder.add_edge("scriptwriting", "video_edit")
    builder.add_edge("video_edit", "human_approval_publish")
    builder.add_edge("human_approval_publish", "publish")
    builder.add_edge("publish", END)

    # 3. Compilar grafo registrando pausas en checkpoints humanos
    app = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval_idea", "human_approval_publish"]
    )
    return app
