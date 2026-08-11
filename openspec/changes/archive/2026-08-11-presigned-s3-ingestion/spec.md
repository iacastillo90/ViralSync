# OpenSpec Spec: Presigned S3 Ingestion

## Requirements & Scenarios

### REQ-PSI-01: Generación de Presigned Upload URL
- **Scenario 1:** Un cliente realiza `POST /{tenant_id}/ingestion/presigned-upload-url` enviando `{ "filename": "foto.png" }`. El backend valida el sufijo del tenant y retorna HTTP 200 con `{ "upload_url": "...", "object_key": "{tenant_id}/products/foto.png", "expires_in": 3600 }`.
- **Scenario 2:** Intentar solicitar presigned URLs para nombres de archivos fuera del prefijo del tenant genera un error HTTP `400 Bad Request`.
