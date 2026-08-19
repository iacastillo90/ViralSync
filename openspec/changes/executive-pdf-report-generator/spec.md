# Specification — Generador de Reportes Ejecutivos PDF de ROI

## Requirements

### Requirement: REQ-REP-01 — Executive PDF Binary Report Generation
El sistema DEBE generar un reporte PDF binario (`application/pdf`) de marca blanca con las métricas consolidadas del tenant.

#### Scenario: REP-01-1 — Real Binary PDF Stream
- GIVEN un tenant ID válido y métricas de rendimiento 72h acumuladas
- WHEN se invoca `build_tenant_pdf_bytes(tenant_id, metrics_summary)`
- THEN se retorna un flujo de bytes binarios que inicia con la firma `%PDF-1.4` y contiene las secciones de KPIs, clasificación RUM y recomendaciones.

#### Scenario: REP-01-2 — Endpoint REST Download
- GIVEN una petición `GET /api/v1/tenants/{tenant_id}/reports/monthly-pdf?download=true`
- WHEN el cliente solicita el reporte ejecutivo
- THEN la API responde con estado HTTP 200, `Content-Type: application/pdf` y encabezado `Content-Disposition: attachment; filename=Reporte_Ejecutivo_{tenant_id}.pdf`.
