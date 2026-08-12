# Especificación de Sincronización Estricta Audio/Video

## Principio de Alineación
El video final renderizado debe sincronizarse de forma idéntica con la pista de voz sintetizada TTS (`gTTS` o proveedor de voz). Ningún video producido por ViralSync debe finalizar con pantalla negra o continuar reproduciéndose tras el fin de la voz.

## Reglas de Recorte
1. **Medición de Duración Real:** Obtener `real_duration = final_audio.duration`.
2. **Tolerancia Máxima:** Si `final_video.duration > real_duration`, aplicar `final_video.subclip(0, real_duration)`.
3. **Respeto a max_duration_seconds:** El parametro global de duracion maxima configurado por el inquilino actúa como limite superior absoluto.

## Manejo de Excepciones
Si el archivo de audio resulta corrupto o entrega duracion 0, se toma el valor por defecto de la escena (ej. 5.0 segundos) y se registra un evento de advertencia en los logs del sistema.
