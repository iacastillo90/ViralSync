"""
test_graph_execution_resilience.py

Focused tests for RESILIENCE-002 (WU-FIX-4):
1. A background graph failure now logs via the structured logger and emits an
   SSE ``graph_error`` event (thread_id + message) instead of a bare print —
   the frontend is no longer left waiting for a signal that never arrives.
2. The three handlers no longer contain print() calls.
"""

import pytest

from backend.routers import graph_execution
from backend.routers.graph_execution import _resume_graph_background, _run_graph_background


class _FakeSSE:
    def __init__(self):
        self.broadcasts = []
        self.graph_errors = []

    async def broadcast(self, tenant_id, event_type, data):
        self.broadcasts.append((tenant_id, event_type, data))

    async def emit_graph_error(self, tenant_id, message):
        self.graph_errors.append((tenant_id, message))


class _FakeGraph:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    async def ainvoke(self, state, config=None):
        if self.error:
            raise self.error
        return self.result


@pytest.mark.anyio
async def test_run_graph_failure_emits_graph_error_event(monkeypatch):
    """RESILIENCE-002: fallo en background -> SSE graph_error con thread_id+message."""
    fake_sse = _FakeSSE()
    monkeypatch.setattr(graph_execution, "sse_manager", fake_sse)
    monkeypatch.setattr(graph_execution, "build_agency_graph", lambda *a, **kw: _FakeGraph(error=RuntimeError("boom")))

    await _run_graph_background("tenant-resil-1", {"tenant_id": "tenant-resil-1"})

    assert fake_sse.graph_errors == [("tenant-resil-1", "boom")]
    assert fake_sse.broadcasts == []  # nunca emite graph_complete cuando falla


@pytest.mark.anyio
async def test_run_graph_success_broadcasts_complete(monkeypatch):
    fake_sse = _FakeSSE()
    monkeypatch.setattr(graph_execution, "sse_manager", fake_sse)
    monkeypatch.setattr(
        graph_execution,
        "build_agency_graph",
        lambda *a, **kw: _FakeGraph(result={"ideas": ["i1", "i2", "i3"], "tenant_id": "t"}),
    )

    await _run_graph_background("tenant-ok", {"tenant_id": "tenant-ok"})

    assert fake_sse.graph_errors == []
    events = [e for e in fake_sse.broadcasts if e[1] == "graph_complete"]
    assert len(events) == 1
    assert events[0][2]["final_state"]["ideas_count"] == 3


@pytest.mark.anyio
async def test_resume_graph_failure_emits_graph_error(monkeypatch):
    fake_sse = _FakeSSE()
    monkeypatch.setattr(graph_execution, "sse_manager", fake_sse)
    monkeypatch.setattr(graph_execution, "build_agency_graph", lambda *a, **kw: _FakeGraph(error=ValueError("resume failed")))

    await _resume_graph_background("tenant-resil-2", {"idea_approved": True})

    assert fake_sse.graph_errors == [("tenant-resil-2", "resume failed")]


def test_handlers_no_longer_print_to_stdout():
    """Los handlers ya no dejan prints colgados: usan logger estructurado."""
    source = graph_execution.__file__  # path del módulo real
    with open(source) as fh:
        content = fh.read()
    assert "print(" not in content


def test_sse_manager_emits_graph_error_event():
    """sse_manager expone el evento graph_error con thread_id + message."""
    import backend.sse_manager as sse_mod

    assert hasattr(sse_mod.SSEManager, "emit_graph_error")