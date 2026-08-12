# Especificación de la Interfaz de Teleprompter y Lector de Guiones

## Componente Script4BlockReader
- Desglosa el guión en 4 bloques: `Gancho (Hook)`, `Problema (Pain)`, `Solución (Value)`, `Llamado a la Acción (CTA)`.
- Renderiza badges con colores contrastantes y estimación de tiempo de lectura por bloque.

## Visor Teleprompter en ScriptInspectorView
- Modo de pantalla completa con tipografía de alto contraste (blanco sobre fondo oscuro `#0F172A`).
- Control de velocidad de desplazamiento ajustable (1x, 1.25x, 1.5x, 2x).
- Botón de pausa/reanudación y reinicio de posición.
- Edición en vivo de párrafos con regeneración instantánea del audio narrado.
