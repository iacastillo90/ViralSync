# media-storage-honesty Specification

## Purpose

Honest tenant media storage over MinIO: `GET /media` lists the tenant's REAL uploaded objects under the `{tenant_id}/` prefix with presigned URLs (no fabricated in-memory registry, no demo seeds, empty list for tenants without uploads), `DELETE /media/{id}` actually removes the object with a strict tenant-prefix guard (idempotent, 404 only for unknown or out-of-prefix ids), and the storage client fails fast on default/invalid credentials in staging/prod while deriving `secure` from the endpoint scheme. Every URL is real, every delete deletes, every credential is guarded.

## Requirements

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

- GIVEN a `media_id` that resolves to no object key for this tenant (unknown id, including keys outside the `{tenant_id}/` prefix)
- WHEN `DELETE /api/v1/tenants/{tenant_id}/media/{media_id}`
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
