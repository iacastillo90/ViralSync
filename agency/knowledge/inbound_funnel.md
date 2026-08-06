# Embudo de Conversión Inbound (Webhooks + Atribución)

## Flujo de Conversión
1. **CTA con Palabra Clave:** Cada guion finaliza con un CTA especificando una palabra clave única (ej. "CONSULTA").
2. **Webhook Inbound:** Meta dispara un evento HTTP a `/backend/webhooks/instagram_inbound.py`.
3. **Calificador Ligero:** El agente calificador valida la palabra clave contra la campaña activa y vincula el lead al `video_id` correspondiente.
4. **Traspaso al Humano:** El lead calificado aparece en tiempo real en el dashboard. El sistema clasifica y atribuye; el humano cierra la venta.
