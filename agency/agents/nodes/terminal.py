"""
terminal.py

Nodos terminales del grafo (design D-C, REQ-PTT-02).

`node_term_rejected` materializa el terminal DISTINTO del éxito: cuando un
checkpoint humano recibe rechazo (`idea_rejected`/`publish_rejected`) el grafo
converge acá y va directo a END. El rechazo es FINAL por run — no hay camino de
vuelta a scriptwriting/publish; re-aprobar exige un run nuevo.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def node_term_rejected(state: Dict[str, Any]) -> Dict[str, Any]:
    """Terminal de rechazo: marca `terminal_state="term_rejected"` (→ END)."""
    tenant_id = state.get("tenant_id", "default_tenant")
    logs = state.get("logs", [])
    logs.append(
        f"[term_rejected] Run rechazado y terminado (FINAL) para tenant '{tenant_id}'"
    )
    return {"terminal_state": "term_rejected", "logs": logs}