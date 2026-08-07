# Proposal: Stabilize Docker, Lockfile, DB, and Pytest Suite

## Intent
ViralSync cannot build, its Postgres DB initializes with zero tables, and the pytest suite is red. A 4-agent audit found the stack un-runnable: the `agency/Dockerfile` copies from the wrong context, `requirements.lock` is stale, the ORM diverges from the live migration SQL, DB init is never wired, and three test blockers fail. Fix these in the user's stated order so the stack builds, bootstraps, and the suite is 100% green.

## Scope

### In Scope (ordered)
1. **Docker + lockfile + DB** — fix `agency/Dockerfile` build context/COPY, regenerate `requirements.lock` from `requirements.txt`, provision Postgres schema (wire `init_db()` or a real alembic path; `docker-compose` DB bootstrap).
2. **Pytest 100% green** — fix `dm_response.py` typing import (List/Optional/Tuple → `typing`), decide dep policy for `test_deps_prune.py` (see policy gap), fix e2e takeover 503.
3. **Bring up stack** — `docker compose up` runs and healthchecks pass.

### Out of Scope
- LiteLLM proxy bypass (crews call `litellm.completion` directly) — track, fix only if trivial.
- Frontend rebuild/refactor (Header.jsx null-deref, prerender `/admin/sistema`, mock views, Tailwind scanning) — adjacent work, note not fix.
- CI workflow repair (`.github/workflows/ci.yml`: install `uv`, fix npm ci dir, hadolint/gitleaks install, docker-lint target) — tracked out-of-scope unless it blocks phases 1–3 locally.

## Capabilities
### New Capabilities
None — infra/stabilization, no spec-level behavior change.

### Modified Capabilities
None — no existing capability behavior changes at spec level.

## Approach
Work strictly in user order; each phase independently verifiable. Phase 1: fix COPY build context to match `build: .`, recompile lock from requirements.txt, provision schema (alembic 002 real revision or `init_db()` on startup + compose postgres init). Phase 2: correct `dm_response.py` import, resolve dep-policy decision for `test_deps_prune.py`, fix takeover 503 (likely DB/auto-inject root cause). Phase 3: compose up + health checks.

## Affected Areas
| Area | Impact | Description |
|------|--------|-------------|
| `agency/Dockerfile` | Modified | COPY paths for build context `agency/` |
| `requirements.lock` | Modified | Regenerated to match requirements.txt (adds litellm/asyncpg/aiosqlite/pyjwt/jose) |
| `agency/backend/db/*` | Modified | DB init wiring; schema/ORM alignment |
| `agency/alembic/` | Modified | Real provisioning path or 002 revision |
| `agency/docker-compose.yml` | Modified | DB bootstrap; DB provisioning |
| `agency/agents/nodes/dm_response.py` | Modified | Fix typing import |
| `agency/tests/unit/test_deps_prune.py` | Modified | Align policy assertions |
| `agency/tests/e2e/test_full_pipeline.py` | Modified | Verify 200 on takeover |

## Risks
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| ORM/migration schema drift | High | Align ORM models to migration SQL; validate with e2e |
| Dep-policy change locks test conflict | High | Get decision: direct vs transitive litellm/sqlalchemy |
| `docker compose up` heavy services (ollama, minio) fail locally | Med | Health checks; start subset needed for phase 3 |
| Pruned-dep reintroduction slips into lockfile | Med | Re-run prune test after compile |
| LiteLLM "trivial fix" creeps scope | Med | Keep tracked out-of-scope |

## Rollback Plan
Revert `requirements.lock` regenerated diff via `git checkout`; revert `Dockerfile`, `docker-compose.yml`, `models.py`, migration changes individually. Dep-policy: revert `requirements.txt`/lock to pinned floors if test conflict persists. DB init stays idempotent — `CREATE IF NOT EXISTS` wherever possible.

## Dependencies
- `uv` or compatible to regenerate lockfile.
- Postgres bootstrappable in compose (schema idempotent).
- Dep-policy decision (user) on whether litellm/sqlalchemy are direct or transitive deps.

## Success Criteria
- [ ] `agency/Dockerfile` builds (`docker build .` from `agency/`).
- [ ] `requirements.lock` regenerated from requirements.txt: litellm, asyncpg, aiosqlite, sqlalchemy[asyncio], pyjwt, python-jose present.
- [ ] Fresh Postgres init yields full schema (tables `videos`, `video_metrics`, `llm_usage_log`, etc.).
- [ ] `pytest` green: all tests collect pass, 0 failures, 0 errors (baseline today: 97 passed, 3 failed, 1 error).
- [ ] `docker compose up` all healthcheck services healthy.
- [ ] E2E takeover returns 200 not 503.