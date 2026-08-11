# Tasks: Health Honesty

> Source: spec.md (REQ-PH-01..04, 11 scenarios) + design.md (D-1..D-6) + code verified at HEAD `ae7a189`. Strict TDD: RED test → GREEN implementation → REFACTOR; suite green at the END of the slice (baseline `297 passed, 1 skipped`, canonical `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/ -q`). Zero-token only: monkeypatched module-level probes, hang-factory fakes (`redis.asyncio.Redis.from_url`, `qdrant_client.AsyncQdrantClient`, `health.async_engine`), TestClient; compose test reads raw YAML text (no docker/network/LLM). Single slice, one PR.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines (total) | ~250 authored (adds+deletes) |
| 400-line budget risk | **Low** (single slice under budget) |
| Chained PRs recommended | No |
| Suggested split | single PR → main |
| Delivery strategy | single-pr (auto; size:exception NOT required) |
| Chain strategy | pending (no chaining) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| WU-1 | Whole change: honest probes + aggregation + version source + compose fix (REQ-PH-01..04) | PR 1 (→main) | `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/unit/test_health_honesty.py tests/unit/test_enterprise_phases_0_to_5.py -q` then full suite | N/A — TestClient + monkeypatched probes + hang fakes; compose config asserted as raw YAML text (no docker run) | `git revert` the slice: restores `health.py`/`main.py:61`, deletes `backend/__init__.py` + `test_health_honesty.py`, drops compose lines → old contract instant, no DDL |

Dependencies (strict TDD, no red window outside the slice): TPH-001/002 (RED, no deps) → TPH-003 (GREEN, PH-03 source) → TPH-004 (GREEN, PH-01/02, needs `backend.__version__` from TPH-003) → TPH-005 (GREEN, PH-04, independent) → TPH-006 (REFACTOR sweep, needs all).

## Phase 1 — RED: honest-contract tests first (REQ-PH-01..04, ~140 lines)

- [x] **TPH-001 (RED)** — Title: health honesty test suite. Files: `agency/tests/unit/test_health_honesty.py` (NEW, ~130). Cover all 11 scenarios: `test_all_dependencies_healthy_reports_healthy` (PH-01-1), `test_database_down_reports_unhealthy` (PH-01-2), `test_redis_down_reports_degraded` (PH-01-3), `test_qdrant_down_reports_degraded` (PH-01-4), `test_timeout_caps_probe_no_hang` (PH-01-5: hang-factory monkeypatch on `health.async_engine`/`redis.asyncio.Redis.from_url`/`qdrant_client.AsyncQdrantClient` then await the REAL `check_*` → resolves within cap as degraded/unhealthy), `test_healthy_returns_200_with_all_keys_and_latency` (PH-02-1: keys `status, version, database, redis, qdrant` + optional `latency_ms`/`checked_at`), `test_database_down_returns_503_unhealthy` (PH-02-2), `test_only_noncritical_down_returns_200_degraded` (PH-02-3), `test_health_version_matches_app_and_backend_version` (PH-03-1), `test_version_change_propagates_without_hardcode` (PH-03-2: monkeypatch `backend.__version__` → both report new value), `test_compose_qdrant_url_reaches_service` (PH-04-1: raw YAML text asserts backend env `QDRANT_URL=qdrant:6333` + qdrant `healthcheck:` with bash `/dev/tcp`). RED: module-level probes/`backend.__version__`/compose env absent. Zero-token ✓. Rollback: test-only. Est: ~130.
- [x] **TPH-002 (RED)** — Title: extend fase-0 health assertions. Files: `agency/tests/unit/test_enterprise_phases_0_to_5.py:23-31` (extend `test_fase_0_unified_health_check_endpoint`, ~10). Add `from backend import __version__`; assert `data["version"] == __version__` and `data["status"] in ("healthy", "degraded")` (default env: db healthy SQLite, redis/qdrant refused → degraded → stays HTTP 200, existing 4-key asserts untouched). RED: `backend.__version__` AttributeError (no `__init__.py`). Zero-token ✓. Rollback: test-only. Est: ~10.

## Phase 2 — GREEN: implementation (REQ-PH-01..04, ~100 lines)

- [x] **TPH-003 (GREEN)** — Title: version single source (D-2). Files: `agency/backend/__init__.py` (NEW, `__version__ = "1.0.0"`, imports nothing — no circularity, package init finishes before main/health bodies run), `agency/backend/main.py:61` (`version="1.0.0"` → `from backend import __version__` + `version=__version__`). Acceptance: PH-03-1 (app side), PH-03-2 (propagation via app). Rollback: WU-1 boundary. Est: ~5.
- [x] **TPH-004 (GREEN)** — Title: honest async probes + aggregation + 503 semantics (D-1). Files: `agency/backend/routers/health.py` (rewrite 56 → ~100). Module-level seams `check_database` (SELECT 1 via `backend.db.session.async_engine`, `wait_for(..., 2)`; FORCE_SQLITE → real SQLite SELECT 1), `check_redis` (lazy `import redis.asyncio`, `from_url(REDIS_URL)`, `wait_for(ping(), 1)`, `aclose()`), `check_qdrant` (lazy `from qdrant_client import AsyncQdrantClient`, `wait_for(get_collections(), 3)`, `close()`); any exception incl. `asyncio.TimeoutError` → db `unhealthy`, redis/qdrant `degraded`; `asyncio.gather` (total ≈ slowest); env-overridable timeout constants; `aggregate_status`: unhealthy iff db≠healthy, degraded iff any≠healthy, else healthy; endpoint returns 503 iff unhealthy else 200, body `{status, version, database, redis, qdrant}` + `latency_ms`/`checked_at`, `version` from `backend.__version__`; no fabricated "healthy". Acceptance: PH-01-1/2/3/4/5, PH-02-1/2/3, PH-03-1/2 (health response). Rollback: WU-1 boundary. Est: ~90.
- [x] **TPH-005 (GREEN)** — Title: compose probe reachability (D-4). Files: `agency/docker-compose.yml` (backend env :96 `QDRANT_HOST=qdrant` → `QDRANT_URL=qdrant:6333`; qdrant service :35-41 add healthcheck `test: ["CMD", "bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/6333 && echo -e 'GET /readyz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' >&3 && grep -q '200' <&3"]` — bash `/dev/tcp` builtin, no curl/wget/nc, `/readyz` 200 only when storage ready). Code reads only `QDRANT_URL`. Acceptance: PH-04-1 (via TPH-001 config test; `depends_on` stays `service_started` — out of scope per design). Rollback: WU-1 boundary. Est: ~5.

## Phase 3 — REFACTOR: slice sweep (~5 lines)

- [x] **TPH-006 (REFACTOR)** — Title: slice sweep. Verify full suite green (baseline 297 passed / 1 skipped + ~11 new); grep for hardcoded `"1.0.0"` / fabricated `"healthy"` leftovers in health path; confirm no sync-blocking calls in `/health` flow (only async clients + gather). Rollback: WU-1 boundary. Est: ~5.

## Dependency order & zero-token constraint

TPH-001 → TPH-002 → TPH-003 → TPH-004 → TPH-005 → TPH-006 (single slice, one PR → main; no chaining). Suite green at end of slice. Zero-token: monkeypatched probes cover every status path; hang-factory fakes prove `wait_for` caps (PH-01-5) with no real network; `FORCE_SQLITE=true` keeps db probe green on SQLite (SELECT 1 dialect-agnostic); compose test is raw YAML text, no docker. Design Threat Matrix: N/A (no routing/shell/subprocess/VCS boundary; compose healthcheck is declarative config, not executed code).
