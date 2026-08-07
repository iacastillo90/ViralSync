# Design: Stabilize Docker, Lockfile, DB, and Pytest Suite

## Technical Approach

Baseline the stack so it builds, bootstraps, and tests green. Four independent
threads: (1) point compose builds at the repo root so the existing Dockerfile
`COPY`s resolve; (2) regenerate the lockfile from the repo-root `requirements.txt`;
(3) provision DB schema by mounting `migrations/*.sql` into Postgres init **and**
wiring idempotent `init_db()` at app startup; (4) four mechanical pytest fixes.

Maps to spec `docker-lockfile-db-bootstrap`. Verified ground truth:
`requirements.*` live at repo root; `docker-compose.yml` builds `context: .`
(= `agency/`) where `requirements.txt` does **not** exist; `prune` test currently
fails on `litellm`/`sqlalchemy`; e2e fails with `Connect call failed ... 5432`
because tests never force SQLite; `dm_response.py` imports `List/Optional/Tuple`
from `tenacity` (not exported → collection ImportError).

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|----------|--------|--------------|-----------|
| 1 | Docker build context | Change compose `build:` to `context: ..` + `dockerfile: agency/Dockerfile`; **keep Dockerfile COPYs** (`COPY requirements.txt .`, `COPY agency/ .`) | Keep `context: agency/`, shrink Dockerfile to `COPY . .` + move requirements into `agency/` | requirements/lock are repo-root; zero Dockerfile edits; mirrors Dockerfile author's intent (copies assume repo-root). Avoids duplicating requirements inside `agency/`. |
| 2 | Lockfile regen | `uv pip compile requirements.txt -o requirements.lock` from repo root (uv 0.12.2 present); add repo-root `.dockerignore` | uv's `uv.lock` | File header already documents this exact command. Keeps pip-lock workflow; transitive pinned output identical style. |
| 3 | DB schema provisioning | **Both**: mount `./migrations:/docker-entrypoint-initdb.d:ro` on `postgres` (fresh volume → full SQL schema incl. `video_metrics`, migration-002 `leads` cols) **AND** wire idempotent `init_db()`/`create_all` via FastAPI lifespan | alembic 002 real revision | `init_db`/create_all covers only ORM tables (`videos`, `market_maps`, `rum_thresholds` live in SQL only); compose init gives the full SQL schema. `create_all` is additive/idempotent so both coexist; avoids double-maintaining schema in alembic. 001 stays a marker. |
| 4 | DB session SQLite | `session.py`: when sqlite in-memory, use `poolclass=StaticPool` | file-based sqlite | In-memory `:memory:` creates a fresh DB per connection; `StaticPool` keeps one shared DB so `create_all` + queries hit the same schema. |
| 5 | Dep policy | Move `litellm`, `sqlalchemy` to KEPT (direct); drop them from PRUNED; add `asyncpg`,`aiosqlite`,`tenacity`,`pyjwt`,`python-jose` to KEPT; remove the sqlalchemy-lock transitive exemption | Keep them pruned | New policy (spec): these are directly imported (litellm in `dm_response`, sqlalchemy→alembic/db, jose for security). Prune only the 6 still-dead packages. |
| 6 | dm_response typing | `from typing import Dict, Any, List, Optional, Tuple`; `from tenacity import retry, stop_after_attempt, wait_exponential` | Use `typing_extensions` only | `tenacity` never exports `List/Optional/Tuple`; this is the ImportError. Fix import origin. |
| 7 | e2e takeover 200 | `conftest` sets `FORCE_SQLITE`, session `init_db()`; e2e seeds a real `Lead(id="lead-001")` before takeover | Put 200 → mock path; allow `503` | Root cause of current 503 = postgres:5432 unreachable in tests. Real lookup + seeded lead returns 200 with `status: handled_by_human`, preserving fail-closed (no mock data). |

## Data Flow

    create_async_engine(TARGET_DB_URL) ──▶ init_db(): create_all (idempotent)
         │ FORCE_SQLITE → sqlite+aiosqlite StaticPool
         │ else → postgresql+asyncpg
    FastAPI lifespan ──▶ init_db()
    compose postgres ──▶ /docker-entrypoint-initdb.d/*.sql (fresh volume) ──▶ full schema
    takeover POST → select Lead → update status/handled_at → 200 handled_by_human

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `agency/docker-compose.yml` | Modify | backend+celery_worker `build:` → `{context: .., dockerfile: agency/Dockerfile}`; `postgres` add `./migrations:/docker-entrypoint-initdb.d:ro`;
| `.dockerignore` (repo root) | Create | Exclude `.venv`, `venv`, `node_modules`, `__pycache__`, `.git`, `frontend/.next`, coverage, tests from build context. |
| `requirements.lock` (repo root) | Modify | Regenerate via `uv pip compile requirements.txt -o requirements.lock` (adds litellm/asyncpg/aiosqlite/sqlalchemy-asyncio/tenacity/pyjwt/python-jose; sqlalchemy 2.0.51 lens; tenacity 9.1.4). |
| `agency/backend/db/session.py` | Modify | Add `StaticPool` for sqlite in-memory URL branch. |
| `agency/backend/main.py` | Modify | Add `asynccontextmanager` lifespan calling `await init_db()`; pass `lifespan=` to `FastAPI(...)`. |
| `agency/tests/conftest.py` | Modify | Top-level `os.environ["FORCE_SQLITE"]="true"`; session/autouse async fixture `init_test_db` → `init_db()`; export `db_session` fixture (AsyncSessionLocal). |
| `agency/tests/e2e/test_full_pipeline.py` | Modify | After tenant create, insert `Lead(id="lead-001", tenant_id=..., origen="comment")` via `db_session` before takeover step. |
| `agency/agents/nodes/dm_response.py` | Modify | Move `List/Optional/Tuple` import from `tenacity` to `typing`. |
| `agency/tests/unit/test_deps_prune.py` | Modify | Update `PRUNED`/`KEPT`/`LOCK_TRANSITIVE_EXEMPT`; drop sqlalchemy-lock-exemption test (covered by KEPT pinned check). |

## Interfaces / Contracts

```python
# session.py — sqlite pools
if "sqlite" in TARGET_DB_URL:
    engine_kwargs = {**engine_kwargs, "poolclass": StaticPool}
else:
    engine_kwargs.update({...})

# main.py
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(_app):
    await init_db(); yield
app = FastAPI(..., lifespan=lifespan)
```
`test_deps_prune.py`:
```python
PRUNED = {"crewai","crewai-tools","llama-index","llama-index-vector-stores-qdrant","openai-whisper","langgraph-checkpoint-postgres"}
KEPT = {"fastapi","uvicorn","langgraph","qdrant-client","celery","redis","psycopg2-binary","moviepy","python-multipart","httpx","pytest","pytest-cov","alembic","litellm","asyncpg","aiosqlite","sqlalchemy","tenacity","pyjwt","python-jose"}
LOCK_TRANSITIVE_EXEMPT = set()
```

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | prune policy | Re-run `test_deps_prune.py`; KEPT param loop proves each direct dep declared once pinned 6; PRUNED loops absent from txt+lock; no sqlalchemy empty-exemption. |
| Unit | db session | Test `FORCE_SQLITE` init + `select()` returns creada schema (proves StaticPool shared DB). |
| Integration | lifespan | `app=FastAPI(...lifespan)`; ensure startup calls `init_db` idempotently twice. |
| E2E | takeover | `test_full_pipeline.py` returns **200** `handled_by_human` (was 503). |

## Threat Matrix

N/A — no routing, shell-subprocess, VCS/PR-commitment, executable-classification, or
process-integration boundary. Docker build/compose `initdb` use vendor-standard
behavior only. All five matrix rows N/A (no pipeline/CLI collection or git operations).

## Migration / Rollout

No data migration. Provisioning is additive/idempotent (`IF NOT EXISTS` in 002 `activate`, `init_db` create_all). Fresh Postgres: `docker compose down -v && docker compose up` re-runs SQL init on empty volume.

Rollback: `git checkout` on regenerated `requirements.lock`; revert `docker-compose.yml` context to `build: .`; revert `session.py`/`main.py`/`conftest.py`/`test_deps_prune.py` individually. 001 stays alembic no-op throughout.

## Open Questions

- None blocking. Optional: confirm whether `docker compose up` may require `--build` for changed context (not a code question).