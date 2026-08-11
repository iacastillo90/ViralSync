# OpenSpec Proposal: Hardening de Integración Frontend UI

- **Change ID:** `frontend-integration-hardening`
- **Scope:** Actualización de componentes React/Next.js (`ProductIngest.jsx`, `PublishApprovalView.jsx`) para consumir el endpoint `/ingestion/presigned-upload-url`, manejar correctamente rechazos `term_rejected` y estados HTTP 429.

## Problem Statement
Las vistas del frontend deben aprovechar los nuevos contratos Enterprise implementados en el backend: presigned upload URLs de S3/MinIO, manejo de cuota excedida (429 Rate Limiting) y consumo resiliente de SSE sin bloqueos infinitos de la UI.

## Proposed Solution
1. **Presigned Upload Support (`ProductIngest.jsx`):**
   - Solicitar `/presigned-upload-url` e invocar el PUT directo al S3/MinIO antes de confirmar metadata.
2. **Rejection & Error Handling (`PublishApprovalView.jsx`):**
   - Manejar estados `term_rejected` y respuestas 404/429 mostrando retroalimentación visual al usuario.
