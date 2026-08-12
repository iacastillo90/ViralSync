# Propuesta de Refactorización: Canalización de Renderizado de Video y Firma Multi-Inquilino

## Resumen Ejecutivo

Esta propuesta formaliza los cambios de arquitectura e ingeniería realizados en la plataforma **ViralSync** para resolver cuellos de botella en la producción automática de videos verticales faceless (9:16). Se aborda la estabilidad del microservicio de renderizado, la correcta inyección de metadatos de producto a lo largo del grafo de agentes (LangGraph), la preservación de firmas de autenticación AWS SigV4 sobre MinIO en entornos contenerizados y la mejora significativa en la experiencia visual mediante la superposición de tarjetas de producto y subtítulos glassmorphism.

## Motivación & Objetivos Tecnológicos

1. **Estabilidad en Renderizado de Video:** Evitar excepciones fatales provocadas por la incompatibilidad de `MoviePy 1.0.3` con versiones recientes de `Pillow` y `NumPy` mediante el fijado estricto de versiones y la inclusión de tipografías vectoriales en el contenedor Docker.
2. **Fidelidad y Estética Visual:** Implementar superposiciones dinámicas sobre los fotogramas (overlays 9:16) que incluyan la tarjeta flotante del producto promocionado en el tercio superior y subtítulos estilizados con opacidad y bordes suaves en el tercio inferior.
3. **Integridad en Almacenamiento Multi-Inquilino:** Garantizar que las URLs presignadas generadas desde el cliente de MinIO permitan la descarga de artefactos tanto desde el exterior (navegador web) como desde la red interna de Docker (`minio:9000`), inyectando cabeceras `Host` dinámicas para no invalidar el hash de firma SigV4.
4. **Resiliencia en el Grafo de Agentes:** Asegurar la propagación continua de `product_image_url` y `product_object_key` desde la fase de ingestión hasta la tarea de Celery (`trigger_video_render`), manteniendo un reporte transparente de errores sin fabricar URIs falsas.
