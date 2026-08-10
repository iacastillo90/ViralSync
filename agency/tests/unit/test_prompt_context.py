"""
test_prompt_context.py

Zero-token unit tests for the shared prompt-context helpers (design D7):
- resolve_rum_threshold: RUM dynamic threshold from Redis (clamped [0.50, 0.90],
  default 0.70) — REQ-CVD-03. Never a hardcoded global (CVD-03-2).
- build_trend_section: sanitized trend snippets (<=400 chars) from
  rag_cache["tendencia_{niche}"] — REQ-CVD-04. Cache miss is non-fatal (CVD-04-2).

All Redis/cache interactions are monkeypatched; zero tokens, no real Redis.
"""

import pytest

from agents.crews import prompt_context


def test_resolve_rum_threshold_injects_redis_value(monkeypatch):
    # CVD-03-1: rum_threshold:{niche} holds 0.78 -> the wrapper returns 0.78.
    monkeypatch.setattr(
        prompt_context, "get_dynamic_threshold", lambda niche: 0.78
    )

    threshold = prompt_context.resolve_rum_threshold("B2B Marketing")

    assert threshold == 0.78


def test_resolve_rum_threshold_degradation_uses_clamp_default(monkeypatch):
    # CVD-03-2: Redis unavailable -> existing clamp default (0.70) is returned,
    # no hardcoded constant introduced. The default lives in rum_calculator;
    # this guard only mirrors it when the underlying getter itself fails.
    def boom(niche):
        raise RuntimeError("redis down")

    monkeypatch.setattr(prompt_context, "get_dynamic_threshold", boom)

    threshold = prompt_context.resolve_rum_threshold("B2B Marketing")

    assert threshold == 0.70


class FakeCache:
    def __init__(self, payload):
        self._payload = payload

    def get(self, query):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_build_trend_section_injects_sanitized_snippets(monkeypatch):
    # CVD-04-1: cached trends reach the writers, sanitized through the HTML
    # sanitization wrapper (no tags leak into the prompt).
    docs = [
        {
            "filename": "trend_reels.md",
            "content": "<b>Tendencia Viral Actual: Reels</b> - retención <i>alta</i> en 2026",
        }
    ]
    monkeypatch.setattr(
        prompt_context, "rag_cache", FakeCache(docs)
    )

    section = prompt_context.build_trend_section("b2b")

    assert section != ""
    assert "Tendencia Viral Actual: Reels" in section
    assert "<b>" not in section
    assert "<i>" not in section
    assert len(section) <= 400


def test_build_trend_section_truncates_at_400_chars(monkeypatch):
    # Repo rule: snippets are trimmed to ~400 chars before reaching prompts.
    long_content = "Tendencia Viral Actual: " + ("X" * 600)
    monkeypatch.setattr(
        prompt_context, "rag_cache", FakeCache([{"content": long_content}])
    )

    section = prompt_context.build_trend_section("b2b")

    assert len(section) <= 400


def test_build_trend_section_miss_omitted(monkeypatch):
    # CVD-04-2: no cache entry -> section is omitted (empty string).
    monkeypatch.setattr(prompt_context, "rag_cache", FakeCache(None))

    section = prompt_context.build_trend_section("b2b")

    assert section == ""


def test_build_trend_section_redis_down_non_fatal(monkeypatch):
    # CVD-04-2: Redis/cache failure must NOT fail the crew -> "" and no raise.
    monkeypatch.setattr(
        prompt_context, "rag_cache", FakeCache(RuntimeError("cache down"))
    )

    section = prompt_context.build_trend_section("b2b")

    assert section == ""