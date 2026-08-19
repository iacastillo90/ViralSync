# Archive Report: 5-value-leaps — S1 (DM Leads CRM) only

- **Change**: `5-value-leaps`
- **Archived slice**: S1 — DM Leads CRM (P3) — REQ-DM-LEAD-01..06, T-S1-01..08 (PR #1)
- **Date**: 2026-08-15
- **Archive mode**: openspec (file mode) — intentional **slice-scoped partial archive** per explicit orchestrator instruction: only S1 is implemented/delivered/verified; S2–S5 remain open and stay in the active change folder.

## Status

**Archived: S1 (DM Leads CRM) — success.** S1 delta spec synced to main specs (`openspec/specs/dm-lead-crm/spec.md`), S1 section marked archived in `tasks.md`, archive report written. S2–S5 are **NOT archived** and remain open.

## What was archived (S1)

1. **Spec sync**: The S1 delta requirements (REQ-DM-LEAD-01..06) were merged into the main specs as a new capability spec:
   - `openspec/specs/dm-lead-crm/spec.md` — **Created** (6 requirements, 9 scenarios, test levels preserved). The `dm-lead-crm` main spec did not exist; the delta is a full spec for this new capability, so it was copied/transformed into the house main-spec format rather than merged into an existing file.
   - `openspec/specs/sprint-2-bot-dm-rag-handoff/spec.md` — **Unchanged**. The delta spec lists `sprint-2-bot-dm-rag-handoff` as "Modified" (REQ-DM-02 wiring, gated send), but it contains no explicit MODIFIED requirement block for REQ-DM-02; per merge rules, MODIFIED requires the full updated requirement in the delta. S1's wiring/gating behavior is captured by REQ-DM-LEAD-04 (dm_graph wiring) and REQ-DM-LEAD-06 (DM send remains gated) in the new `dm-lead-crm` spec. No destructive edit applied.
2. **Tasks marked archived**: `openspec/changes/5-value-leaps/tasks.md` — added an `Estado: Archivado` status line under the `## S1 — DM Leads CRM (PR #1)` header (house convention; the file uses `- **Descripción**` task blocks, no markdown checkboxes). **S2–S5 tasks/requirements/status were NOT altered.**
3. **No folder move**: The change folder was **not** moved to `openspec/changes/archive/` — deliberate slice-scoped archive (S2–S5 active). The folder remains `openspec/changes/5-value-leaps/` as the active change for the remaining slices.

## Task Completion Gate

- `tasks.md` uses the house task format **without checkboxes** (no `- [ ]` markers exist), so check-box reconciliation does not apply.
- `verify-report.md` proves 8/8 S1 tasks PASS with runtime evidence (38/38 S1 tests + 10/10 regression, exit 0) and 6/6 requirements COMPLIANT — the persisted verify artifact reflects the final S1 state.

## Verification & review artifact references

- `openspec/changes/5-value-leaps/verify-report.md` — **S1 verification: PASS** (38/38 S1 + 10/10 regression, exit 0; 6/6 REQ compliant; 8/8 tasks PASS).
- `openspec/changes/5-value-leaps/reviews-s1a2/` — receipt `terminal_state: approved` (`final_candidate_tree af186a98e4af10820da29c4303193c02bcc953bb`); pre-pr gate `base_ref d0d007a → revision b6e7a03`.
- `openspec/changes/5-value-leaps/reviews-s1b/` — receipt `terminal_state: approved` (`final_candidate_tree 1ee7c078c505ddfc1c412e96264cc30469b1e7a9`); pre-pr gate `base_ref b6e7a03 → revision 951c4d3`; evidence file corroborates 23 passed.
- Deliverable chain (git): `d0d007a` (s1a1) → `616bde7` → `d651ce0` → `b6e7a03` (s1a2) → `453dbc7` → `951c4d3` (s1b, HEAD of `feat/5-value-leaps-s1b`).
- Review ledger s1b: 1 CRITICAL (`RELIABILITY-001`), 3 WARNING, 1 SUGGESTION — all findings were addressed in the s1b fix batch; final verification approved by the s1b gate.

## Intentional-with-warnings annotations (recorded per archive policy)

1. **Slice-scoped partial archive (orchestrator instruction)**: only S1 archived while S2–S5 remain open in the active change folder. The change folder was intentionally NOT moved to `openspec/changes/archive/`.
2. **Missing apply-progress artifact (verify-report CRITICAL, process-only)**: `verify-report.md` reports one CRITICAL — no `apply-progress` artifact / Strict-TDD evidence table exists on disk or in Engram. The report classifies it as an apply-phase artifact/process gap, NOT an implementation defect. The orchestrator adjudicated it non-blocking (launch explicitly: "Verify status is PASS … gates allow") and instructed archive to proceed. Independence was re-confirmed here: review receipts for both gates are `approved` and the s1b evidence file records 23 passed.
3. **s1a2-approved design deviation (WARNING)**: webhook sync-failure returns HTTP 500 (forces Meta redelivery) instead of acking `200 queued_dlq`; approved by the s1a2 gate, breaks no REQ-DM-LEAD requirement. Carried as-is.

## Out of scope — S2–S5 remain OPEN (NOT archived)

- **S2 — Voice Personas (PR #2, batches S2a/S2b)**: REQ-VOICE-01..05, T-S2a-01..05, T-S2b-01..03 — not implemented, not verified, not archived.
- **S3 — Auto-Publicación (PR #3)**: REQ-PUB-01..07, T-S3-01..06 — not implemented, not verified, not archived.
- **S4 — Competitor Benchmark (PR #4)**: REQ-COMP-01..04, T-S4-01..06 — not implemented, not verified, not archived.
- **S5 — PDF Reports (PR #5)**: REQ-PDF-01..04, T-S5-01..07 — not implemented, not verified, not archived.

The delta spec `openspec/changes/5-value-leaps/spec.md` still contains the full S1–S5 requirement set and stays in the active change folder; only the S1 requirements were synced to main specs. S2–S5 requirement blocks are NOT present in any `openspec/specs/` file.

## Main specs (source of truth) updated

| Domain | Action | Details |
|--------|--------|---------|
| `dm-lead-crm` | Created | 6 requirements synced from S1 delta (REQ-DM-LEAD-01..06), 9 scenarios, test levels unit/integration preserved |

## Archive contents (S1 slice)

- proposal.md ✅ (S1 scope defined)
- spec.md ✅ (delta, full S1–S5 — S1 portion synced)
- design.md ✅ (S1 section implemented per design)
- tasks.md ✅ (8/8 S1 tasks PASS; S1 section marked archived)
- verify-report.md ✅ (S1 PASS)
- reviews/ ✅ (policy + s1a1 review bundle)
- reviews-s1a2/ ✅ (approved receipt)
- reviews-s1b/ ✅ (approved receipt)

## SDD Cycle Status

S1 cycle complete: planned → specified → designed → implemented → verified → archived. Ready for S2 (Voice Personas). The SDD cycle for `5-value-leaps` as a whole remains OPEN until S2–S5 are archived.