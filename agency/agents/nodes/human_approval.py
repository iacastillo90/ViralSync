"""
Nodos de checkpoint humano (AGENTS.md sección 8: "un bug si no lo pausas").

Estos nodos nunca se ejecutan realmente: graph.py los declara en
interrupt_before, así que LangGraph pausa el thread justo ANTES de entrar
aquí. El dashboard (vía SSE, ver backend/realtime/sse_manager.py) muestra
"Esperando aprobación" y el humano responde con:

    POST /tenants/{tenant_id}/ideas/approve   {"status": "approved"}
    POST /tenants/{tenant_id}/publish/approve {"status": "approved"}

que actualiza el state (idea_approval_status / publish_approval_status) y
llama graph.invoke(None, config=get_thread_config(tenant_id)) para reanudar.

Si el grafo alguna vez ejecuta el cuerpo de estas funciones significa que
el interrupt_before no se configuró — tratar como bug crítico.
"""


def review_idea(state: dict) -> dict:  # pragma: no cover - no debería ejecutarse
    return state


def review_publish(state: dict) -> dict:  # pragma: no cover - no debería ejecutarse
    return state
