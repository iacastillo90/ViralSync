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

import litellm

logger = logging.getLogger(__name__)

# Direct-chain fallback order: (model id, env var holding its API key).
# Only providers with a configured key are attempted.
DIRECT_CHAIN = (
    ("gemini/gemini-3.5-flash", "GEMINI_API_KEY"),
    ("groq/llama-3.3-70b-versatile", "GROQ_API_KEY"),
    ("openrouter/openrouter/free", "OPENROUTER_API_KEY"),
)

PROXY_MODEL = "motor-agencia"
DEFAULT_PROVIDER = "groq"


class AllProvidersFailedError(RuntimeError):
    """Raised when every configured provider fails; message names each one."""


def _call_completion(**kwargs):
    """Single LLM completion call. Seam mocked by unit tests."""
    call_kwargs = dict(kwargs)
    if call_kwargs.get("model") == "motor-agencia":
        call_kwargs["model"] = "openai/motor-agencia"
    return litellm.completion(**call_kwargs)




def _configured_providers():
    """Providers to attempt, in order: proxy first, then the keyed direct chain."""
    providers = []  # (model, api_base or None, env_var or None)
    proxy_url = os.getenv("LITELLM_PROXY_URL")
    master_key = os.getenv("LITELLM_MASTER_KEY")
    if proxy_url and master_key:
        providers.append((PROXY_MODEL, proxy_url, None))
    for model, env_var in DIRECT_CHAIN:
        if os.getenv(env_var):
            providers.append((model, None, env_var))
    return providers


def complete(messages, temperature=0.7, max_tokens=1000, **kwargs):
    """Synchronous multi-provider completion returning plain text.

    Returns the text of the first healthy provider's response. Raises
    ``AllProvidersFailedError`` when no provider responds (missing keys count
    as a failure reason too).
    """
    providers = _configured_providers()
    if not providers:
        missing = ", ".join(env_var for _, env_var in DIRECT_CHAIN)
        raise AllProvidersFailedError(
            "No LLM provider configured: set one of "
            f"{missing}, or LITELLM_PROXY_URL + LITELLM_MASTER_KEY"
        )

    reasons = []
    for model, api_base, _ in providers:
        call_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if api_base:
            call_kwargs["api_base"] = api_base
        call_kwargs.update(kwargs)
        try:
            completion = _call_completion(**call_kwargs)
            content = completion.choices[0].message.content
            if content:
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