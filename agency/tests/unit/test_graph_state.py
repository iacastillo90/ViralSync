"""
test_graph_state.py

Pruebas unitarias TDD para el orquestador StateGraph de LangGraph.
"""

from agents.graph import build_agency_graph, AgencyState


def test_build_agency_graph_compiles():
    app = build_agency_graph()
    assert app is not None


def test_agency_state_initialization():
    initial_state: AgencyState = {
        "tenant_id": "tenant_test_123",
        "niche": "Negocios B2B y SaaS",
        "logs": [],
    }
    assert initial_state["tenant_id"] == "tenant_test_123"
    assert initial_state["niche"] == "Negocios B2B y SaaS"
    assert isinstance(initial_state["logs"], list)
