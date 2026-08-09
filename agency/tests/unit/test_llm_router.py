"""
test_llm_router.py

Pruebas unitarias TDD del router LLM multi-proveedor compartido (REQ-LLM-01..03).

Cubre:
- LLM-01-1: primer proveedor sano responde con texto LLM real (sin template).
- LLM-01-2: fallback en 429/error -> siguiente proveedor de la cadena.
- LLM-01-3: todos los proveedores fallan -> error honesto nombrando motivos.
- REQ-LLM-03-2: default provider fijado por evidencia (test tagged, skip por defecto).
"""

import os
from pathlib import Path

import pytest

import agents.llm as llm


# --------------------------------------------------------------------------- #
# LLM-02-1: ningún call site usa litellm.completion directamente (REQ-LLM-02)
# --------------------------------------------------------------------------- #
CALL_SITE_FILES = (
    "agents/crews/ideation_crew.py",
    "agents/crews/scriptwriting_crew.py",
    "agents/crews/video_prompt_crew.py",
    "agents/nodes/dm_response.py",
)


def test_no_direct_litellm_completion_in_call_sites():
    """LLM-02-1: los 4 call sites delegan en agents.llm, nunca en litellm directo."""
    repo_root = Path(__file__).resolve().parents[2]
    offenders = [
        rel
        for rel in CALL_SITE_FILES
        if "litellm.completion" in (repo_root / rel).read_text(encoding="utf-8")
    ]
    assert offenders == [], f"Direct litellm.completion still present in: {offenders}"


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    """Respuesta mínima compatible con litellm.completion(...).choices[0].message."""

    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _FakeRateLimit(RuntimeError):
    """Simula un 429 Too Many Requests de un proveedor."""


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _clean_llm_env(monkeypatch):
    """Aisla el router de claves reales: los tests deciden qué proveyó cada key.

    Con ``RUN_REAL_KEYS=1`` (gate REQ-LLM-03-2) se conserva el entorno real
    para que el provider elegido por evidencia responda de verdad.
    """
    if os.getenv("RUN_REAL_KEYS"):
        return
    for var in (
        "LITELLM_PROXY_URL",
        "LITELLM_MASTER_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "OLLAMA_BASE_URL",
    ):
        monkeypatch.delenv(var, raising=False)


# --------------------------------------------------------------------------- #
# LLM-01-1: primer proveedor sano -> texto LLM, sin template
# --------------------------------------------------------------------------- #
def test_completion_returns_first_healthy_provider_text(monkeypatch):
    """LLM-01-1: el primer proveedor sano responde y se devuelve su texto real."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    called_models = []

    def fake_call_completion(**kwargs):
        called_models.append(kwargs["model"])
        assert kwargs["messages"][0]["role"] == "system"
        assert kwargs["temperature"] == 0.7
        return _FakeCompletion("TEXTO REAL GENERADO POR EL LLM PARA EL NICHO")

    monkeypatch.setattr("agents.llm._call_completion", fake_call_completion)

    text = llm.complete(
        [{"role": "system", "content": "prompt"}, {"role": "user", "content": "niche"}],
        temperature=0.7,
        max_tokens=1000,
    )

    assert text == "TEXTO REAL GENERADO POR EL LLM PARA EL NICHO"
    assert called_models == ["gemini/gemini-3.5-flash"]
    assert "3 Errores" not in text  # sin template de respaldo


# --------------------------------------------------------------------------- #
# LLM-01-2: fallback en 429 -> siguiente proveedor
# --------------------------------------------------------------------------- #
def test_fallback_on_429_tries_next_provider(monkeypatch):
    """LLM-01-2: gemini 429 -> se intenta groq, que responde."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    called_models = []

    def fake_call_completion(**kwargs):
        called_models.append(kwargs["model"])
        if kwargs["model"].startswith("gemini"):
            raise _FakeRateLimit("429 Too Many Requests")
        return _FakeCompletion("RESPUESTA DE GROQ")

    monkeypatch.setattr("agents.llm._call_completion", fake_call_completion)

    text = llm.complete([{"role": "user", "content": "hola"}])

    assert text == "RESPUESTA DE GROQ"
    assert called_models == ["gemini/gemini-3.5-flash", "groq/llama-3.3-70b-versatile"]


def test_fallback_tries_third_provider_when_two_fail(monkeypatch):
    """LLM-01-2 (triangulación): gemini y groq fallan -> responde openrouter."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key")
    called_models = []

    def fake_call_completion(**kwargs):
        called_models.append(kwargs["model"])
        if kwargs["model"].startswith(("gemini", "groq")):
            raise _FakeRateLimit("429 Too Many Requests")
        return _FakeCompletion("RESPUESTA DE OPENROUTER")

    monkeypatch.setattr("agents.llm._call_completion", fake_call_completion)

    text = llm.complete([{"role": "user", "content": "hola"}])

    assert text == "RESPUESTA DE OPENROUTER"
    assert called_models[-1] == "openrouter/openrouter/free"


# --------------------------------------------------------------------------- #
# LLM-01-3: todos fallan -> error honesto
# --------------------------------------------------------------------------- #
def test_all_providers_fail_raises_honest_error(monkeypatch):
    """LLM-01-3: todos los proveedores fallan -> AllProvidersFailedError con motivos."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key")

    def fake_call_completion(**kwargs):
        raise _FakeRateLimit(f"429 para {kwargs['model']}")

    monkeypatch.setattr("agents.llm._call_completion", fake_call_completion)

    with pytest.raises(llm.AllProvidersFailedError) as excinfo:
        llm.complete([{"role": "user", "content": "hola"}])

    msg = str(excinfo.value)
    assert "gemini" in msg
    assert "groq" in msg
    assert "openrouter" in msg
    assert "429" in msg


def test_all_providers_fail_when_no_keys_configured(monkeypatch):
    """LLM-01-3 (triangulación): sin keys configuradas -> error honesto sin keys."""
    # _clean_llm_env ya eliminó todas las claves
    with pytest.raises(llm.AllProvidersFailedError) as excinfo:
        llm.complete([{"role": "user", "content": "hola"}])
    assert "GEMINI_API_KEY" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Proxy-first (REQ-LLM-03-1 / D1)
# --------------------------------------------------------------------------- #
def test_proxy_is_attempted_before_direct_chain(monkeypatch):
    """D1: si hay proxy configurado, se intenta PRIMERO (motor-agencia en :4000)."""
    monkeypatch.setenv("LITELLM_PROXY_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-proxy-master")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    called_models = []

    def fake_call_completion(**kwargs):
        called_models.append((kwargs["model"], kwargs.get("api_base")))
        return _FakeCompletion("RESPUESTA VIA PROXY")

    monkeypatch.setattr("agents.llm._call_completion", fake_call_completion)

    text = llm.complete([{"role": "user", "content": "hola"}])

    assert text == "RESPUESTA VIA PROXY"
    assert called_models[0] == ("motor-agencia", "http://localhost:4000/v1")


def test_proxy_failure_falls_back_to_direct_chain(monkeypatch):
    """D1: proxy caído/error -> cadena directa (gemini responde)."""
    monkeypatch.setenv("LITELLM_PROXY_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-proxy-master")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    called_models = []

    def fake_call_completion(**kwargs):
        called_models.append(kwargs["model"])
        if kwargs["model"] == "motor-agencia":
            raise RuntimeError("connection refused: proxy down")
        return _FakeCompletion("RESPUESTA DIRECTA GEMINI")

    monkeypatch.setattr("agents.llm._call_completion", fake_call_completion)

    text = llm.complete([{"role": "user", "content": "hola"}])

    assert text == "RESPUESTA DIRECTA GEMINI"
    assert called_models == ["motor-agencia", "gemini/gemini-3.5-flash"]


# --------------------------------------------------------------------------- #
# Async + REQ-LLM-03-2 default fijado por evidencia
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_acomplete_returns_text_when_provider_responds(monkeypatch):
    """acomplete() (async) devuelve el texto del primer proveedor sano."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")

    def fake_call_completion(**kwargs):
        return _FakeCompletion("RESPUESTA ASYNC")

    monkeypatch.setattr("agents.llm._call_completion", fake_call_completion)

    text = await llm.acomplete([{"role": "user", "content": "hola"}])
    assert text == "RESPUESTA ASYNC"


@pytest.mark.real_keys
@pytest.mark.skipif(
    not os.getenv("RUN_REAL_KEYS"),
    reason="Requiere claves reales: exportar RUN_REAL_KEYS=1",
)
def test_real_key_default_provider_completes():
    """REQ-LLM-03-2 gate: el default elegido por evidencia responde con claves reales.

    Evidencia (probe 2026-08-09): GEMINI 429 RateLimitError; GROQ OK; OPENROUTER OK.
    El default se fija por TEST (nunca pre-claimado) y este test lo refuerza.
    """
    assert llm.DEFAULT_PROVIDER == "groq"
    text = llm.complete(
        [{"role": "user", "content": "Responde exactamente con la palabra OK"}],
        temperature=0.0,
        max_tokens=20,
    )
    assert text.strip()
    assert "error" not in text.lower()