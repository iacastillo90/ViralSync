"""Slice 1 (python-deps) — prune verification tests.

The pruned packages have zero imports across
``backend/``, ``agents/``, ``workers/``, ``knowledge/``, ``gateway/`` and
``migrations/`` (design D3). ``litellm``, ``sqlalchemy``, ``asyncpg``,
``aiosqlite``, ``tenacity``, ``pyjwt`` and ``python-jose`` are DIRECT
dependencies (code imports them) and MUST be declared/pinned and present in
both ``requirements.txt`` and the lockfile (design D5).
"""

from pathlib import Path
import re

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIREMENTS_TXT = REPO_ROOT / "requirements.txt"
REQUIREMENTS_LOCK = REPO_ROOT / "requirements.lock"

# The 5 still-dead direct dependencies pruned in Phase 0 (design D3).
# NOTE: `langgraph-checkpoint-postgres` was pruned in Phase 0 (zero imports)
# but the approved change `pipeline-production-gaps` (REQ-PERSIST-04 / design
# D2, WU-03 T-14) makes it a DIRECT dependency again: `AsyncPostgresSaver`
# lives in `backend/db/checkpointer.py` (import lazy, rama Postgres). It moved
# from PRUNED to KEPT below with its `~=` floor.
PRUNED = {
    "crewai",
    "crewai-tools",
    "llama-index",
    "llama-index-vector-stores-qdrant",
    "openai-whisper",
}

# The kept dependencies with ~= floors (design D5 / Interface).
# `langgraph-checkpoint-postgres` = checkpointer persistente del grafo
# (design D2 / REQ-PERSIST-04): reincorporado como dependencia directa en WU-03.
KEPT = {
    "fastapi",
    "uvicorn",
    "langgraph",
    "langgraph-checkpoint-postgres",
    "qdrant-client",
    "celery",
    "redis",
    "psycopg2-binary",
    "moviepy",
    "python-multipart",
    "httpx",
    "pytest",
    "pytest-cov",
    "alembic",
    "litellm",
    "asyncpg",
    "aiosqlite",
    "sqlalchemy",
    "tenacity",
    "pyjwt",
    "python-jose",
}

# No lockfile-only transitive exemptions anymore: every KEPT direct dep must be
# pinned in requirements.txt AND present in the lockfile (design D5).
LOCK_TRANSITIVE_EXEMPT = set()


def _declared_name(line):
    """Distribution name (extras stripped) declared by a single pip/uv line."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    name = re.split(r"[=<>!~\[\];\s]", line, maxsplit=1)[0]
    return name.lower() if name else None


def _parse_names(text):
    """Distribution names (extras stripped) declared in a pip/uv file."""
    return {name for name in (_declared_name(raw) for raw in text.splitlines()) if name}


def _requirements_txt():
    return REQUIREMENTS_TXT.read_text(encoding="utf-8")


def _requirements_lock():
    return REQUIREMENTS_LOCK.read_text(encoding="utf-8")


def test_pruned_packages_absent_from_requirements_txt():
    names = _parse_names(_requirements_txt())
    assert PRUNED.isdisjoint(names), (
        f"pruned deps still declared in {REQUIREMENTS_TXT.name}: "
        f"{sorted(PRUNED & names)}"
    )


def test_pruned_packages_absent_from_lockfile():
    names = _parse_names(_requirements_lock())
    must_be_absent = PRUNED - LOCK_TRANSITIVE_EXEMPT
    assert must_be_absent.isdisjoint(names), (
        f"pruned deps still in {REQUIREMENTS_LOCK.name}: "
        f"{sorted(must_be_absent & names)}"
    )


@pytest.mark.parametrize("kept", sorted(KEPT))
def test_kept_dependency_declared_with_pin(kept):
    txt = _requirements_txt()
    names = _parse_names(txt)
    assert kept in names, f"{kept} missing from {REQUIREMENTS_TXT.name}"
    lines = [
        raw
        for raw in txt.splitlines()
        if _declared_name(raw) == kept
    ]
    assert len(lines) == 1, f"{kept} must be declared exactly once, got {len(lines)}"
    assert ("~=" in lines[0]) or ("==" in lines[0]), (
        f"{kept} is not pinned with ~= or ==: {lines[0]}"
    )
