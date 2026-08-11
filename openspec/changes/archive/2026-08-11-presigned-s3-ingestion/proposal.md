# OpenSpec Proposal: Presigned S3 Ingestion (Navegador -> MinIO/S3)

- **Change ID:** `presigned-s3-ingestion`
- **Scope:** Endpoint `/ingestion/presigned-upload-url` para subida directa de archivos multimedia desde el navegador a MinIO/S3 sin saturar la memoria ni ancho de banda del backend FastAPI.

## Problem Statement
Actualmente el endpoint de subida de imágenes de producto en `routers/ingestion.py` recibe el archivo mediante `UploadFile` (bytes completos en memoria del servidor FastAPI) antes de invocar a MinIO. En archivos pesados de video o imágenes de alta resolución, esto genera picos de consumo de memoria en el backend e incrementa la latencia HTTP.

## Proposed Solution
1. **Endpoint Presigned Upload:** Crear `POST /api/v1/tenants/{tenant_id}/ingestion/presigned-upload-url` que reciba `{ "filename": "producto.jpg", "content_type": "image/jpeg" }`.
2. **Generación de Presigned URL en MinIO Client:** Utilizar `minio_client.presigned_put_object` (o presign PUT/GET) para derivar la URL de subida directa y el `object_key` estable (`{tenant_id}/products/{safe_filename}`).
3. **Registro en BD:** El frontend realiza el PUT directo al S3/MinIO y luego confirma la metadata en el backend.
