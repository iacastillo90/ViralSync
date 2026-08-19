# Specification — Kanban CRM Inbound Leads
## Requirements
- `PATCH /api/v1/tenants/{tenant_id}/leads/{lead_id}/stage` DEBE actualizar la etapa del lead (`nuevo`, `contactado`, `cualificado`, `cerrado`).
- `POST /api/v1/tenants/{tenant_id}/leads/{lead_id}/reply-dm` DEBE enviar o simular la respuesta por mensaje directo.
