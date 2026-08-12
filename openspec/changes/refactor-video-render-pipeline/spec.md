# Especificación Técnica: Integración del Pipeline de Renderizado y Almacenamiento

## Especificaciones de Entrada / Salida

### RenderRequest Payload
```json
{
  "tenant_id": "tenant_demo",
  "title": "Demostración de Producto",
  "scenes": [
    {
      "text": "Descubre el poder del nuevo micrófono USB profesional.",
      "visual_prompt": "microfono de estudio profesional con iluminacion rgb",
      "image_url": "http://localhost:9000/tenant_demo/products/mic.jpg?X-Amz-Signature=..."
    }
  ],
  "product_image_url": "http://localhost:9000/tenant_demo/products/mic.jpg?X-Amz-Signature=...",
  "voice": "es-ES-Neural2-B",
  "keywords": ["microfono", "audio", "podcast"]
}
```

### Contratos de Renderizado
1. **Resolución Target:** Los clips producidos deben encuadrarse estrictamente a 1080x1920 px (relación vertical 9:16).
2. **Audio Alignment:** La duración global del video no debe exceder en más de 0.1s la pista de audio TTS.
3. **Naming Convention en S3:** Los artefactos subidos a MinIO deben nombrarse con el formato `{tenant_id}/videos/reel_{short_uuid}_{filename}.mp4`.
