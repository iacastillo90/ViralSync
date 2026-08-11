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
from agents.nodes.terminal import node_term_rejected

class AgencyState(TypedDict, total=False):
    """Estado global del flujo de trabajo de la agencia para un tenant."""
    tenant_id: str
    niche: str
    niche_ppp: str
    market_map: Dict[str, Any]
    ideas: List[Dict[str, Any]]
    selected_idea: Dict[str, Any]
    idea_approved: bool
    idea_rejected: bool
    script: Dict[str, Any]
    product_image_url: str
    # PERSIST-05-1 / D-5: key estable del objeto en MinIO (no la URL presignada).
    # Viaja del request → state → node_ideation (persiste) → node_video_edit
    # (re-firma en cada lectura, SH-05-3; filas legacy NULL → fallback SH-05-4).
    product_object_key: str
    business_type: str
    video_storyboard: List[Dict[str, Any]]
    raw_video_uri: str
    edited_video_uri: str
    video_id: str
    publish_approved: bool
    publish_rejected: bool
    published_post_id: str
    logs: List[str]
    terminal_state: str

def _route_after_idea_approval(state: Dict[str, Any]) -> str:
    """D-B/D-C (REQ-PTT-02): bifurcación del checkpoint de idea.

    - `idea_rejected` positivo → "rejected" (terminal term_rejected).
    - `idea_approved` positivo → "approved" (scriptwriting, vía intacta PTT-02-3).
    - sin señal positiva (payload malformado) → "pending" (self → re-pausa).

    `idea_approved: False`/ausente JAMÁS se interpreta como rechazo — nunca
    confundir "not yet" con una decisión humana (D-B).
    """
    if state.get("idea_rejected"):
        return "rejected"
    if state.get("idea_approved"):
        return "approved"
    return "pending"


def _route_after_publish_approval(state: Dict[str, Any]) -> str:
    """D-B/D-C (REQ-PTT-02): bifurcación del checkpoint de publicación (idem)."""
    if state.get("publish_rejected"):
        return "rejected"
    if state.get("publish_approved"):
        return "approved"
    return "pending"


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
    builder.add_node("term_rejected", node_term_rejected)

    # 2. Conectar aristas secuenciales
    builder.set_entry_point("ideation")
    builder.add_edge("ideation", "human_approval_idea")
    builder.add_edge("scriptwriting", "video_edit")
    builder.add_edge("video_edit", "human_approval_publish")
    builder.add_edge("publish", END)
    builder.add_edge("term_rejected", END)

    # 2b. D-C (REQ-PTT-02): aristas CONDICIONALES tras cada checkpoint humano —
    # approved→next, rejected→term_rejected (FINAL), pending→self (re-pausa).
    builder.add_conditional_edges(
        "human_approval_idea",
        _route_after_idea_approval,
        {
            "approved": "scriptwriting",
            "rejected": "term_rejected",
            "pending": "human_approval_idea",
        },
    )
    builder.add_conditional_edges(
        "human_approval_publish",
        _route_after_publish_approval,
        {
            "approved": "publish",
            "rejected": "term_rejected",
            "pending": "human_approval_publish",
        },
    )

    # 3. Compilar grafo registrando pausas en checkpoints humanos
    app = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval_idea", "human_approval_publish"]
    )
    return app
