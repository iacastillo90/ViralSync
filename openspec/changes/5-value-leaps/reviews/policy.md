# Review Policy — 5-value-leaps S1a1

- **transaction_id**: `txn-5vl-s1a1-616bde7`
- **lineage_id**: `5-value-leaps-s1a1`
- **target**: commit `616bde7` (branch `feat/5-value-leaps-s1a1`), diff vs `main` (30bcddf)
- **mode**: ordinary-4r
- **trigger**: post-apply (no prior valid receipt)
- **risk_classification**: High (465 authored changed lines > 400) → full 4R
- **initial_lenses**: review-risk, review-reliability, review-readability, review-resilience (one exhaustive sweep each)
- **refuter**: none required (no inferential severe findings — all severe findings deterministic)
- **correction**: one correction transaction, one work unit (RESILIENCE-001)
- **scoped_fix_delta_validator**: executed, returned `approve`

## Target snapshot

- `genesis`: main @ `30bcddf`
- `final_candidate_tree`: working tree of `feat/5-value-leaps-s1a1` at commit `616bde7` + uncommitted fix delta
- Path scope: `agency/backend/db/models.py`, `agency/backend/services/lead_scoring.py`, `agency/migrations/011_leads_qualification.sql`, `agency/workers/celery_app.py`, `agency/workers/lead_persist_task.py`, `agency/tests/unit/test_lead_scoring.py`, `agency/tests/unit/test_lead_persist_task.py`, `agency/tests/unit/test_db_indexes.py`, `agency/tests/unit/test_celery_tasks.py`

## Scope / non-goals

- Wiring webhook→worker (REQ-DM-LEAD-01 integration) is delivered by chained PR S1a2 (`f40467e`), NOT part of this target. RELIABILITY-001 marked `fixed` by chain evidence, not corrected here.
- WARNING/SUGGESTION findings are `info` and non-blocking.

## Outcome

- **Terminal state**: approved (fix-delta validator approved; no unresolved BLOCKER/CRITICAL in target scope after fix)
