# Design: Storage Honesty

## Technical Approach

Three stacked PRs (chained stacked-to-main, `size:exception` APPROVED, 400-line budget). **PR #1** core honesty: rewrite `backend/storage/minio_client.py` (real list/delete, fail-fast creds, derived `secure`, drop `_MEDIA_REGISTRY` + demo seeds), `routers/ingestion.py` endpoint semantics, docker-compose backend env fix. **PR #2** renderer signed URL (`microservices/renderer/app.py:329`). **PR #3** migration 005 `products.object_key` + DAO + re-sign-on-read through state. Everything zero-token via FakeMinio; no real network/LLM in tests.

## Architecture Decisions

### D-1 Client honesty (PR #1)
**Choice**: Constructor becomes pure config (no network; raises if `HAS_MINIO_SDK` false). Bucket creation moves to lazy `_ensure_bucket()` on first upload (private bucket invariant preserved). Single client lifecycle via module-level cached singleton `get_client()` + `_reset_client()` test hook. `list_tenant_media` = `list_objects(prefix=f"{tenant_id}/", recursive=True)` mapped to items `{id: object_key, object_key, filename, type, url, size_bytes, created_at}`; `delete_media` = guard + `remove_object`. `_MEDIA_REGISTRY`, seeds, and demo seeding deleted.
**Alternatives**: registry + real ops (two sources of truth); eager bucket_exists per request (network churn).
**Rationale**: MinIO is the single source of truth (SH-01-1/2); S3 delete is idempotent 204 (SH-02-2). Helper signatures preserved (`save_product_photo_to_minio→str`, `get_tenant_media_list→list`, `delete_tenant_media_item→bool`); new `build_object_key(tenant_id, filename)` and `presign_public_url(key)` shared functions (no key/URL drift).
**Presign host**: `MINIO_PUBLIC_ENDPOINT` set → sign with a signer client bound to that host (native signing, no string surgery), else default client (SH-01-3, SH-05-3).

### D-2 Config honesty (PR #1)
**Choice**: Module-level fail-fast mirroring `session.py:31-32`/`main.py:107-114`: staging/prod + `minioadmin` defaults → `raise ValueError` (SH-03-1). `secure = "https://" in endpoint or MINIO_SECURE truthy` (SH-03-2/3). Init/op errors raise `RuntimeError` with clear message — never silent `minio_client=None` (SH-03-4).
**Alternatives**: current swallow+warn; unconditional `secure=False`.
**Rationale**: mirrors two existing guards; dev http stays `secure=False` (zero runtime risk).

### D-3 API semantics (PR #1)
**Choice**: `GET /media` → 200 always, empty list when no objects (SH-01-2). `DELETE /media/{media_id:path}` (`:path` converter for slash keys; `media_id` == object_key): id starts with `{tenant_id}/` → `remove_object` → 200 idempotent; else 404 (SH-02-3/4). Tenant scoping unchanged (`main.py:91` `_TENANT_GUARD` on `ingestion_router`).
**Rationale**: key-as-id needs no registry mapping; repeat delete succeeds (S3 204), malformed/foreign id → 404.

### D-4 Renderer URL (PR #2)
**Choice**: `upload_to_minio` returns `minio_client.presigned_get_object(MINIO_BUCKET, object_name)`, honoring `MINIO_PUBLIC_ENDPOINT` via signer client; fabricated root (app.py:329) deleted; `secure` derived from raw endpoint scheme / `MINIO_SECURE`.
**Alternatives**: import backend client into renderer (cross-service coupling).
**Rationale**: renderer is a separate microservice — same pattern, own client, minimal blast radius (SH-04-1/2); scenes/TTS/b-roll/compose untouched (SH-04-3).

### D-5 product_image_url (PR #3)
**Choice**: Migration `005_add_products_object_key.sql`: `ALTER TABLE products ADD COLUMN IF NOT EXISTS object_key TEXT;` (additive nullable). ORM column + `upsert_product` writes `object_key` (None-safe). Ingest path derives key via `build_object_key`; graph path adds optional `GraphRunRequest.product_object_key` → state → `ideation.py` persists it.
**Re-sign seam**: runtime never reads `products` (write-only; URL travels in state), so re-sign happens at consumption: `video_edit.py` re-signs `presign_public_url(key)` when `product_object_key` in state, else falls back to stored URL (SH-05-4); crew signature unchanged → test fakes untouched (SH-05-5). Ingest response/SSE keep returning the fresh signed URL (SH-05-3). PERSIST-05-2 unaffected.
**Alternatives**: keep 7-day URL (RISK-04); recompute key from filename (drift).
**Rationale**: key is stable truth; every read gets a fresh URL.

### D-6 Compose env (PR #1)
**Choice**: backend service env adds `MINIO_ENDPOINT=minio:9000` (`docker-compose.yml:92-97`); renderer already correct (`:150`). `MINIO_PUBLIC_ENDPOINT` documented in `.env.example` for browser-reachable gallery.
**Rationale**: honest list surfaces the localhost self-reference bug; fix ships in the same slice (spec risk note).

### D-7 Test seams (zero-token)
FakeMinio (`test_minio_real.py`): add `list_objects(bucket, prefix, recursive)` (prefix-filtered, records calls) and `remove_object(bucket, key)` (records keys, idempotent); `presigned_get_object` keeps `X-Amz-Signature=`. **Existing RED at PR #1**: `test_minio_real.py::test_helpers_keep_signature` (demo-seed assertions), `test_minio_client.py::test_new_bucket_creation_never_applies_public_policy` (make_bucket now lazy). **RED at PR #3**: `test_daos.py::test_product_columns_match_migration_004_exact` (+`object_key`). New: `tests/unit/test_api_media.py` (GET empty/real+presigned, DELETE 404/idempotent/cross-tenant guard with `remove_object` never called for out-of-prefix), renderer `test_upload_to_minio_returns_signed_url` + secure derivation, DAO `object_key` persist test, ingest-with-file `object_key` test. All other existing tests stay green; baseline 271 passed / 1 skipped preserved.

### D-8 Rollback + work units
| PR | Content | Forecast |
|----|---------|----------|
| #1 | client rewrite ~120, ingestion ~30, compose 2, tests ~120 | ~270 |
| #2 | renderer app ~20, tests ~35 | ~55 |
| #3 | 005+models+dao+state ~45, tests ~105 | ~150 |

Total ~475 > 400 → chained PRs required (`size:exception` APPROVED). Rollback per-slice reverse (3→2→1): PR #3 revert → `object_key` NULL → stored-URL fallback; PR #2 revert → fabricated dev URL; PR #1 revert → registry behavior. 005 is ADD-only nullable — no destructive DDL, deploy-safe.

## Data Flow

    ingest ──upload──▶ presigned URL + object_key ──▶ products{product_image_url, object_key}
    GET /media ──▶ list_objects(prefix={tenant}/) ──▶ presign each ──▶ JSON items
    video_edit ──▶ object_key? presign_public_url(key) : stored URL ──▶ crew prompt text

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `agency/backend/storage/minio_client.py` | Modify | Honest list/delete, lazy bucket, secure, fail-fast; drop registry/seeds; `get_client()`, `build_object_key`, `presign_public_url` |
| `agency/backend/routers/ingestion.py` | Modify | DELETE `:path` semantics; persist `object_key` on ingest |
| `agency/docker-compose.yml` | Modify | Backend `MINIO_ENDPOINT=minio:9000` |
| `agency/tests/unit/test_minio_real.py`, `test_minio_client.py` | Modify | RED rewrites + FakeMinio list/remove |
| `agency/tests/unit/test_api_media.py` | Create | API contract tests (PR #1) |
| `agency/microservices/renderer/app.py` | Modify | Signed URL (PR #2) |
| `agency/tests/unit/test_video_renderer_microservice.py` | Modify | Renderer URL tests (PR #2) |
| `agency/migrations/005_add_products_object_key.sql` | Create | Additive nullable column (PR #3) |
| `agency/backend/db/models.py`, `db/daos.py` | Modify | `object_key` column + upsert (PR #3) |
| `agency/backend/routers/graph_execution.py`, `agents/nodes/ideation.py`, `agents/nodes/video_edit.py` | Modify | object_key state flow + re-sign (PR #3) |
| `agency/tests/unit/test_daos.py`, `test_api_product_ingest.py` | Modify | object_key tests (PR #3) |

## Interfaces / Contracts

```python
# backend/storage/minio_client.py (public surface)
get_client() -> MinIOStorageClient            # cached singleton; raises on SDK/creds failure
build_object_key(tenant_id: str, filename: str) -> str
presign_public_url(object_key: str) -> str    # honors MINIO_PUBLIC_ENDPOINT
# routes
GET    /api/v1/tenants/{tenant_id}/media                -> 200 [{id, object_key, filename, type, url, size_bytes, created_at}]
DELETE /api/v1/tenants/{tenant_id}/media/{media_id:path} -> 200 | 404
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | list/delete/secure/fail-fast/presign-host | FakeMinio records keys+prefix; rewrite 2 RED tests |
| Integration | GET/DELETE endpoints | `test_api_media.py`, AsyncClient + ASGITransport, monkeypatched client |
| Unit | renderer signed URL | Direct `upload_to_minio` with stub Minio |
| Integration | DAO + migration 005 | `db_session` SQLite; parity test + object_key persist |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. Only an in-app FastAPI path-converter change (`{media_id}` → `{media_id:path}`), not infra routing.

## Migration / Rollout

Fresh PG volumes auto-run 005 via `initdb.d` (compose mounts `./migrations`). Existing dev DBs: documented manual apply — `psql "$DATABASE_URL" -c "ALTER TABLE products ADD COLUMN IF NOT EXISTS object_key TEXT;"`. Additive nullable; old code path (NULL → stored URL) keeps working.

## Open Questions

None blocking. `MINIO_PUBLIC_ENDPOINT` deliberately unset by default (sign with container endpoint); set in `.env` for browser-accessible gallery — documented, not code.
