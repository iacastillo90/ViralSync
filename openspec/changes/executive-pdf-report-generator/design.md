# Technical Design — Generador de Reportes Ejecutivos PDF de ROI

## Architecture

```
[ Frontend: ExecutiveReportButton.jsx ]
                   │
                   ▼ (GET /api/v1/tenants/{id}/reports/monthly-pdf?download=true)
[ FastAPI Router: backend/routers/metrics.py ]
                   │
                   ▼
[ Service: backend/reports/pdf_generator.py (ReportLab) ]
                   │
                   ▼
[ Binary Stream: application/pdf (%PDF-1.4) ]
```

## Data Flow
1. El usuario hace clic en **"📄 Descargar Reporte PDF"** en el Dashboard.
2. El frontend realiza un `fetch` con `responseType: blob`.
3. El router `metrics.py` consulta las métricas de 72h y de la base de datos (videos, leads, scores RUM).
4. `pdf_generator.py` construye el documento PDF usando `reportlab.platypus` (`SimpleDocTemplate`, `Paragraph`, `Table`, `Spacer`, `colors`).
5. Se retorna el blob `.pdf` y el navegador dispara la descarga directa.
