# Proposal: Storage Honesty

## Intent

The storage layer lies: `list_tenant_media` reads an in-memory registry and seeds fabricated demo URLs (RISK-07, READABILITY-002, RESILIENCE-010), `delete_media` never calls `remove_object` (leak + false success), the client boots with default `minioadmin` creds and unconditional `secure=False` (RISK-02/03), the renderer fabricates a public `http://{endpoint}/{bucket}/{key}` URL for a PRIVATE bucket (403 for the publisher), `products.product_image_url` persists a 7-day presigned URL that dies (RISK-04, RESILIENCE-008), and the backend container points at `localhost:9000` instead of `minio:9000`. Goal: every URL is real, every delete deletes, every credential is guarded.

## Scope

### In Scope (LOCKED decisions)

- **A. Core storage honesty** — `list_objects(prefix={tenant_id}/)` + presign per object; drop demo seeds from `_MEDIA_REGISTRY`; `remove_object` delete with strict tenant-prefix guard, idempotent, 404 for unknown `media_id`; fail-fast creds guard (staging/prod reject `minioadmin`, mirroring `session.py:31-32`/`main.py:107-114`); `secure` derived from endpoint scheme (`https://` → True) or `MINIO_SECURE`; docker-compose backend `MINIO_ENDPOINT=minio:9000` fix.
- **B. Renderer URL honesty** — `renderer/app.py:329` stops fabricating public URLs; returns a real/signed URL.
- **C. product_image_url redesign** — persist `object_key` (not the 7-day presigned URL), re-sign on read; migration 005 + DAO + LLM-prompt changes.

### Out of Scope

- Object lifecycle/retention beyond delete; bucket migration/rename.
- Frontend changes beyond the existing empty-state gallery.
- Upload size/type limits (RISK-11); public bucket policy (RISK-01, already fixed); publisher internals (it simply starts receiving real URLs).

## Capabilities

### New Capabilities

- `media-storage-honesty`: real list/delete of tenant media over MinIO — tenant-prefix isolation, presigned listing, idempotent delete with 404 semantics, no demo seeds, credential/transport guards.

### Modified Capabilities

- `pipeline-persistence-writes`: REQ-PERSIST-05 changes — persist `products.object_key`, re-sign on read; migration 005.
- `video-scene-render-contract`: renderer upload returns a real signed URL, never a fabricated root.

## Approach

- **A**: Rewrite `list_tenant_media` → `list_objects(prefix=tenant_id + "/")`, presign each; rewrite `delete_media` → resolve object_key via listing, guard `object_key.startswith(f"{tenant_id}/")`, `remove_object`, 404 when absent; delete `_MEDIA_REGISTRY` + seeds; module-level fail-fast + `secure` derivation; compose fix.
- **B**: `upload_to_minio` returns `presigned_get_object(...)`; same `secure` derivation.
- **C**: migration 005 adds `products.object_key`; `upsert_product` writes key; read paths re-sign; `ideation.py`/`video_prompt_crew.py`/`graph_execution.py` carry the key; API keeps returning a signed URL.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agency/backend/storage/minio_client.py` | Modified | Core rewrite: honest list/delete, guards, secure |
| `agency/backend/routers/ingestion.py` | Modified | GET /media, DELETE /media/{id} semantics (404/idempotent) |
| `agency/microservices/renderer/app.py:313-331` | Modified | Signed URL instead of fabricated root |
| `agency/migrations/005_*.sql` | New | `products.object_key` (additive) |
| `agency/backend/db/daos.py:199-234` | Modified | Upsert/re-sign object_key |
| `agency/agents/nodes/ideation.py:55-64`, `crews/video_prompt_crew.py:65,101-163`, `routers/graph_execution.py:127-131` | Modified | Object-key flow through state/prompts |
| `agency/docker-compose.yml:98-100` + `.env` | Modified | Backend `MINIO_ENDPOINT=minio:9000`; endpoint normalization |
| `agency/tests/unit/test_minio_real.py` (:110-125 RED), `test_minio_client.py`, `test_api_product_ingest.py`, `test_video_renderer_microservice.py` | Modified | New list/delete/secure contracts |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `remove_object` irreversible — wrong key deletes other tenant's object | Med | Strict prefix guard + listing-based lookup + FakeMinio records keys |
| Migration 005: `initdb.d` only runs on fresh PG volumes; existing dev DBs miss it | Med | Additive nullable column; document manual `psql` apply in tasks/verify |
| Presigned host unreachable from browser (`minio:9000`) | Med | `MINIO_PUBLIC_ENDPOINT` override for client-facing URLs |
| Honest list surfaces env bug as failures | Low | Compose fix ships in same slice |
| Scope creep (3 microservices + migration) | Med | Chained PRs below |

## Rollback Plan

Per-slice revert in reverse order. 005 is ADD-only nullable — no destructive DDL. Old code still works: re-sign falls back to the stored URL when `object_key` is null.

## Dependencies

- MinIO SDK (present); optional `MINIO_SECURE` / `MINIO_PUBLIC_ENDPOINT` env vars. None external.

## Success Criteria

- [ ] `GET /media` lists real objects (tenant prefix), presigned URLs, zero demo seeds
- [ ] `DELETE /media/{id}` removes the object (FakeMinio records `remove_object`), 404 on unknown id, idempotent
- [ ] staging/prod boot fails on default `minioadmin` creds; `secure` follows scheme/`MINIO_SECURE`
- [ ] Renderer upload returns a signed URL
- [ ] `products.object_key` persisted (005), URLs re-signed on read; baseline 271 passed / 1 skipped stays green

## Open Questions

1. Client-reachable presign host: sign with container endpoint (`minio:9000`, works for publisher/renderer) vs `MINIO_PUBLIC_ENDPOINT` (works for browser gallery)? Recommend the env override, default `localhost:9000` in dev.
2. Migration runner: accept manual `psql` apply for existing dev DBs, or add a run-migrations step? Recommend documented manual apply.

## First Slice + Chained PRs (stacked-to-main, 400-line budget)

- **PR #1** — Slice A (minio_client honesty + ingestion endpoints + guards + compose fix + tests). Core, self-contained.
- **PR #2** — Slice B (renderer signed URL + renderer tests). Targets PR #1 branch.
- **PR #3** — Slice C (migration 005 + DAO + state/prompt object_key + tests). Targets PR #2 branch.

Forecast exceeds 400 lines → chained PRs expected (`size:exception` APPROVED).
