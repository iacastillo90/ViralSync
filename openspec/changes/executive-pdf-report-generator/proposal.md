# Proposal — Generador de Reportes Ejecutivos PDF de ROI

## Summary
Implementar la generación automática de Reportes Ejecutivos en PDF de marca blanca para clientes de la agencia ViralSync 360°. El servicio agregará métricas de rendimiento (alcance, conversiones, leads captados, clasificación RUM 72h y ROI estimado) y exportará un documento PDF estructurado en 1-click para el cliente.

## Motivation
Los clientes de agencias de marketing requieren reportes periódicos descargables para justificar la inversión en contenido corto (Reels/TikToks). Una exportación ejecutiva en PDF de marca blanca aumenta el valor percibido del servicio y facilita la rendición de cuentas.

## Scope
- Registro de especificaciones en `openspec/changes/executive-pdf-report-generator/`.
- Motor de renderizado PDF con `reportlab` en `backend/reports/pdf_generator.py`.
- Endpoint REST `GET /api/v1/tenants/{tenant_id}/reports/monthly-pdf` con soporte de descarga binaria `application/pdf`.
- Componente UI Frontend `ExecutiveReportButton.jsx` con descarga en 1-click.
- Pruebas unitarias completas en `tests/unit/test_sprint4_pdf_reports.py`.
