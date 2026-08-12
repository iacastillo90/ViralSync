# Especificación de Aislamiento Multi-Inquilino (Multi-Tenant)

## Estructura de Claves en Almacenamiento S3 (MinIO)
- **Bucket Global:** `agency-media` (o variable `MINIO_BUCKET`).
- **Prefijo por Inquilino:** `{tenant_id}/`
- **Ruta de Productos:** `{tenant_id}/products/{product_id}_{filename}`
- **Ruta de Videos Finales:** `{tenant_id}/videos/reel_{short_uuid}_{clean_filename}.mp4`

## Reglas de Seguridad en Base de Datos (PostgreSQL)
- Toda consulta DAO a la tabla `videos` o `scripts` debe incluir explícitamente el filtro `WHERE tenant_id = :tenant_id`.
- La inserción de registros en `insert_video` valida la existencia del `tenant_id` en la tabla principal de inquilinos.
