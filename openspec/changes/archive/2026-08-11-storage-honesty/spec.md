# Storage Honesty — Spec

Delta covering three capabilities: new `media-storage-honesty` (real list/delete/config guards), a MODIFIED requirement (REQ-PERSIST-05) in `pipeline-persistence-writes` (persist `object_key`, re-sign on read), and an ADDED requirement (REQ-SH-04) in `video-scene-render-contract` (renderer returns a real signed URL). Behavior only; implementation is design's job.

## Capability: `media-storage-honesty` (new, add)

### Requirement: REQ-SH-01 — Honest media list

**User Story**: As a user, I want `GET /media` to list my REAL uploaded objects from MinIO — not a fabricated in-memory registry — so what I see is what actually exists.

**Motivo**: `list_tenant_media` reads only `_MEDIA_REGISTRY` and seeds 2 demo items with fabricated non-presigned URLs (RISK-07, READABILITY-002); real uploads vanish on restart.

The system MUST list objects from MinIO under the tenant prefix `{tenant_id}/` and MUST return one entry per real object with a presigned URL. The system MUST NOT read `_MEDIA_REGISTRY` and MUST NOT seed demo items; a tenant without uploads MUST receive an empty list. When `MINIO_PUBLIC_ENDPOINT` is set, presigned URLs MUST be signed against that host (client-reachable override); otherwise the default endpoint host is used.

#### Scenario: SH-01-1 — list returns real objects

- GIVEN a tenant with uploaded objects under `{tenant_id}/` in MinIO
- WHEN `GET /api/v1/tenants/{tenant_id}/media`
- THEN one item per real object is returned with a presigned URL (`X-Amz-Signature=`) and its `object_key`
- AND no registry/demo entries appear

#### Scenario: SH-01-2 — demo seeds gone, empty-state for empty tenants

- GIVEN a tenant with no uploads
- WHEN `GET /media`
- THEN the response is an empty list (no fabricated demo items, gallery empty-state shown)

#### Scenario: SH-01-3 — presign host override honored

- GIVEN `MINIO_PUBLIC_ENDPOINT` set to a browser-reachable host
- WHEN `GET /media`
- THEN every presigned URL uses that host
- AND when unset, URLs use the default endpoint host

### Requirement: REQ-SH-02 — Honest media delete

**User Story**: As a user, I want `DELETE /media/{id}` to actually remove the object from MinIO — idempotently, with 404 only for unknown ids — so a 200 never lies while the object persists.

**Motivo**: `delete_media` only filters `_MEDIA_REGISTRY`; it never calls `remove_object` (RESILIENCE-010) and the demo delete re-seeds on next list. `remove_object` is irreversible, so cross-tenant deletes must be impossible.

The system MUST resolve the `media_id` to an object key, MUST guard `object_key.startswith(f"{tenant_id}/")` before deleting, and MUST call `remove_object`. DELETE MUST be idempotent for an already-missing object (S3 delete 204) and MUST return 404 for an unknown `media_id`. A key outside the tenant prefix MUST NOT be deleted.

#### Scenario: SH-02-1 — delete removes the object

- GIVEN an object under `{tenant_id}/` listed for the tenant
- WHEN `DELETE /api/v1/tenants/{tenant_id}/media/{media_id}`
- THEN `remove_object` is called with the exact guarded key and the response is 200/204
- AND the object no longer appears in a subsequent `GET /media`

#### Scenario: SH-02-2 — missing object is idempotent

- GIVEN the object was already removed (absent from listing)
- WHEN the same `DELETE` is repeated
- THEN the response succeeds without error (idempotent 204-style), no 500

#### Scenario: SH-02-3 — unknown media_id is 404

- GIVEN no object matches `media_id` for this tenant
- WHEN `DELETE /media/{media_id}`
- THEN the response is 404 and no object is deleted

#### Scenario: SH-02-4 — cross-tenant key guarded

- GIVEN a `media_id` resolving to a key NOT starting with `{tenant_id}/`
- WHEN delete runs
- THEN the delete is refused (guard) and `remove_object` is never called for the out-of-prefix key

### Requirement: REQ-SH-03 — Honest config: fail-fast creds + secure derivation

**User Story**: As an operator, I want the storage client to refuse to boot with default/invalid credentials in staging/prod and to derive `secure` from reality — so misconfiguration fails loudly instead of silently.

**Motivo**: Client uses default `minioadmin` creds and unconditional `secure=False` (RISK-02/03); init errors are swallowed (`self.minio_client=None` + warning), silently degrading listing.

The system MUST fail fast at module/startup level when `AGENCY_ENV` is staging/prod and `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` are the `minioadmin` defaults (mirroring `session.py:31-32` / `main.py:107-114`). `secure` MUST be derived: `True` when the endpoint scheme is `https://` or `MINIO_SECURE` is truthy, else `False`. Initialization errors MUST surface (raise or error-log) and MUST NOT be silently swallowed.

#### Scenario: SH-03-1 — default creds fail fast in staging/prod

- GIVEN `AGENCY_ENV=staging` (or prod) with `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` at the `minioadmin` defaults
- WHEN the storage module initializes
- THEN a security error is raised and the process does not boot

#### Scenario: SH-03-2 — secure=True from scheme or env

- GIVEN `MINIO_ENDPOINT=https://...` or `MINIO_SECURE=true`
- WHEN the client initializes
- THEN `secure=True`

#### Scenario: SH-03-3 — plain http dev stays secure=False

- GIVEN `MINIO_ENDPOINT=http://localhost:9000` and no `MINIO_SECURE`
- WHEN the client initializes
- THEN `secure=False`

#### Scenario: SH-03-4 — init errors are not swallowed

- GIVEN MinIO unreachable during initialization
- WHEN the client initializes
- THEN the failure is surfaced (raise/error log), never a silent `minio_client=None` that later degrades listing

## Capability: `video-scene-render-contract` (MODIFIED)

### Requirement: REQ-SH-04 (ADDED) — Renderer returns a real signed URL

**User Story**: As a publisher, I want the renderer's upload response to be a URL I can actually fetch — a signed URL for the private bucket, never a fabricated public root that 403s.

**Motivo**: `upload_to_minio` (`renderer/app.py:329`) fabricates `http://{endpoint}/{bucket}/{key}` for a PRIVATE bucket; the publisher fetching it gets 403 in prod.

The system MUST return a real `presigned_get_object` URL from `upload_to_minio` for the private bucket. The system MUST NOT return the fabricated `http://{endpoint}/{bucket}/{key}` root. All other render behavior (scenes protocol, TTS, b-roll, compose) MUST remain unchanged.

#### Scenario: SH-04-1 — signed URL returned

- GIVEN the renderer uploads the final `.mp4`
- WHEN `upload_to_minio` completes
- THEN the returned URL is a presigned URL containing `X-Amz-Signature=`

#### Scenario: SH-04-2 — no fabricated public root

- GIVEN the returned URL
- WHEN it is inspected
- THEN it is NOT the pattern `http://{endpoint}/{bucket}/{key}` of the private bucket

#### Scenario: SH-04-3 — existing render behavior unchanged

- GIVEN a render request (with or without `scenes[]`)
- WHEN it renders after the change
- THEN the produced video/audio output is unchanged; only the returned URL differs

## Capability: `pipeline-persistence-writes` (MODIFIED)

### Requirement: REQ-PERSIST-05 (MODIFIED) — product data persists `object_key` and re-signs on read

**User Story**: As a user, I want my product image reference to survive — a stable `object_key` persisted, re-signed to a working URL on every read — so the 7-day presigned URL expiry cannot kill the flow (RISK-04, RESILIENCE-008).

**Motivo**: `product_image_url` persisted a 7-day presigned URL that dies; the LLM prompt and downstream consumers receive dead URLs. Migration 005 (additive, nullable `products.object_key`) plus re-sign-on-read keeps every URL real.

The system MUST persist `products.object_key` (not the presigned URL) via migration `005_*.sql` (additive nullable column, fresh volumes via `initdb.d`; documented manual `psql` apply for existing dev DBs). `upsert_product` MUST store `object_key`. Read paths MUST re-sign via `presigned_get_object`, honoring `MINIO_PUBLIC_ENDPOINT`, and the API MUST keep returning a working signed URL. Legacy rows with `object_key` NULL MUST fall back to the stored `product_image_url`. The LLM prompt (`video_prompt_crew`) MUST receive working URL text. The pipeline MUST continue normally when no product is ingested.

(Previously: REQ-PERSIST-05 wired the 7-day presigned `product_image_url` from ingest into graph state and the `products` row; nothing was ever re-signed.)

#### Scenario: PERSIST-05-1 (updated) — product persists object_key

- GIVEN a product-ingest response with an image
- WHEN the product is upserted (`/graph/run` or ingest)
- THEN the `products` row stores `object_key` — not the presigned URL

#### Scenario: PERSIST-05-2 (unchanged) — no product: graceful TEXT_TO_VIDEO

- GIVEN no product ingested
- WHEN the graph runs
- THEN the pipeline completes without error on the text-to-video path

#### Scenario: SH-05-3 — read re-signs a working URL

- GIVEN a `products` row with `object_key`
- WHEN the product is read (API response / downstream consumer)
- THEN the URL is freshly presigned (`X-Amz-Signature=`), honoring `MINIO_PUBLIC_ENDPOINT`

#### Scenario: SH-05-4 — legacy rows fall back to stored URL

- GIVEN a pre-005 row with `object_key` NULL and a stored `product_image_url`
- WHEN it is read
- THEN the stored URL is used as fallback — no break, no fabrication

#### Scenario: SH-05-5 — LLM prompt receives working URL text

- GIVEN `video_prompt_crew` runs with a product image
- WHEN the storyboard/prompt is built
- THEN the prompt contains a working (re-signed) URL text, never the expired one

## Capability flags

| Capability | Flag | Kind |
|------------|------|------|
| `media-storage-honesty` | add | new spec |
| `video-scene-render-contract` | update | REQ-SH-04 added (delta merged at archive) |
| `pipeline-persistence-writes` | update | REQ-PERSIST-05 modified (delta merged at archive) |

## Traceability

| Requirement | Scenarios | Debt closed |
|-------------|-----------|-------------|
| REQ-SH-01 | SH-01-1, SH-01-2, SH-01-3 | RISK-07, READABILITY-002 |
| REQ-SH-02 | SH-02-1, SH-02-2, SH-02-3, SH-02-4 | RESILIENCE-010, RISK-07 |
| REQ-SH-03 | SH-03-1, SH-03-2, SH-03-3, SH-03-4 | RISK-02, RISK-03 |
| REQ-SH-04 | SH-04-1, SH-04-2, SH-04-3 | renderer 403 lie |
| REQ-PERSIST-05 (mod) | PERSIST-05-1, PERSIST-05-2, SH-05-3, SH-05-4, SH-05-5 | RISK-04, RESILIENCE-008 |

## Risks / notes

- **`remove_object` irreversible**: mitigated by strict tenant-prefix guard + listing-based key resolution (REQ-SH-02-4); FakeMinio must record keys in tests.
- **Migration 005 on existing dev DBs**: `initdb.d` is fresh-volume only; additive nullable column + documented manual `psql` apply (REQ-PERSIST-05).
- **Presigned host unreachable from browser**: `MINIO_PUBLIC_ENDPOINT` override for client-facing URLs (REQ-SH-01-3, SH-05-3).
- **Honest list surfaces compose env bug**: backend `MINIO_ENDPOINT=minio:9000` compose fix ships in the same slice (PR #1).
- **Scope**: 3 services + migration → chained PRs per proposal (`size:exception` APPROVED, 400-line budget).
- **Zero-token constraint**: all list/delete/presign paths testable with fakes; no real LLM/network path required.
