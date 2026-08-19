"""
lead_scoring.py

Servicio puro de calificación de leads inbound (S1 — DM Leads CRM, REQ-DM-LEAD-03).
Sin IO: recibe el mensaje y la intención clasificada y devuelve un score 0-100
con el status correspondiente. Patrón `trend_scorer.py` (reglas + umbrales).

Contrato: `score_lead(message: str, intent: str) -> tuple[int, str]`
  - int:  qualification_score 0-100
  - str:  status en {"Nuevo", "Contactado", "Calificado"}

Reglas deterministas:
  - spam                          ->  <30 Nuevo
  - purchase_intent + keyword     ->  >=60 Calificado
  - señal de compra + keyword     ->  >=60 Calificado (ej. comentario "quiero ... AUDIO")
  - objection/question + keyword  ->  30-59 Contactado (requiere seguimiento comercial)
  - sin keyword comercial         ->  <30 Nuevo
"""

from typing import Tuple

# Palabras clave comerciales que califican un lead (precio/demo + keywords de
# atribución del webhook de Meta: AUDIO, INFO, CONSULTA, PRECIO, OFERTA, PROMO).
_QUALIFY_KEYWORDS = (
    "precio", "demo", "comprar", "contratar", "quiero el sistema", "costo",
    "oferta", "presupuesto", "audio", "info", "consulta", "promo", "catalogo",
    "cotizacion", "muestra",
)

# Señales de intención de compra en el texto del mensaje.
_PURCHASE_SIGNALS = (
    "quiero", "necesito", "me interesa", "comprar", "contratar", "estoy listo",
)


def _has_qualify_keyword(message: str) -> bool:
    return any(kw in message for kw in _QUALIFY_KEYWORDS)


def _has_purchase_signal(message: str) -> bool:
    return any(signal in message for signal in _PURCHASE_SIGNALS)


def score_lead(message: str, intent: str) -> Tuple[int, str]:
    """Calcula el score de calificación (0-100) y el status del lead.

    :param message: texto original del mensaje del prospecto.
    :param intent:  intención clasificada (purchase_intent/objection/question/spam/unclear).
    :return: (qualification_score, status) con status en Nuevo/Contactado/Calificado.
    """
    msg_lower = (message or "").lower()
    has_keyword = _has_qualify_keyword(msg_lower)
    has_signal = _has_purchase_signal(msg_lower)

    # Spam siempre baja calificación (REQ-DM-LEAD-03 escenario 2).
    if intent == "spam":
        return 5, "Nuevo"

    # Alta intención + keyword comercial -> Calificado (>=60).
    if has_keyword and (intent == "purchase_intent" or has_signal):
        return 90, "Calificado"

    # Intención comercial con keyword (objection/question) -> seguimiento: Contactado.
    if has_keyword and intent in ("objection", "question"):
        return 45, "Contactado"

    # Sin keyword comercial -> aún no calificado (Nuevo, <30).
    return 10, "Nuevo"
