# Tasks: Stabilize Docker, Lockfile, DB, and Pytest Suite

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~85 authored + `requirements.lock` (generated, ~1000) |
| 400-line budget risk | Low |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (infra) → PR 2 (pytest green) → PR 3 (stack verify) |
| Delivery strategy | force-chained |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Docker build context + lockfile + DB wiring + SQLite session | PR 1 (base: tracker) | `uv pip compile requirements.txt -o requirements.lock && uv run pytest agency/tests/unit/test_db_session.py -q` | `docker compose build backend celery_worker`; fresh postgres init via `docker compose up postgres` | Revert compose context to `build: .`, `git checkout requirements.lock`, revert session/main/conftest |
| 2 | Pytest suite green (dm_response typing, prune policy, e2e 200) | PR 2 (base: PR 1 branch) | `uv run pytest agency/tests/unit/test_deps_prune.py agency/tests/unit/test_dm_response.py -q` then full `uv run pytest -q` | `uv run pytest -q` full suite (expect 100% green) | Revert dm_response.py/test_deps_prune.py/test_full_pipeline.py individually |
| 3 | Stack up + healthchecks (verify-only, no new diff) | PR 3 (folded into PR 2 verification) | `docker compose ps` healthchecks healthy | `docker compose up --build` then `docker compose ps` all healthy | None — no diff; rerun compose only |

## Phase 1: Docker + Lockfile + DB

- [x] 1.1 Create repo-root `.dockerignore` excluding `.venv`, `venv`, `node_modules`, `__pycache__`, `.git`, `frontend/.next`, `.coverage`, test caches. — Test: `docker build` context send is empty for those paths.
- [x] 1.2 `agency/docker-compose.yml`: `backend` + `celery_worker` `build:` → `{context: .., dockerfile: agency/Dockerfile}`. — Test: `docker compose config` resolves context; `docker build .` from repo root succeeds.
- [x] 1.3 `agency/docker-compose.yml`: `postgres` mounts `./migrations:/docker-entrypoint-initdb.d:ro`. — Test: fresh volume `\dt` lists all migration-001/002 tables (spec scenario).
- [x] 1.4 Regenerate `requirements.lock` via `uv pip compile requirements.txt -o requirements.lock` (uv 0.12.2 present). Verify litellm/asyncpg/aiosqlite/sqlalchemy/tenacity/pyjwt/python-jose present. — Test: lock contains all 7 pins (spec "complete compile" scenario).
- [x] 1.5 `agency/backend/db/session.py`: add `poolclass=StaticPool` on sqlite-in-memory URL branch. — Test: `FORCE_SQLITE` init + `select()` returns shared schema.
- [x] 1.6 `agency/backend/main.py`: add `asynccontextmanager` lifespan calling `await init_db()`; pass `lifespan=` to `FastAPI(...)`. — Test: app startup calls `init_db`; running twice is idempotent.
- [x] 1.7 `agency/tests/conftest.py`: top-level `os.environ["FORCE_SQLITE"]="true"`; `init_test_db` session/autouse fixture → `init_db()`; export `db_session` (AsyncSessionLocal). — Test: e2e uses SQLite not postgres.

## Phase 2: Pytest Green

- [x] 2.1 `agency/agents/nodes/dm_response.py`: move `from typing import ... List, Optional, Tuple`; keep `tenacity` imports to retry/stop_after_attempt/wait_exponential. — Test: pytest collection import succeeds (spec scenario).
- [x] 2.2 `agency/tests/unit/test_deps_prune.py`: set `PRUNED` = the 6 dead pkgs; `KEPT` gains litellm/sqlalchemy/asyncpg/aiosqlite/tenacity/pyjwt/python-jose; `LOCK_TRANSITIVE_EXEMPT=set()`; drop sqlalchemy-lock-exemption test. — Test: prune param-loop passes for KEPT/PRUNED (spec scenarios).
- [x] 2.3 `agency/tests/e2e/test_full_pipeline.py`: after tenant create, seed `Lead(id="lead-001", ...)` via `db_session` before takeover. — Test: takeover POST returns 200 `handled_by_human` (spec scenario).
- [x] 2.4 Full-suite gate: run `uv run pytest -q` from repo root. — Test: 0 failures, 0 errors, all collect (spec green scenario).

## Phase 3: Bring Up Stack

- [x] 3.1 `docker compose up --build`; verify all healthcheck services healthy (postgres, backend, celery_worker). — Test: `docker compose ps` healthy; backend reachable; DB schema present.