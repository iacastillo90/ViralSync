# Review Policy — txn-2026-08-09-pipeline-production-gaps

## Operation
- Type: ordinary bounded implementation review (4R) post-apply, explicit `review/start(pipeline-production-gaps)`.
- Target snapshot (immutable genesis): `bf7dd12..022883a`; path scope: `agency/`, `requirements.txt`, `requirements.lock`.
- Trigger classification: High tier (security/auth/payments, data exposure, >400 authored changed lines) → full 4R: `review-risk`, `review-readability`, `review-reliability`, `review-resilience`. Each lens ran exactly one exhaustive sweep; no extra sweeps, no fan-out.

## Lens selection
- Dominant risk at High tier → full 4R set. Each lens emits neutral structured claims with proof refs; findings freeze after the initial selected-lens review.

## Evidence routing
- Deterministic severe findings (BLOCKER/CRITICAL) → corroborated with proof; never invoke a refuter: RISK-01, RELIABILITY-001, RELIABILITY-002, RESILIENCE-001, RESILIENCE-002.
- Inferential severe findings from all lenses → merged into exactly ONE detached refuter operation: RELIABILITY-003 (refuter verdict: corroborated).
- Insufficient findings → inconclusive; none occurred.
- WARNING/SUGGESTION rows are `info`; they never drive correction or block approval (24 WARNING + 14 SUGGESTION remain info).

## Correction and scoped validation
- Exactly one correction transaction (WU-FIX-1..5), one atomic commit per work unit, each mapped to frozen accepted/blocking IDs, changes only the immutable genesis path set, independent rollback boundary (git revert per commit).
- Exactly one scoped fix-delta validator ran: detached, read-only, received only frozen ledger + immutable fix delta; returned `approve`. A failed original criterion escalates; none did.

## Independent final verification
- Independent requirements/runtime verification: requirements/scenarios from archived spec remain satisfied at corrected HEAD `f00f9be`; full suite `AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/ -q` → 213 passed / 1 skipped (real-keys gate) / 0 failed, verified by the orchestrator and by the scoped validator.
- Snapshot identity: genesis `961edc3`, base tree `bf7dd12`, candidate `022883a`, corrected `f00f9be`.
- Counter coherence: 4 lens sweeps, 1 refuter batch (consumed), 1 correction transaction, 1 scoped validation; corroborated IDs equal correction IDs; no pending severe work.
- Terminal state: `approved`.

## Lifecycle gates
- Pre-commit / pre-push / pre-PR / release must call the native receipt validator for the same content-bound receipt; they never create a new review budget and never silently start Judgment Day.
- Missing, scope-changed, invalidated, or escalated results fail closed via machine-readable denial.
