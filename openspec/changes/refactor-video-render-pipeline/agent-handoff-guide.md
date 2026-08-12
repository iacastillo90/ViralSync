# Guía de Traspaso de Contexto para Agentes de IA Colaboradores

## Resumen para el Siguiente Agente
Este repositorio (`ViralSync`) ha completado exitosamente la refactorización técnica de su canalización de renderizado de video faceless (9:16), la autenticación de almacenamiento multi-inquilino en MinIO y la actualización de la interfaz de usuario en Next.js.

## Puntos Clave a Tener en Cuenta
1. **Renderizador (`agency/microservices/renderer`):** Utiliza MoviePy 1.0.3 con monkey-patch para `PIL.Image.ANTIALIAS` y fuentes TrueType. Las llamadas a MinIO requieren la cabecera `Host: localhost:9000`.
2. **Grafo de Agentes (`agency/agents`):** Los nodos propagan `product_image_url` y `product_object_key`. No modificar los contratos de entrada de Pydantic sin actualizar OpenSpec.
3. **OpenSpec:** Todos los cambios técnicos y especificaciones están registrados de forma permanente en `openspec/changes/refactor-video-render-pipeline/` y `openspec/specs/faceless-overlay-render-hardening/`.
4. **Commits:** Se ha mantenido un historial transparente con más de 50 commits explicativos en español indicando el porqué de cada decisión técnica.
