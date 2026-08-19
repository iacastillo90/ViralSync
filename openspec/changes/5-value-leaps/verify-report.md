# Verify Report: 5-value-leaps — S1 (DM Leads CRM) only

- **Change**: `5-value-leaps`
- **Slice verified**: S1 (DM Leads CRM, P3) — REQ-DM-LEAD-01..06, T-S1-01..08
- **Scope note**: S2–S5 are NOT implemented and NOT verified here. The archive phase handles S1-only scope.
- **Mode**: Strict TDD (active — module `strict-tdd-verify.md` loaded)
- **Branch/commit**: `feat/5-value-leaps-s1b` @ `951c4d3` (tree `1ee7c078` — matches `reviews-s1b/receipt.json` `final_candidate_tree`)
- **Review gates**: s1b `terminal_state: approved` (full_reviews=1, refuter_batches=1, fix_batches=1, scoped_fix_validations=1, final_verifications=1); s1a2 and s1b `pre-pr` gates present with test evidence
- **Artifact persistence**: openspec file mode — this report is written to the change dir root

## Status

`S1 verification: PASS` — 38/38 S1 tests pass (plus 10 webhook/lead regression tests), all 6 requirements and all 8 tasks verified against implementation with file:line evidence. One process-level CRITICAL (missing apply-progress TDD evidence table) is reported for orchestrator adjudication; it is an apply-phase artifact gap, not an implementation defect. No failing or untested spec scenario.

## Test evidence (exact commands + counts)

Run from repo root on branch `feat/5-value-leaps-s1b` @ `951c4d3`:

```bash
cd /home/ivan/Desktop/AgentMarketingIA && AGENCY_ENV=dev ./venv/bin/python -m pytest agency/tests/unit/test_lead_persist_task.py -q
# -> 12 passed, 42 warnings in 8.60s
cd /home/ivan/Desktop/AgentMarketingIA && AGENCY_ENV=dev ./venv/bin/python -m pytest agency/tests/unit/test_fastapi_endpoints.py -q
# -> 11 passed, 15 warnings in 9.40s
cd /home/ivan/Desktop/AgentMarketingIA && AGENCY_ENV=dev ./venv/bin/python -m pytest agency/tests/unit/test_lead_scoring.py -q
# -> 6 passed in 0.12s
cd /home/ivan/Desktop/AgentMarketingIA && AGENCY_ENV=dev ./venv/bin/python -m pytest agency/tests/unit/test_db_indexes.py -q
# -> 5 passed in 0.09s
cd /home/ivan/Desktop/AgentMarketingIA && AGENCY_ENV=dev ./venv/bin/python -m pytest agency/tests/unit/test_celery_tasks.py -q
# -> 4 passed, 1 warning in 7.01s
```

Regression safety net (webhook/lead surface, pre-existing tests):

```bash
cd /home/ivan/Desktop/AgentMarketingIA && AGENCY_ENV=dev ./venv/bin/python -m pytest agency/tests/unit/test_lead_automation.py agency/tests/unit/test_brechas_consolidation.py agency/tests/unit/test_enterprise_4_events.py agency/tests/unit/test_frontend_sse_views.py -q
# -> 10 passed in 2.45s
```

Combined S1 suite: `38 passed, 58 warnings` — **0 failed, 0 skipped**.
Test output SHA-256 (5 S1 files combined): `d340ec560d25aeedff98cdc2a7b6a7168eed8c62fc925f63ae72d7e61143fc5d`
Test exit code: `0`.
No build step exists for this Python change; `pytest` collection is the type/syntax gate and exited 0.

## Per-requirement verdicts (REQ-DM-LEAD-01..06)

Compliance statuses: ✅ COMPLIANT (covering test passed) · ⚠️ PARTIAL · ❌ UNTESTED/FAILING.

| Req | Verdict | Implementation evidence | Covering tests (all passed) |
|-----|---------|--------------------------|------------------------------|
| REQ-DM-LEAD-01: webhook persists Lead with tenant resolution (async) | ✅ COMPLIANT | `backend/main.py:204-212` resolves tenant + enqueues `persist_instagram_lead.delay`; `workers/lead_persist_task.py:245-260` INSERT with resolved `tenant_id`, `platform='instagram'`, `status='Nuevo'`; tenant resolution `backend/webhooks/instagram_inbound.py:24-65` | `test_lead_persist_task.py::test_lead_persisted_with_resolved_tenant`, `test_webhook_payload_resolves_tenant_and_persists`, `test_webhook_endpoint_enqueues_worker_and_returns_200`, `test_webhook_payload_without_account_falls_back_to_default`; `test_fastapi_endpoints.py::test_get_leads_exposes_scoring_fields` |
| REQ-DM-LEAD-02: qualification schema migration (score col + status index) | ✅ COMPLIANT (contract-style; see SUGGESTION) | `migrations/011_leads_qualification.sql:9-18` (`qualification_score INTEGER NOT NULL DEFAULT 0`, `platform`, `dedup_hash`, `ALTER COLUMN video_id DROP NOT NULL`, `uq_leads_dedup_hash`, `idx_leads_status`); model `backend/db/models.py:144-153` | `test_db_indexes.py::test_migration_011_exists`, `test_migration_011_declares_qualification_schema`, `test_lead_model_declares_qualification_columns` |
| REQ-DM-LEAD-03: keyword + intent scoring (0-100, Nuevo/Contactado/Calificado) | ✅ COMPLIANT | `backend/services/lead_scoring.py:36-68` — spam→(5,Nuevo) <30; purchase_intent+keyword→(90,Calificado) ≥60; objection/question+keyword→(45,Contactado); no keyword→(10,Nuevo) | `test_lead_scoring.py` (6 tests: both spec scenarios + 4 triangulations, incl. `test_audio_keyword_high_intent_is_calificado` for the REQ-DM-LEAD-01 scenario) |
| REQ-DM-LEAD-04: dm_graph wiring with persisted classification | ✅ COMPLIANT | `workers/lead_persist_task.py:102-128` (`build_dm_graph().ainvoke`, fallback `classify_intent`) + `:163-175` persists `{intent, confidence, ts}` JSON into `conversacion_history` | `test_lead_persist_task.py::test_classification_persisted_in_conversacion_history`, `test_dm_graph_failure_falls_back_and_keeps_persistence` |
| REQ-DM-LEAD-05: webhook idempotency (dedup hash) | ✅ COMPLIANT | `workers/lead_persist_task.py:68-71` sha256(ig_user_id\|message); DB unique index `uq_leads_dedup_hash` (011:16); model `dedup_hash` unique (`models.py:151`) | `test_lead_persist_task.py::test_repeated_webhook_does_not_duplicate` (count==1), `test_retry_after_partial_insert_recovers_classification` (count==1, same row) |
| REQ-DM-LEAD-06: DM send remains gated | ✅ COMPLIANT | `agents/dm_graph.py` and `agents/nodes/dm_response.py` NOT in the change diff (git `main...HEAD` shows no edits — `node_send_dm_reply` untouched); `lead_persist_task.py` never calls the send path and never writes `pending_manual` | `test_lead_persist_task.py::test_no_dm_send_side_effects` (wraps real `node_send_dm_reply`, asserts no `pending_manual` in result or history) |

**Compliance summary**: 6/6 requirements compliant. 0 failing, 0 untested.

## Per-S1-task verdicts (T-S1-01..08)

| Task | Verdict | Evidence (file:line) | Covering test |
|------|---------|----------------------|---------------|
| T-S1-01: Migration 011 | ✅ PASS | `agency/migrations/011_leads_qualification.sql:9-18` — all columns + DROP NOT NULL + both indexes present | `test_db_indexes.py::test_migration_011_exists`, `test_migration_011_declares_qualification_schema` |
| T-S1-02: Lead model updated | ✅ PASS | `agency/backend/db/models.py:144-153` — `qualification_score`, `platform` (default instagram), `dedup_hash` unique nullable, `video_id` nullable, `idx_leads_status` in `__table_args__` (models.py:129) | `test_db_indexes.py::test_lead_model_declares_qualification_columns` |
| T-S1-03: Pure scoring service | ✅ PASS | `agency/backend/services/lead_scoring.py:44-68` — `score_lead(message, intent) -> (int, str)`, no IO | `test_lead_scoring.py` (6/6 passed) |
| T-S1-04: Worker persist_instagram_lead | ✅ PASS | `agency/workers/lead_persist_task.py` — dedup `:68-71`, INSERT `:243-260`, classify+score+history `:149-181`, dm_graph best-effort + fallback `:102-128`, `node_send_dm_reply` untouched | `test_lead_persist_task.py` (10/12 tests cover this task) |
| T-S1-05: Celery registration + webhooks queue | ✅ PASS | `agency/workers/celery_app.py` — `"workers.lead_persist_task"` in include (celery_app.py:24), route `workers.lead_persist_task.* → webhooks` (celery_app.py:39) | `test_celery_tasks.py::test_lead_persist_task_discoverable_and_routed_to_webhooks` |
| T-S1-06: Tenant resolution in webhook | ✅ PASS | `agency/backend/webhooks/instagram_inbound.py:24-65` (`_extract_account_id`, `_resolve_tenant_from_payload` via `tenants.instagram_business_account_id`); SSE to resolved tenant `:113`, `:129` | `test_lead_persist_task.py::test_webhook_payload_resolves_tenant_and_persists` (tenant_b), `test_webhook_payload_without_account_falls_back_to_default` |
| T-S1-07: Enqueue worker from main | ✅ PASS | `agency/backend/main.py:202-212` (`_resolve_tenant_from_payload` + `process_instagram_webhook_payload(payload, tenant_id=…)` + `persist_instagram_lead.delay(...)` loop); sync-failure → 500 (`main.py:214-222`, RESILIENCE-001) | `test_lead_persist_task.py::test_webhook_endpoint_enqueues_worker_and_returns_200`, `test_webhook_endpoint_returns_500_on_sync_failure_not_ack` |
| T-S1-08: GET /{tenant}/leads exposes scoring | ✅ PASS | `agency/backend/routers/leads.py:68-79` (`_extract_intent_from_history`) + `:105-107` (status, qualification_score, intent fields) | `test_fastapi_endpoints.py::test_get_leads_exposes_scoring_fields` |

**Task completeness**: 8/8 S1 tasks PASS.

## Design coherence (S1)

| Design decision | Followed? | Evidence |
|-----------------|-----------|----------|
| Worker Celery async (queue `webhooks`) instead of inline persist | ✅ | celery_app.py include+route; main.py `.delay` |
| Idempotency via `dedup_hash` UNIQUE (sha256 user+message) | ✅ | 011:16, models.py:151, worker :68-71 |
| `video_id` nullable in 011 (webhook has no video) | ✅ | 011:13, models.py:142, asserted `lead.video_id is None` |
| Scoring as pure service without IO | ✅ | lead_scoring.py (no imports outside typing) |
| `dm_graph` best-effort + `classify_intent` fallback | ✅ | lead_persist_task.py:102-128 |
| Send gated — `node_send_dm_reply` intact | ✅ | dm_graph.py / dm_response.py unchanged in diff |
| SSE to resolved tenant (not "default") | ✅ | instagram_inbound.py:113,129 |

## Issues found

**CRITICAL** (process/artifact — orchestrator adjudication required):
1. **Missing apply-progress artifact / Strict TDD evidence table.** No `apply-progress` artifact exists on disk (`openspec/changes/5-value-leaps/`) nor in Engram (`mem_search "sdd/5-value-leaps/apply-progress" → no results`). Per `strict-tdd-verify.md`, an absent TDD Cycle Evidence table is CRITICAL (apply phase did not report TDD evidence). Mitigating fact: all test files referenced by the tasks exist and pass on independent execution (RED/GREEN re-confirmed here), and the 4R gate receipts (`reviews-s1b/receipt.json`, evidence `23 passed`) corroborate the apply-phase test runs. This is an artifact/process gap, not an implementation defect. Orchestrator decides whether it blocks the archive phase.

**WARNING**:
1. **Design deviation on webhook error path (approved in s1a2 review).** Design step 3 specified "responde 200 al webhook" with DLQ enqueue on sync error; implementation returns `HTTPException 500` on sync failure instead of acking `200 queued_dlq` (`main.py:214-222`) per RESILIENCE-001 (the DLQ path did not persist; 500 forces Meta redelivery). Approved by the s1a2 gate; does not break any REQ-DM-LEAD requirement (no error-ack semantics specified).
2. **Safety-net run not independently verifiable.** `agency/tests/conftest.py` (added `CELERY_TASK_ALWAYS_EAGER`/`CELERY_TASK_EAGER_PROPAGATES`) and pre-existing files (`test_db_indexes.py`, `test_celery_tasks.py`, `test_fastapi_endpoints.py`, `test_lead_automation.py`) were modified, and the house task format has no checkboxes; without apply-progress the pre-modification safety-net execution cannot be confirmed retroactively. Current regression run of the webhook/lead surface passes (10 tests).

**SUGGESTION**:
1. REQ-DM-LEAD-02 is verified contract-style (migration file exists + declares schema + model maps columns) rather than by executing the migration against a live pre-migration schema. Consistent with the repo convention (`test_db_indexes.py`), but a real apply test would strengthen the migration claim.
2. Test layer: all S1 tests live under `agency/tests/unit/` even though REQ-DM-LEAD-01/04 are spec-tagged "integration" and several tests exercise real SQLite DB + ASGI transport + Celery eager routing (integration-flavored). No `tests/integration/` suite exists in the repo. Non-blocking; SUGGESTION only (informational per strict module).
3. Coverage analysis skipped — no coverage tool configured (`pytest.ini` has no coverage; no `.coveragerc`). Not a failure.

## Strict TDD compliance

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported (apply-progress) | ❌ | Missing — no apply-progress artifact on disk or in Engram (CRITICAL, see Issues) |
| All tasks have tests | ✅ | 8/8 S1 tasks map to a test file (lead_persist_task, lead_scoring, db_indexes, celery_tasks, fastapi_endpoints) |
| RED confirmed (test files exist) | ✅ | 5/5 test files verified present |
| GREEN confirmed (tests pass on execution) | ✅ | 38/38 S1 tests pass + 10/10 regression tests, exit 0 |
| Triangulation adequate | ✅ | REQ-DM-LEAD-03: 6 scoring cases (2 scenarios + 4 triangulations); REQ-DM-LEAD-01/04/05: 12 persist cases |
| Safety Net for modified files | ⚠️ | Not verifiable (no apply-progress); current regression set green |

**TDD Compliance**: 5/6 verifiable checks pass; 1 CRITICAL (missing TDD evidence table).

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit (incl. integration-flavored SQLite/ASGI/exercises) | 38 (S1) + 10 (regression) | 5 + 4 | pytest |
| Integration | 0 | 0 | — (no tests/integration suite in repo) |
| E2E | 0 (S1) | 0 | playwright/cypress not used for S1 |
| **Total** | **48** | **9** | |

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected (not a failure).

### Assertion Quality
✅ All assertions verify real behavior. Audit of the 5 S1 test files found: no tautologies; no ghost loops (the only loop in `test_db_indexes.py` iterates a static non-empty model list); no type-only assertions used alone (all combined with value assertions on status/score/count); no smoke-only tests; mock ratio healthy (1 mock per test vs 2–6 value assertions; mocks used only for external LLM/Redis/config, not production logic).

### Quality Metrics
Linter: ➖ Not available. Type checker: ➖ Not available (no ruff/flake8/mypy/pylint configured or installed in venv).

## Verdict

**S1 verification: PASS** — all 8 S1 tasks and all 6 REQ-DM-LEAD requirements verified against implementation with runtime test evidence (38/38 S1 + 10/10 regression passed, exit 0). The single CRITICAL finding is the missing apply-progress/TDD-evidence artifact (process gap, orchestrator adjudication); it does not affect S1 implementation correctness. S2–S5 are explicitly out of scope and unverified — the archive phase must handle S1-only scope.