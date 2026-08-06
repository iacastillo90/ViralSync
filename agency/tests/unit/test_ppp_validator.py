"""
test_ppp_validator.py

Pruebas unitarias TDD para el validador de Promesa Principal de Producto (PPP).
"""

from agents.criterion.ppp_validator import validate_ppp_structure


def test_validate_ppp_valid():
    ppp = "Consigue 100 nuevos clientes SaaS en 30 días sin gastar en anuncios pagados"
    res = validate_ppp_structure(ppp)
    assert res["valid"] is True
    assert res["components_detected"]["has_timeframe"] is True
    assert res["components_detected"]["has_objection_removal"] is True


def test_validate_ppp_missing_timeframe():
    ppp = "Escala tu negocio sin complicaciones"
    res = validate_ppp_structure(ppp)
    assert res["valid"] is False
    assert "ventana de tiempo" in res["reason"]


def test_validate_ppp_missing_objection():
    ppp = "Consigue 50 clientes en 2 semanas"
    res = validate_ppp_structure(ppp)
    assert res["valid"] is False
    assert "remoción de objeción" in res["reason"]


def test_validate_ppp_too_long():
    ppp = "Consigue " + "palabra " * 40 + "en 30 días sin problemas"
    res = validate_ppp_structure(ppp)
    assert res["valid"] is False
    assert "demasiado larga" in res["reason"]
