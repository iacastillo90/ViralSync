# dm-lead-crm Specification

## Purpose

S1 slice of the `5-value-leaps` change (PR #1): persist Instagram webhook leads asynchronously with tenant resolution, compute a qualification score (keyword + intent), wire the DM classification graph into the persisted lead, enforce webhook idempotency, and keep the DM send gated. S1 only persists, scores, and wires — it does NOT send DMs.

Synced from the S1 delta spec (`openspec/changes/5-value-leaps/spec.md`, section "S1 — DM Leads CRM (P3)") at archive time — 2026-08-15. Scenario test levels: unit / integration.

## Requirements

### Requirement: REQ-DM-LEAD-01 — Webhook persists Lead with tenant resolution
The system MUST persist an Instagram webhook lead as a `Lead` row (username, message, platform=instagram, status) asynchronously, resolving the tenant from the account→tenant mapping instead of the default tenant.
**Test**: integration
#### Scenario: IG comment with AUDIO keyword creates qualified lead
- **Given** a verified Instagram webhook payload containing a comment with the keyword `AUDIO` for an account mapped to a tenant
- **When** the webhook is processed by the worker
- **Then** a `Lead` is inserted with the resolved tenant, `platform=instagram`, `status=Calificado` and `qualification_score>=60`
#### Scenario: Tenant resolved non-default
- **Given** a webhook payload for an account mapped to tenant `tenant_b`
- **When** the lead is persisted
- **Then** the lead's `tenant_id` equals `tenant_b`, not the default

### Requirement: REQ-DM-LEAD-02 — Qualification schema migration
The system MUST add an integer `qualification_score` column to `leads` and a database index on `leads.status` via migration.
**Test**: unit
#### Scenario: Migration applies cleanly
- **Given** the pre-migration schema without `leads.qualification_score`
- **When** the migration runs
- **Then** `leads.qualification_score` (integer) exists and an index on `status` is created

### Requirement: REQ-DM-LEAD-03 — Keyword + intent scoring
The system MUST compute a `qualification_score` (0–100) from message keywords and classified intent (`purchase_intent`/`objection`/`question`/`spam`) and set status `Nuevo`/`Contactado`/`Calificado` accordingly.
**Test**: unit
#### Scenario: High-intent lead qualified
- **Given** a message classified `purchase_intent` with pricing keywords
- **When** scoring runs
- **Then** the lead is `Calificado` with `qualification_score>=60`
#### Scenario: Spam scored low
- **Given** a message classified `spam` with no qualifying keywords
- **When** scoring runs
- **Then** the lead is `Nuevo` with `qualification_score<30`

### Requirement: REQ-DM-LEAD-04 — dm_graph wiring with persisted classification
The system MUST execute the dm_graph classification for persisted leads and store the classification output in `leads.conversacion_history`.
**Test**: integration
#### Scenario: Classification available after wiring
- **Given** a persisted lead awaiting classification
- **When** the dm_graph runs against it
- **Then** the intent classification is written into `conversacion_history` of that lead

### Requirement: REQ-DM-LEAD-05 — Webhook idempotency
The system MUST NOT insert a duplicate `Lead` when the same (user, message) combination is received more than once, keyed by a deterministic content hash.
**Test**: unit + integration
#### Scenario: Repeated webhook does not duplicate
- **Given** an existing lead created from user+message `M`
- **When** a webhook with the same user+message `M` arrives again
- **Then** no new lead row is inserted and the original lead is returned

### Requirement: REQ-DM-LEAD-06 — DM send remains gated
The system MUST NOT change `node_send_dm_reply` behavior and MUST NOT simulate a DM send; S1 only persists, scores, and wires.
**Test**: unit
#### Scenario: No send side-effects
- **Given** a lead that completed S1 processing
- **When** the send node is invoked
- **Then** no Graph API messaging call is made and no simulated `pending_manual` state is produced