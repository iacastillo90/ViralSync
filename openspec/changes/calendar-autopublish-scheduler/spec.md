# Specification — Auto-Publicación Programada desde el Calendario

## Requirements
### Requirement: REQ-CAL-01 — Scheduled Post Creation and Retrieval
El sistema DEBE permitir agendar publicaciones de Reels aprobados asociando fecha, hora, plataforma y pie de foto.

#### Scenario: CAL-01-1 — Post agendado exitosamente
- GIVEN un tenant ID y un video_id aprobado
- WHEN se invoca `POST /api/v1/tenants/{tenant_id}/calendar/schedule`
- THEN la publicación queda en estado `scheduled` y se retorna su ID.
