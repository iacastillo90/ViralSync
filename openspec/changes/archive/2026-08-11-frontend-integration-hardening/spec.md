# OpenSpec Spec: Hardening de Integración Frontend UI

## Requirements & Scenarios

### REQ-FIH-01: Integración Presigned Upload en ProductIngest
- **Scenario 1:** Al subir un producto, el componente solicita `POST /ingestion/presigned-upload-url` y realiza un `fetch(upload_url, { method: "PUT", body: file })` directo a MinIO/S3.

### REQ-FIH-02: Manejo de Rate Limit 429 en Frontend Services
- **Scenario 1:** Cuando una llamada a la API devuelve HTTP 429, el cliente extrae la cabecera `Retry-After` e informa al usuario del tiempo de espera.
