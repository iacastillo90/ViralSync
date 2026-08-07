"""
dm_response.py

Nodo del Grafo Conversacional de DMs de Instagram (LangGraph).
Evalúa la intención del mensaje entrante, consulta la base de conocimientos RAG de Qdrant,
calcula el puntaje de confianza e inicia automáticamente el handoff a operador humano cuando se requiere.
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from typing_extensions import TypedDict
from agents.mcp_servers.rag_mcp_server import query_rag_knowledge
from backend.sse_manager import emit_node_progress

logger = logging.getLogger(__name__)

CONFIDENCE_HUMAN_THRESHOLD = 0.75


class DMState(TypedDict):
    tenant_id: str
    lead_id: str
    incoming_message: str
    conversation_history: List[Dict[str, str]]
    rag_context: str
    reply_text: str
    confidence_score: float
    intent: str  # question | objection | purchase_intent | spam | unclear
    requires_human: bool


def classify_intent(message: str) -> str:
    """Clasifica la intención del mensaje entrante."""
    msg_lower = message.lower()

    if any(word in msg_lower for word in ["comprar", "precio", "demo", "contratar", "quiero el sistema"]):
        return "purchase_intent"
    elif any(word in msg_lower for word in ["caro", "duda", "funciona realmente", "pero"]):
        return "objection"
    elif any(word in msg_lower for word in ["como", "cuando", "donde", "que es", "informacion"]):
        return "question"
    elif any(word in msg_lower for word in ["http", "crypto", "win money", "casino"]):
        return "spam"
    return "unclear"


def generate_grounded_reply(message: str, rag_context: str) -> tuple[str, float]:
    """Genera una respuesta basada en el RAG y estima la confianza de la respuesta."""
    if not rag_context or "no se encontro" in rag_context.lower():
        reply = "Gracias por escribirnos. Un especialista humano se pondrá en contacto contigo en breve para darte respuesta exacta."
        confidence = 0.50
    else:
        reply = f"¡Hola! Sobre tu consulta: {message[:30]}... Te confirmo que en nuestro sistema {rag_context[:100]}... ¿Te gustaría ver una demo?"
        confidence = 0.88

    return reply, confidence


async def node_dm_response(state: DMState) -> DMState:
    """
    Nodo ejecutable de LangGraph para el procesamiento conversacional de DMs.
    """
    tenant_id = state.get("tenant_id", "default_tenant")
    lead_id = state.get("lead_id", "lead-unknown")
    incoming_msg = state.get("incoming_message", "")

    logger.info(f"[{tenant_id}] Procesando DM entrante del lead '{lead_id}': '{incoming_msg[:40]}'")
    emit_node_progress(tenant_id, "dm_processing", "running")

    # 1. Clasificación de Intención
    intent = classify_intent(incoming_msg)

    # 2. Consulta de Contexto RAG en Qdrant
    rag_docs = query_rag_knowledge(query=incoming_msg)
    rag_context = "\n".join([doc.get("content", "") for doc in rag_docs if isinstance(doc, dict)])

    # 3. Generación de Respuesta grounded y Score de Confianza
    reply_text, confidence = generate_grounded_reply(incoming_msg, rag_context)

    # 4. Evaluación de Handoff a Humano
    requires_human = (
        confidence < CONFIDENCE_HUMAN_THRESHOLD
        or intent in ["objection", "purchase_intent"]
    )

    if requires_human:
        logger.warning(f"[{tenant_id}] Escalando DM del lead '{lead_id}' a operador humano (Intención: {intent}, Confianza: {confidence})")
        emit_node_progress(tenant_id, "human_takeover_triggered", "completed")

    return {
        "tenant_id": tenant_id,
        "lead_id": lead_id,
        "incoming_message": incoming_msg,
        "conversation_history": state.get("conversation_history", []),
        "rag_context": rag_context,
        "reply_text": reply_text,
        "confidence_score": confidence,
        "intent": intent,
        "requires_human": requires_human,
    }
