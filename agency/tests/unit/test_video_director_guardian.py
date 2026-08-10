"""
test_video_director_guardian.py

Pruebas unitarias para el VideoDirectorAgent como Guardián de Calidad y Rendimiento:
1. Filtro de Valor (Evaluación de Impacto RUM).
2. Filtro de Hardware (Restricciones Quirúrgicas 45s / 720p).
3. Curaduría de Metadatos (Título, Descripción y Hashtags).

PR-B / WU3: el director se vuelve curador contextual con guard de presupuesto
(REQ-CVD-01..02, D4/D5/D6). Los tests usan fake_acomplete (patrón
test_ideation_crew.py:59-67) → zero tokens, sin red.
"""

import asyncio
import json
import logging

import pytest
import redis

from agents.crews.video_director_crew import (
    run_video_director_crew,
    evaluate_script_quality,
    curate_video_metadata,
)
from agents.crews import video_director_crew as crew_module
from workers.video_edit_task import trigger_video_render

GOOD_SCRIPT = {
    "gancho_0_5s": "3 errores masivos al escalar tu software SaaS en 2026.",
    "contexto_5_30s": "El problema principal es intentar abarcar todo sin foco ni automatización. Cuando simplificas tu arquitectura, la conversión aumenta.",
    "moraleja_30_50s": "Primero valida la tracción orgánica y la entrega de valor sin fricción antes de invertir en anuncios.",
    "cta_50_60s": "Comenta la palabra DEMO abajo y te enviamos el desglose.",
    "keyword": "DEMO",
}
IDEA = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

LLM_JSON = json.dumps(
    {
        "final_title": "5 Errores que Matan tu SaaS en 2026",
        "description": "Descripción contextual generada por el LLM para el director.",
        "hashtags": ["#saas", "#marketingdigital", "#viral"],
        "keywords": ["saas", "growth", "automation"],
    },
    ensure_ascii=False,
)


def _make_fake_acomplete(calls, payload=LLM_JSON):
    """fake_acomplete (patrón test_ideation_crew.py:59-67): registra la llamada
    y devuelve el JSON estricto; el seam es agents.llm.acomplete (async)."""

    async def fake_acomplete(messages, temperature=0.7, max_tokens=1000, **kwargs):
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        calls.append(True)
        return payload

    return fake_acomplete


def test_evaluate_script_quality_pass():
    score, approved, feedback = evaluate_script_quality(GOOD_SCRIPT, IDEA)

    assert score >= 0.70
    assert approved is True
    assert len(feedback) == 0


def test_evaluate_script_quality_fail():
    poor_script = {
        "gancho_0_5s": "Hola",
        "contexto_5_30s": "Cómprame algo",
        "moraleja_30_50s": "Es bueno",
        "cta_50_60s": "Chao",
        "keyword": "",
    }
    idea = {"texto": "Spam Ad"}

    score, approved, feedback = evaluate_script_quality(poor_script, idea)

    assert score < 0.70
    assert approved is False
    assert len(feedback) > 0


def test_curate_video_metadata():
    script = {"gancho_0_5s": "3 Errores al Escalar B2B", "keyword": "CONSULTA"}
    idea = {"texto": "Estrategia B2B", "niche": "Marketing SaaS"}

    metadata = curate_video_metadata(script, idea)

    assert "🚀 Estrategia B2B | Caso Práctico 2026" in metadata["final_title"]
    assert "CONSULTA" in metadata["description"]
    assert len(metadata["hashtags"]) >= 4
    assert "#marketingsaas" in metadata["hashtags"]


def test_video_director_hardware_filter_and_rejection():
    poor_script = {
        "gancho_0_5s": "Hi",
        "contexto_5_30s": "Short",
        "moraleja_30_50s": "Small",
        "cta_50_60s": "Bye",
        "keyword": "",
    }
    result = trigger_video_render.run(tenant_id="tenant-guardian-test", script=poor_script)

    assert result["status"] == "rejected_quality"
    assert result["quality_score"] < 0.70
    assert "no superó el umbral" in result["message"]


# ===========================================================================
# PR-B / WU3 — Director contextual con guard de presupuesto (REQ-CVD-01..02)
# ===========================================================================


def test_director_curates_metadata_via_router_within_budget(monkeypatch):
    """CVD-01-1 / LLM-02-3: dentro de presupuesto el director llama al router
    (agents.llm.acomplete) y los 4 campos curados llegan al render_payload."""
    calls = []
    monkeypatch.setattr("agents.llm.acomplete", _make_fake_acomplete(calls))

    result = run_video_director_crew(script=GOOD_SCRIPT, idea=IDEA, tenant_id="tenant-llm-ok")

    assert calls == [True]
    payload = result["render_payload"]
    assert payload["title"] == "5 Errores que Matan tu SaaS en 2026"
    assert "Descripción contextual" in payload["description"]
    assert payload["hashtags"] == ["#saas", "#marketingdigital", "#viral"]
    assert payload["keywords"] == ["saas", "growth", "automation"]
    assert result["metadata"]["final_title"] == payload["title"]


def test_director_over_budget_does_not_call_router(monkeypatch):
    """CVD-02-1: tenant sobre presupuesto → acomplete NO se llama y la salida
    es la plantilla determinística (provable por fake que registra llamadas)."""
    calls = []
    monkeypatch.setattr("agents.llm.acomplete", _make_fake_acomplete(calls))
    monkeypatch.setattr(
        "agents.crews.video_director_crew._tenant_within_llm_budget",
        lambda tenant_id: False,
    )

    result = run_video_director_crew(script=GOOD_SCRIPT, idea=IDEA, tenant_id="tenant-over-budget")

    assert calls == []
    payload = result["render_payload"]
    assert "🚀" in payload["title"]  # plantilla, no LLM
    assert result["metadata"]["final_title"] == payload["title"]
    assert payload["description"]  # plantilla también entrega descripción


def test_director_all_providers_down_falls_back_to_template(monkeypatch):
    """CVD-02-2: todos los providers caídos → plantilla, sin excepción que
    se propague a video_edit_task.py."""
    from agents.llm import AllProvidersFailedError

    async def failing_acomplete(messages, temperature=0.7, max_tokens=1000, **kwargs):
        raise AllProvidersFailedError("All LLM providers failed: test-only")

    monkeypatch.setattr("agents.llm.acomplete", failing_acomplete)

    result = run_video_director_crew(script=GOOD_SCRIPT, idea=IDEA, tenant_id="tenant-down")

    payload = result["render_payload"]
    assert "🚀" in payload["title"]
    assert payload["description"]
    assert len(payload["hashtags"]) >= 4


def test_director_redis_down_warns_and_continues(monkeypatch, caplog):
    """CVD-02-3: Redis caído → warning y continúa sin guard (patrón
    dm_response.py:71-72); el router aún se llama."""
    calls = []
    monkeypatch.setattr("agents.llm.acomplete", _make_fake_acomplete(calls))

    def _raising_redis(url, **kwargs):
        raise redis.exceptions.ConnectionError("Redis caído en test")

    monkeypatch.setattr("redis.Redis.from_url", _raising_redis)

    with caplog.at_level(logging.WARNING, logger="agents.crews.video_director_crew"):
        result = run_video_director_crew(script=GOOD_SCRIPT, idea=IDEA, tenant_id="tenant-redis-down")

    assert calls == [True]  # guard omitido → se curó con LLM
    assert "Redis no disponible" in caplog.text
    assert result["render_payload"]["title"] == "5 Errores que Matan tu SaaS en 2026"


def test_director_unparseable_llm_output_falls_back_to_template(monkeypatch):
    """D6: salida LLM no parseable → plantilla (fallback determinístico).
    El fake SÍ se invoca (calls == [True]): el fallback ocurre en el parse,
    no porque el director omita el router."""
    calls = []

    async def garbage_acomplete(messages, temperature=0.7, max_tokens=1000, **kwargs):
        calls.append(True)
        return "Esto no es JSON"

    monkeypatch.setattr("agents.llm.acomplete", garbage_acomplete)

    result = run_video_director_crew(script=GOOD_SCRIPT, idea=IDEA, tenant_id="tenant-bad-parse")

    assert calls == [True]
    assert "🚀" in result["render_payload"]["title"]


def test_parse_metadata_json_strict():
    """D6: parse estricto — quita fences ```, valida tipos; fallo → None."""
    good = json.dumps(
        {"final_title": "T", "description": "D", "hashtags": ["#a"], "keywords": ["k"]}
    )
    parsed = crew_module._parse_metadata_json(f"```json\n{good}\n```")
    assert parsed["final_title"] == "T"
    assert parsed["hashtags"] == ["#a"]
    assert parsed["keywords"] == ["k"]

    assert crew_module._parse_metadata_json("no es json") is None
    assert crew_module._parse_metadata_json('{"final_title": "T"}') is None  # faltan campos
    assert crew_module._parse_metadata_json("[1, 2]") is None  # no es dict
    assert crew_module._parse_metadata_json(
        '{"final_title": 3, "description": "D", "hashtags": [], "keywords": []}'
    ) is None  # tipo incorrecto


def test_tenant_within_llm_budget_reads_redis_spend(monkeypatch):
    """D5: el guard lee llm_spend:{tenant_id} de Redis y consulta
    check_tenant_llm_budget (999 > límite → False; 5 <= límite → True)."""

    class _FakeRedis:
        def __init__(self, value):
            self.value = value

        def get(self, key):
            return self.value

    monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: _FakeRedis("999.0"))
    assert crew_module._tenant_within_llm_budget("tenant-over") is False

    monkeypatch.setattr("redis.Redis.from_url", lambda url, **kw: _FakeRedis("5.0"))
    assert crew_module._tenant_within_llm_budget("tenant-ok") is True


def test_director_sync_bridge_from_running_loop(monkeypatch):
    """D4: run_video_director_crew (sync) es invocable DESDE un event loop
    corriendo (contexto nodo LangGraph async) sin chocar. Una implementación
    con asyncio.run() fallaría aquí (RuntimeError)."""
    calls = []
    monkeypatch.setattr("agents.llm.acomplete", _make_fake_acomplete(calls))

    async def _inside_loop():
        # El nodo async de LangGraph llama al worker sync dentro de su loop
        return run_video_director_crew(script=GOOD_SCRIPT, idea=IDEA, tenant_id="tenant-bridge")

    result = asyncio.run(_inside_loop())

    assert calls == [True]
    assert result["render_payload"]["title"] == "5 Errores que Matan tu SaaS en 2026"
