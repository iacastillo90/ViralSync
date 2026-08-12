# Matriz de Verificación y Pruebas End-to-End (E2E)

| ID Prueba | Descripción de la Prueba | Tipo | Criterio de Éxito | Estado |
|---|---|---|---|---|
| TEST-E2E-01 | Renderizado completo de video 9:16 desde prompt | E2E | Archivo MP4 generado con tarjeta de producto y audio tts | PASSED |
| TEST-E2E-02 | Firma AWS SigV4 en red interna Docker | Integración | Petición GET con Host localhost devuelve 200 OK | PASSED |
| TEST-E2E-03 | Escena de fallback animada cuando Pexels no responde | Unidad | VideoClip procedural renderiza correctamente | PASSED |
| TEST-E2E-04 | Pruebas de carga concurrentes multi-inquilino | Carga | Locust ejecuta 100 usuarios distribuidos sin errores | PASSED |
| TEST-E2E-05 | Re-firmado de URLs caducadas en MediaGalleryView | Frontend | La URL de MinIO se actualiza dinámicamente | PASSED |
