# Archive Report: storage-honesty

- **Change**: storage-honesty — honest storage: real media list/delete/config guards (`media-storage-honesty` NEW), renderer returns a real signed URL (REQ-SH-04), `products.object_key` persisted + re-signed on read (REQ-PERSIST-05 MODIFIED)
- **Archived at**: 2026-08-11
- **Status**: success
- **Mode**: hybrid (openspec filesystem + Engram)
- **Implementation commits** (stacked-to-main, no push, no PR): base `0b5d13b` → head `d503e89`; 13 commits (12 impl + 1 RISK-001 correction), 20 files, +1366/−151. See verify-report task table for per-task commits (ce94306 → 605b6ab → a56f2c8 → 42b4132/8caa100 → 53e030a → 3019436 → 4b5e22c → ebf660c → fcce7fe → 65a7afa → d503e89).
- **Delivery**: auto-forecast, chained stacked-to-main (`size:exception` APPROVED, ~475 authored lines > 400 budget). PRs not pushed — orchestrator delivers 3 stacked PRs per slice (PR1 core minio+API, PR2 renderer, PR3 migration+DAO).

## Task Completion Gate

- [x] All implementation tasks checked in `tasks.md` — **13/13 `[x]`** (TSH-001..013) plus RISK-001 correction task ✅, zero stale unchecked tasks. No archive-time reconciliation needed.
- [x] No open CRITICAL verification findings: verify verdict **PASS WITH WARNINGS** — full suite **297 passed / 1 skipped** (x3 independent runs, deterministic; skip = pre-existing real-keys gate `test_llm_router.py:281`, NOT new); focused changed-file set **67 passed**; **19/19 scenarios PASS**; D-1..D-8 honored in code.
- [x] Review gate: no native 4R `reviews/` folder exists for this change (verify-only flow — no transaction/ledger/receipt artifacts were produced; the fix-delta validator verdict for RISK-001 is recorded in Engram obs #264, `approve`). The verify-report (obs #265) is the terminal quality gate: no CRITICAL, no spec breaks, all requirements MET.
- [x] All required artifacts present and archived (proposal, delta spec, design, tasks, verify-report).

## Specs Synced (delta → base)

The change's delta spec is a single flat `spec.md` (repo single-file convention, aligning with archived `2026-08-09-pipeline-production-gaps` and `2026-08-10-pipeline-terminal-truth`). It creates one new capability spec, adds one requirement, and modifies one requirement. All syncs are additive/extending — no REMOVED or RENAMED requirements, no destructive merge.

| Domain | Action | Details |
|--------|--------|---------|
| media-storage-honesty | **Created** | `openspec/specs/media-storage-honesty/spec.md` (NEW capability) — **REQ-SH-01** honest list (real objects under `{tenant_id}/` with presigned URLs, no `_MEDIA_REGISTRY`, no demo seeds, empty list for empty tenants, `MINIO_PUBLIC_ENDPOINT` host override; SH-01-1/2/3), **REQ-SH-02** honest delete (prefix-guarded `remove_object`, idempotent, 404 for unknown id, out-of-prefix refused; SH-02-1/2/3/4), **REQ-SH-03** config honesty (fail-fast `minioadmin` creds in staging/prod, `secure` derived from scheme/`MINIO_SECURE`, init errors surfaced; SH-03-1/2/3/4). 3 requirements, 11 scenarios. |
| video-scene-render-contract | Updated | `openspec/specs/video-scene-render-contract/spec.md` — **ADDED REQ-SH-04** (renderer `upload_to_minio` returns a real `presigned_get_object` URL for the private bucket, never the fabricated `http://{endpoint}/{bucket}/{key}` root; all other render behavior unchanged; scenarios SH-04-1/2/3). Purpose paragraph updated with the real-signed-URL sentence (consistency edit matching the merged requirement, per prior archive convention). REQ-VSR-01..06 untouched. |
| pipeline-persistence-writes | Updated | `openspec/specs/pipeline-persistence-writes/spec.md` — **REQ-PERSIST-05 MODIFIED** (full requirement block replaced: persist `products.object_key` not the presigned URL via migration `005_*.sql` additive nullable; `upsert_product` stores key; read paths re-sign via `presigned_get_object` honoring `MINIO_PUBLIC_ENDPOINT`; legacy `object_key` NULL falls back to stored `product_image_url`; LLM prompt receives working URL text; pipeline continues when no product). PERSIST-05-1 preserved (updated to assert object_key) + PERSIST-05-2 unchanged; **SH-05-3/4/5 appended**. Purpose paragraph updated with the object_key/re-sign sentence (consistency edit). REQ-PERSIST-01/02/03/04 untouched. |

## Verification Evidence (linkage)

- **Verify report**: Engram obs **#265** (`sdd/storage-honesty/verify-report`, `obs-048e1613bfa0fb1d`) + local `verify-report.md` (archived with the change folder). Verdict **PASS WITH WARNINGS** — REQ-SH-01..04 + REQ-PERSIST-05 all MET, 19/19 scenarios mapped to named passing tests; D-1..D-8 honored; TDD evidence validated from apply-progress obs #261 (RED→GREEN commit ordering independently confirmed, e.g. ce94306→605b6ab, 53e030a→3019436, 4b5e22c→ebf660c).
- **Full suite (HEAD `d503e89`)**: `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/ -q` → **297 passed / 1 skipped** (x3 runs, deterministic); focused changed-file set (7 test files) → **67 passed**.
- **Zero-token**: FakeMinio list/remove/presign recording (3 files) + renderer `_StubMinio` in `sys.modules`; `db_session` SQLite (StaticPool); ASGITransport; no real network/LLM/docker.

## Warnings & Deviations (none spec-breaking, none blocking)

Warnings (verify-report #1-#4): SH-02-3 spec/impl wording divergence (reconciled below); apply-progress obs #261 narrative TDD evidence (substantively verified via commit ordering + runtime); `graph.py:36` non-Optional `product_object_key` type (runtime-safe); renderer whole-file coverage 53% (changed path covered by 7 dedicated tests). Deviations #1-#9 documented in verify-report (SH-02-3 wording, signer `secure` inheritance, renderer lacks minioadmin fail-fast, migration 005 manual `psql` apply, `_iso_last_modified` fallback, `title` alias field, graph.py Optional typing, duplicated `_derive_secure`/`_host_port`, 4 divergent Minio fakes). All informational; no CRITICAL.

## SH-02-3 Wording Reconciliation (spec ↔ implemented semantics)

The delta scenario SH-02-3 ("no object matches `media_id` → 404") diverged from the implemented semantics documented in verify-report (Deviation #1, Warning #1): an **in-prefix-but-nonexistent** key returns **idempotent 200** (S3 delete-204 semantics, consistent with SH-02-2), while **404** is returned for **unknown ids and out-of-prefix keys** (out-of-prefix → guard → False → 404; covering test `test_delete_media_unknown_id_returns_404` asserts the 404 contract via the out-of-prefix id). Per repo convention (pipeline-terminal-truth updated scenario wording to match implemented reality, e.g. PERSIST-03-2), the **main spec** `openspec/specs/media-storage-honesty/spec.md` SH-02-3 was aligned to implemented semantics: *"GIVEN a `media_id` that resolves to no object key for this tenant (unknown id, including keys outside the `{tenant_id}/` prefix) → THEN the response is 404 and no object is deleted."* The requirement text (REQ-SH-02: idempotent for already-missing object + 404 for unknown `media_id`) already matched. The **archived delta spec keeps the original wording verbatim** (audit trail — never modified); this reconciliation note is the record of the alignment. Behaviorally safe: `remove_object` of a missing key is a no-op and the cross-tenant guard is intact.

## Engram Traceability

| Artifact | Obs | Sync |
|----------|-----|------|
| explore | #256 (`obs-4ad83422405ce31d`) | — |
| proposal | #257 (`obs-9773fde0c896f9cd`) | — |
| spec | #258 (`obs-50865639e9e8acb6`) | — |
| design | #259 (`obs-c627548961e30943`) | — |
| tasks | #260 (`obs-61c1f4768b226349`) | — |
| apply-progress | #261 (`obs-097b14780ae5872e`) | merged into verify-report (TDD evidence) |
| fix-delta validator (RISK-001) | #264 (`obs-bb0560c342af4ea2`) | `approve` verdict for d503e89 |
| verify-report | #265 (`obs-048e1613bfa0fb1d`) | merged into this report |
| **archive-report** | saved this phase (`sdd/storage-honesty/archive-report`) | 3 delta syncs merged into `openspec/specs/`; folder → `openspec/changes/archive/2026-08-11-storage-honesty/` |

## Archive Contents

- `archive-report.md` (this file) ✅
- `proposal.md` ✅
- `spec.md` ✅ (delta — flat single-file convention, verbatim, per `2026-08-09-pipeline-production-gaps`)
- `design.md` ✅ (D-1..D-8)
- `tasks.md` ✅ (13/13 tasks complete + RISK-001, historical record — not rewritten)
- `verify-report.md` ✅ (PASS WITH WARNINGS, 19/19 scenarios, no CRITICAL)

No `reviews/` folder for this change (verify-only flow; fix-delta verdict in Engram obs #264).

Active `openspec/changes/` now contains only `archive/` — the change is no longer active.

## Commit / Uncommitted Consistency Notes

- Archive operations made **zero commits**: synced specs + archived change folder left uncommitted, consistent with prior archives (planning artifacts untracked since propose; impl commits already on main up to `d503e89`). The three synced/created main specs and the archived folder are ready to be committed by the orchestrator at the lifecycle gate (suggest `docs(openspec): archive storage-honesty with consolidated delta specs`).
- No production code touched; no frontend files touched; no migration beyond the already-implemented `005_add_products_object_key.sql`.

## Reconciliation Notes

- No stale-checkbox reconciliation needed (`tasks.md` 13/13 `[x]`).
- No destructive merge: only CREATED (media-storage-honesty full spec), ADDED (REQ-SH-04), and MODIFIED (REQ-PERSIST-05 — full requirement block replaced with merged text) applied; all requirements not mentioned in the delta preserved.
- SH-02-3 scenario wording aligned to implemented semantics in the main spec (documented above); archived delta kept verbatim.
- No CRITICAL verification findings; no intentional partial archive; no deviations from the archive contract.
- No `openspec/config.yaml` and no `openspec/README` index exist in this repo — no index/roadmap update required (noted, skipped per convention check, same as prior archives).

## Next Recommended

**orchestrator**: commit the archive artifacts (synced main specs + archived folder, e.g. `docs(openspec): archive storage-honesty with consolidated delta specs`) and deliver the **3 stacked PRs** per the approved plan — PR1 = Slice 1 (core MinIO honesty + media API + compose fix, ~270 lines), PR2 = Slice 2 (renderer signed URL, ~55 lines), PR3 = Slice 3 (migration 005 + DAO + re-sign, ~150 lines) — each →main, in order. Non-blocking follow-ups for future changes (from verify-report): consolidate the 4 divergent Minio fakes into a shared test seam; document `MINIO_PUBLIC_ENDPOINT` signer `secure` inheritance if a public HTTPS host is ever fronted by a non-TLS internal endpoint; consider a shared storage SDK for the duplicated `_derive_secure`/`_host_port` helpers across backend and renderer.
