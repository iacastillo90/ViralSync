"""
agents/llm.py

Shared multi-provider LLM router (REQ-LLM-01 .. REQ-LLM-03, design D1).

Strategy:
1. PROXY-FIRST: if ``LITELLM_PROXY_URL`` and ``LITELLM_MASTER_KEY`` are set,
   the request goes to the LiteLLM gateway (model ``motor-agencia`` from
   ``gateway/litellm_config.dev.yaml``), which resolves its own fallback pool.
2. DIRECT CHAIN: if the proxy is unreachable/fails, fall back to a direct
   per-env chain gemini -> groq -> openrouter, skipping providers whose API key
   is not configured.
3. HONEST ERROR: if every configured provider fails, raise
   ``AllProvidersFailedError`` naming each provider and its reason.

Modules call ``complete()`` / ``acomplete()`` and receive plain text. The single
seam ``_call_completion(**kwargs)`` is what unit tests monkeypatch.
"""

import asyncio
import logging
import os
import json
from datetime import datetime

import litellm
from openai import OpenAI

logger = logging.getLogger(__name__)

def _log_llm_error_to_redis(model: str, error_msg: str):
    """Logs LLM provider errors to a global Redis list for the Admin Sistema dashboard."""
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis.Redis.from_url(redis_url, socket_timeout=1.0)
        
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "model": model,
            "error": str(error_msg)
        }
        
        # Push to list and trim to keep only the last 50 errors
        client.lpush("system_llm_errors", json.dumps(event))
        client.ltrim("system_llm_errors", 0, 49)
    except Exception as exc:
        logger.debug("Failed to log LLM error to Redis: %s", exc)


# Direct-chain fallback order: (model id, env var holding its API key).
# Only providers with a configured key are attempted.
# NOTA: la API de Google (generativelanguage.googleapis.com) devuelve 404 para
# gemini-1.5-flash / 1.5-flash-8b / 2.0-flash-exp (familia 3.x en adelante, 1M ctx).
# mixtral-8x7b-32768 fue retirado de Groq (verificado contra /openai/v1/models).
DIRECT_CHAIN = (
    ("gemini/gemini-3-flash-preview", "GEMINI_API_KEY"),
    ("gemini/gemini-3.1-flash-lite", "GEMINI_API_KEY"),
    ("gemini/gemini-flash-latest", "GEMINI_API_KEY"),
    ("groq/llama-3.3-70b-versatile", "GROQ_API_KEY"),
    ("groq/llama-3.1-8b-instant", "GROQ_API_KEY"),
    ("openrouter/openrouter/free", "OPENROUTER_API_KEY"),
)

PROXY_MODEL = "motor-agencia"
DEFAULT_PROVIDER = "groq"


class AllProvidersFailedError(RuntimeError):
    """Raised when every configured provider fails; message names each one."""


def _call_completion(**kwargs):
    """Single LLM completion call. Seam mocked by unit tests.

    Proxy path: cuando el modelo es ``motor-agencia`` (gateway LiteLLM), se usa el
    cliente OpenAI estándar apuntando al proxy en lugar de ``litellm.completion``.
    Evita el salto litellm-SDK -> litellm-proxy que truncaba respuestas largas
    (APIConnectionError/empty content) y degradaba el scoring LLM a reglas puras.
    """
    call_kwargs = dict(kwargs)
    if call_kwargs.get("model") == "motor-agencia":
        api_base = call_kwargs.pop("api_base")
        api_key = call_kwargs.pop("api_key")
        model = call_kwargs.pop("model")
        client = OpenAI(base_url=api_base, api_key=api_key, timeout=120)
        return client.chat.completions.create(model=model, **call_kwargs)
    return litellm.completion(**call_kwargs)


def _configured_providers():
    """Providers to attempt, in order: proxy first, then the keyed direct chain."""
    providers = []  # (model, api_base or None, env_var or None)
    proxy_url = os.getenv("LITELLM_PROXY_URL")
    master_key = os.getenv("LITELLM_MASTER_KEY")
    if proxy_url and master_key:
        providers.append((PROXY_MODEL, proxy_url, "LITELLM_MASTER_KEY"))
    for model, env_var in DIRECT_CHAIN:
        if os.getenv(env_var):
            providers.append((model, None, env_var))
    return providers


def _normalize_model_id(model: str) -> str:
    """Strip a litellm provider prefix to get the clean dashboard model id.

    Examples: ``gemini/gemini-3-flash-preview`` -> ``gemini-3-flash-preview``,
    ``groq/llama-3.3-70b-versatile`` -> ``llama-3.3-70b-versatile``,
    ``openrouter/openrouter/free`` -> ``openrouter/free``.
    """
    if "/" in model:
        provider, _, rest = model.partition("/")
        if provider in ("gemini", "groq", "openrouter", "openai") and rest:
            return rest
    return model


def _track_llm_usage(model: str, completion, tenant_id: str = "system") -> None:
    """Best-effort record of token usage for a successful completion.

    Never raises and never blocks: Redis outages, missing usage metadata or
    unexpected response shapes degrade to a silent no-op so token tracking can
    never break or delay the LLM response path.
    """
    try:
        usage = getattr(completion, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        from backend.services.llm_budget_service import track_llm_token_usage

        track_llm_token_usage(
            tenant_id, _normalize_model_id(model), prompt_tokens, completion_tokens
        )
    except Exception as exc:  # noqa: BLE001 - telemetry must never break the call
        logger.debug("Failed to track LLM token usage: %s", exc)


def complete(messages, temperature=0.7, max_tokens=1000, **kwargs):
    """Synchronous multi-provider completion returning plain text.

    ``tenant_id`` may be passed as a keyword argument for per-tenant token
    usage tracking; it is consumed here and never forwarded to the provider.
    """
    tenant_id = kwargs.pop("tenant_id", "system")
    providers = _configured_providers()
    if not providers:
        missing = ", ".join(env_var for _, env_var in DIRECT_CHAIN)
        raise AllProvidersFailedError(
            "No LLM provider configured: set one of "
            f"{missing}, or LITELLM_PROXY_URL + LITELLM_MASTER_KEY"
        )

    reasons = []
    for model, api_base, env_var in providers:
        call_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if api_base:
            call_kwargs["api_base"] = api_base
        if env_var and os.getenv(env_var):
            call_kwargs["api_key"] = os.getenv(env_var)
        call_kwargs.update(kwargs)
        try:
            completion = _call_completion(**call_kwargs)
            content = completion.choices[0].message.content
            if content:
                _track_llm_usage(model, completion, tenant_id)
                return content
            raise RuntimeError("empty response content")
        except Exception as exc:  # noqa: BLE001 - any provider error triggers failover
            reasons.append(f"{model}: {exc}")
            logger.warning(
                "LLM provider %s failed (%d/%d): %s",
                model,
                len(reasons),
                len(providers),
                exc,
            )
            _log_llm_error_to_redis(model, str(exc))
    raise AllProvidersFailedError(
        "All LLM providers failed: " + "; ".join(reasons)
    )


async def acomplete(messages, temperature=0.7, max_tokens=1000, **kwargs):
    """Async variant of :func:`complete`.

    Runs the blocking completion in a worker thread so the caller's event loop
    is never blocked by provider latency.
    """
    return await asyncio.to_thread(
        complete, messages, temperature=temperature, max_tokens=max_tokens, **kwargs
    )