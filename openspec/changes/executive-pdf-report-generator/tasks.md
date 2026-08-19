# Tasks — Generador de Reportes Ejecutivos PDF de ROI

- [x] Crear paquete de especificaciones en `openspec/changes/executive-pdf-report-generator/`
- [ ] Instalar `reportlab` e implementar `build_tenant_pdf_bytes()` en `backend/reports/pdf_generator.py`
- [ ] Actualizar endpoint `GET /api/v1/tenants/{tenant_id}/reports/monthly-pdf` en `backend/routers/metrics.py`
- [ ] Crear componente frontend `ExecutiveReportButton.jsx` e integrarlo en `DashboardView.jsx`
- [ ] Escribir y verificar pruebas unitarias en `tests/unit/test_sprint4_pdf_reports.py`
- [ ] Crear informe de verificación `verify-report.md`
