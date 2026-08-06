"""
test_filter_5_50.py

Pruebas unitarias TDD para el gate binario del Filtro 5/50.
"""

from agents.criterion.filter_5_50 import passes_5_50_filter


def test_passes_5_50_filter_both_true():
    idea = {
        "entendible_nino_5_anos": True,
        "interesa_50_de_100": True,
    }
    assert passes_5_50_filter(idea) is True


def test_passes_5_50_filter_one_false():
    idea = {
        "entendible_nino_5_anos": True,
        "interesa_50_de_100": False,
    }
    assert passes_5_50_filter(idea) is False


def test_passes_5_50_filter_missing_keys():
    idea = {
        "entendible_nino_5_anos": True,
    }
    assert passes_5_50_filter(idea) is False
