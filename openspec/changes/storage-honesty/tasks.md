# Tasks: Storage Honesty

> Source: spec.md (REQ-SH-01..04 + REQ-PERSIST-05, 19 scenarios) + design.md (D-1..D-8) + code verified at HEAD `0b5d13b`. Strict TDD: RED test → GREEN implementation per task; suite green at the END of every slice (no red window inside a slice). Zero-token only: FakeMinio list/remove/presign, `db_session` SQLite (StaticPool), AsyncClient + ASGITransport — no real network/LLM/docker. Baseline verified at HEAD: `271 passed, 1 skipped` (canonical: `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/ -q`).

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines (total) | ~475 authored (adds+deletes) |
| Slice 1 (core minio, PR #1) | ~270 |
| Slice 2 (renderer, PR #2) | ~55 |
| Slice 3 (migration+DAO, PR #3) | ~150 |
| 400-line budget risk per slice | **Low** (each slice < 400; total ~475 > 400 ⇒ chained) |
| Chained PRs recommended | Yes |
| Suggested split | PR1 = Slice 1 → PR2 = Slice 2 → PR3 = Slice 3 (each →main) |
| Delivery strategy | auto-forecast (chained) |
| Chain strategy | stacked-to-main (cached) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low

> Decision status: `size:exception` already APPROVED (total ~475 > 400); `stacked-to-main` cached. No further user decision required.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| WU-1 | Slice 1: honest client (lazy bucket, real list/delete, fail-fast creds, derived secure, drop `_MEDIA_REGISTRY`+seeds) + GET/DELETE media API + compose `MINIO_ENDPOINT=minio:9000` (REQ-SH-01/02/03) | PR 1 (→main) | `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/unit/test_minio_real.py tests/unit/test_minio_client.py tests/unit/test_api_media.py -q` | N/A — FakeMinio records keys/prefix, ASGITransport; no real MinIO | `git revert` WU-1 commits (minio_client.py, ingestion.py, docker-compose.yml) → registry behavior restored |
| WU-2 | Slice 2: `upload_to_minio` returns `presigned_get_object` honoring `MINIO_PUBLIC_ENDPOINT`; delete fabricated root (REQ-SH-04) | PR 2 (→main) | `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/unit/test_video_renderer_microservice.py -q` | N/A — stub Minio in sys.modules, direct `upload_to_minio` call | Revert renderer/app.py `upload_to_minio` → fabricated dev URL returns |
| WU-3 | Slice 3: migration 005 `products.object_key` + ORM/DAO upsert + state flow + re-sign on read (REQ-PERSIST-05, SH-05-3/4/5) | PR 3 (→main) | `cd agency && AGENCY_ENV=dev ./.venv/bin/python -m pytest tests/unit/test_daos.py tests/unit/test_api_product_ingest.py tests/unit/test_video_prompt_crew.py -q` | N/A — `db_session` SQLite; crew fakes untouched (signature unchanged) | Revert 005+models+daos+state edits → `object_key` NULL, stored-URL fallback (ADD-only nullable, no destructive DDL) |

Dependencies (strict, no red window per slice): WU-1 (none) → WU-2 (none from WU-1; renderer is a separate service) → WU-3 (needs `build_object_key`/`presign_public_url` from WU-1 for key derivation + re-sign).

## Phase 1 — Slice 1: core MinIO honesty (REQ-SH-01/02/03, ~270 lines, PR #1)

- [x] **TSH-001 (RED)** — Title: FakeMinio list/remove + helpers signature rewrite. Files: `agency/tests/unit/test_minio_real.py` (FakeMinio :36-67 + `test_helpers_keep_signature` :110-125). Add `list_objects(bucket, prefix, recursive)` (prefix-filtered, records `(bucket, prefix)`) and `remove_object(bucket, key)` (records keys, idempotent 204). Rewrite `test_helpers_keep_signature`: drop demo-seed assertions (`vid-demo-` :114-115) → empty FakeMinio returns `[]`; `delete_tenant_media_item` True; `save_product_photo_to_minio` still returns `X-Amz-Signature=` URL. RED: current registry+seed behavior fails. Zero-token ✓. Rollback: test-only.
- [x] **TSH-002 (RED)** — Title: lazy bucket rewrite. Files: `agency/tests/unit/test_minio_client.py` (`test_new_bucket_creation_never_applies_public_policy` :34-44). Assert constructor performs NO `make_bucket` (pure config; D-1) — `make_bucket` only via `_ensure_bucket()` after first upload; `set_bucket_policy` never called. RED: ctor currently makes bucket eagerly. Zero-token ✓. Rollback: test-only.
- [x] **TSH-003 (RED)** — Title: media API contract tests. Files: `agency/tests/unit/test_api_media.py` (NEW). AsyncClient + ASGITransport + monkeypatched `get_client()`: `test_list_media_empty_returns_empty_list` (SH-01-2), `test_list_media_returns_real_objects_with_presigned_url` (SH-01-1: item has `object_key` + `X-Amz-Signature=`), `test_delete_media_unknown_id_returns_404` (SH-02-3), `test_delete_media_idempotent_repeat` (SH-02-2), `test_delete_media_out_of_prefix_refused_remove_object_never_called` (SH-02-4: guard, FakeMinio records no remove). RED: registry semantics fail. Zero-token ✓. Rollback: test-only.
- [x] **TSH-004 (GREEN)** — Title: client honesty + config honesty (D-1/D-2). Files: `agency/backend/storage/minio_client.py`. Pure-config ctor (raise RuntimeError if `HAS_MINIO_SDK` false); lazy `_ensure_bucket()` on first upload (private-bucket invariant); module-level cached `get_client()` + `_reset_client()` hook; `list_tenant_media` = `list_objects(prefix=f"{tenant_id}/", recursive=True)` → items `{id: object_key, object_key, filename, type, url, size_bytes, created_at}` presigned; `delete_media` = `startswith(f"{tenant_id}/")` guard + `remove_object` idempotent; DELETE `_MEDIA_REGISTRY` + demo seeds; helpers `build_object_key(tenant_id, filename)` + `presign_public_url(object_key)` honoring `MINIO_PUBLIC_ENDPOINT` (signer client bound to override host); module-level helpers keep signature via `get_client()`. Fail-fast: `AGENCY_ENV` staging/prod + `minioadmin` defaults → `raise ValueError` (mirror `session.py:31-32`/`main.py:107-114`); `secure = "https://" in endpoint or MINIO_SECURE truthy`; init/op errors raise, never silent `minio_client=None` (SH-03-4). Acceptance: SH-01-1/2/3, SH-02-1/2/4, SH-03-1/2/3/4. Rollback: WU-1 boundary. Est: ~120.
- [x] **TSH-005 (GREEN)** — Title: media API semantics + compose fix (D-3/D-6). Files: `agency/backend/routers/ingestion.py` (`list_media` :206-210, `delete_media_item` :213-219 → `{media_id:path}` converter; `media_id` == object_key; in-prefix → `remove_object` → 200 idempotent; else 404), `agency/docker-compose.yml` (backend env :98-100 += `MINIO_ENDPOINT=minio:9000`). Acceptance: SH-01-1/2, SH-02-1/2/3/4. Rollback: WU-1 boundary. Est: ~32.
- [x] **TSH-006 (REFACTOR)** — Title: slice-1 sweep. Verify full suite green; grep for `_MEDIA_REGISTRY`/`vid-demo`/seed leftovers; `.env.example` documents `MINIO_PUBLIC_ENDPOINT`. Rollback: WU-1 boundary. Est: ~5.

## Phase 2 — Slice 2: renderer signed URL (REQ-SH-04, ~55 lines, PR #2)

- [x] **TSH-007 (RED)** — Title: renderer signed-URL tests. Files: `agency/tests/unit/test_video_renderer_microservice.py` (extend `_StubMinio` :34-40 with `bucket_exists`/`make_bucket`/`fput_object`/`presigned_get_object`). `test_upload_to_minio_returns_signed_url` (SH-04-1: URL contains `X-Amz-Signature=`), `test_upload_to_minio_never_fabricates_public_root` (SH-04-2: NOT `http://{endpoint}/{bucket}/{key}`), `test_upload_to_minio_secure_derivation_from_scheme` (SH-03-2: https scheme → secure=True). RED: app.py:329 fabricates root. Zero-token ✓. Rollback: test-only.
- [x] **TSH-008 (GREEN)** — Title: renderer returns presigned URL (D-4). Files: `agency/microservices/renderer/app.py` (`upload_to_minio` :313-331): return `minio_client.presigned_get_object(MINIO_BUCKET, object_name)` honoring `MINIO_PUBLIC_ENDPOINT` via signer client; DELETE fabricated `public_url = f"http://{MINIO_ENDPOINT}..."` (:329); `secure` derived from raw scheme / `MINIO_SECURE` (detect scheme before host strip :36); scenes/TTS/b-roll/compose untouched (SH-04-3). Acceptance: SH-04-1/2/3. Rollback: WU-2 boundary. Est: ~20.

## Phase 3 — Slice 3: migration 005 + DAO + re-sign (REQ-PERSIST-05, ~150 lines, PR #3)

- [x] **TSH-009 (RED)** — Title: ORM/DDL parity + DAO object_key tests. Files: `agency/tests/unit/test_daos.py` (`PRODUCT_004_COLUMNS` :48 += `"object_key"`, rewrite `test_product_columns_match_migration_004_exact` :104-109; new `test_upsert_product_persists_object_key` — PERSIST-05-1: row stores `object_key`, not the URL). RED: ORM lacks column. Zero-token ✓ (`db_session`). Rollback: test-only.
- [x] **TSH-010 (RED)** — Title: ingest + graph object_key flow tests. Files: `agency/tests/unit/test_api_product_ingest.py` (extend no-file test :52-77; new with-file test: response carries fresh signed URL AND row `object_key` persisted — PERSIST-05-1/SH-05-3), `agency/tests/unit/test_video_prompt_crew.py` (graph path: `GraphRunRequest(product_object_key=...)` → state → `upsert_product` persists key; re-sign on read SH-05-3, legacy NULL fallback SH-05-4 — `test_*` asserting stored URL used when key absent; crew signature unchanged SH-05-5). RED. Zero-token ✓. Rollback: test-only.
- [x] **TSH-011 (GREEN)** — Title: migration 005 + ORM + DAO + state flow (D-5). Files: `agency/migrations/005_add_products_object_key.sql` (NEW: `ALTER TABLE products ADD COLUMN IF NOT EXISTS object_key TEXT;` additive nullable); `agency/backend/db/models.py` (`Product.object_key` :128-140); `agency/backend/db/daos.py` (`upsert_product` :199-234 writes `object_key`, None-safe); `agency/backend/routers/ingestion.py` (ingest derives key via `build_object_key` and passes to upsert); `agency/backend/routers/graph_execution.py` (`GraphRunRequest.product_object_key: Optional[str]` :116-131 → state :281-283); `agency/agents/nodes/ideation.py` (:55-64 persists `object_key` in upsert payload). Acceptance: PERSIST-05-1, PERSIST-05-2 (no-product path unaffected). Rollback: WU-3 boundary (ADD-only nullable). Est: ~45.
- [x] **TSH-012 (GREEN)** — Title: re-sign on read (D-5 seam). Files: `agency/agents/nodes/video_edit.py` (:25, :30-31): `product_object_key` in state → `presign_public_url(key)`; else fallback `product_image_url` (SH-05-4); pass re-signed URL to crew — signature unchanged, `video_prompt_crew.py` untouched (SH-05-5); ingest/SSE response keeps fresh signed URL (SH-05-3). Acceptance: SH-05-3/4/5. Rollback: WU-3 boundary. Est: ~15.
- [x] **TSH-013 (REFACTOR)** — Title: slice-3 sweep + docs. Verify full suite green; document manual apply for existing dev DBs — `psql "$DATABASE_URL" -c "ALTER TABLE products ADD COLUMN IF NOT EXISTS object_key TEXT;"` (migration note). Rollback: WU-3 boundary. Est: ~5.

## Dependency order & zero-token constraint

Slices land strictly 1 → 2 → 3 (stacked-to-main): WU-1 (none) → WU-2 (independent service) → WU-3 (needs `build_object_key`/`presign_public_url` from WU-1). Every slice ends with the full suite green (baseline at HEAD `0b5d13b`: `271 passed, 1 skipped`). Zero-token: FakeMinio records list/remove/presign keys; `db_session` SQLite; ASGITransport; renderer stub Minio in `sys.modules`; crew fakes untouched (SH-05-5). Design Threat Matrix: N/A (no routing/shell/subprocess/VCS boundary).
