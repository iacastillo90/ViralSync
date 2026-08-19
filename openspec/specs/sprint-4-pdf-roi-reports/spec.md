# sprint-4-pdf-roi-reports Specification

## Purpose

Sprint 4: Executive PDF ROI & 72h RUM Metrics Report Generator service and REST API endpoint.

## Requirements

### Requirement: REQ-REP-01 — Executive PDF Report Generation
The system MUST generate a structured PDF report metadata object summarizing tenant performance, views, RUM 72h classifications (`ROJO`/`AMARILLO`/`VERDE`), and ROI metrics.

#### Scenario: REP-01-1 — Report metadata generated
- GIVEN a tenant ID and consolidated 72h metrics
- WHEN `generate_tenant_roi_pdf_report(tenant_id, summary)` is called
- THEN a PDF report metadata object with `content_type: application/pdf` and summary metrics is returned.

#### Scenario: REP-01-2 — Binary PDF Stream Generation
- GIVEN a tenant ID and consolidated metrics
- WHEN `build_tenant_pdf_bytes(tenant_id, summary)` is called
- THEN a valid binary PDF stream starting with `%PDF-1.4` is produced.

