"""
test_lead_scoring.py

Pruebas TDD para el servicio puro de scoring de leads (REQ-DM-LEAD-03):
keyword + intención clasificada -> score 0-100 y status Nuevo/Contactado/Calificado.
Servicio sin IO, determinista (patrón trend_scorer).
"""

from backend.services.lead_scoring import score_lead


def test_purchase_intent_with_pricing_keyword_is_calificado():
    """REQ-DM-LEAD-03 escenario 1: purchase_intent + keyword precio/demo -> >=60 Calificado."""
    score, status = score_lead("¿Cuál es el precio del servicio premium?", "purchase_intent")
    assert status == "Calificado"
    assert score >= 60
    assert 0 <= score <= 100


def test_spam_without_keywords_is_nuevo():
    """REQ-DM-LEAD-03 escenario 2: spam sin keywords -> <30 Nuevo."""
    score, status = score_lead("gana money crypto win money casino", "spam")
    assert status == "Nuevo"
    assert score < 30


def test_question_without_commercial_keyword_is_nuevo():
    """Triangulación: question sin keyword comercial -> <30 Nuevo."""
    score, status = score_lead("¿cómo funciona el algoritmo de los reels?", "question")
    assert status == "Nuevo"
    assert score < 30


def test_objection_with_commercial_keyword_is_contactado():
    """Triangulación: objection + keyword comercial (demanda información) -> banda media Contactado."""
    score, status = score_lead("me parece caro, tengo una duda sobre el precio", "objection")
    assert status == "Contactado"
    assert 30 <= score < 60


def test_empty_message_is_nuevo():
    """Triangulación: mensaje vacío sin señales -> Nuevo <30 (sin crash)."""
    score, status = score_lead("", "unclear")
    assert status == "Nuevo"
    assert score < 30


def test_audio_keyword_high_intent_is_calificado():
    """REQ-DM-LEAD-01 escenario 1: comentario con keyword AUDIO + señal de compra -> Calificado >=60."""
    score, status = score_lead("¡Me encanta este micrófono! Quiero más AUDIO por favor", "unclear")
    assert status == "Calificado"
    assert score >= 60
