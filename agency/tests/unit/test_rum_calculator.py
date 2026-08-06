"""
test_rum_calculator.py

Pruebas unitarias TDD para el calculador de la fórmula RUM:
RUM = U * I * C * S * D * A
"""

import pytest
from agents.criterion.rum_calculator import (
    calculate_rum_score,
    evaluate_rum_threshold,
)


def test_calculate_rum_score_valid():
    metrics = {
        "universalidad": 0.85,
        "intensidad": 0.90,
        "claridad": 0.95,
        "shareability": 0.80,
        "distribucion": 0.85,
        "alineacion": 0.90,
    }
    # 0.85 * 0.90 * 0.95 * 0.80 * 0.85 * 0.90 = 0.444771 -> rounded to 0.44477
    score = calculate_rum_score(metrics)
    assert isinstance(score, float)
    assert score == 0.44477


def test_calculate_rum_score_out_of_bounds():
    metrics = {
        "universalidad": 1.50,  # Invalid (> 1.0)
        "intensidad": 0.90,
        "claridad": 0.95,
        "shareability": 0.80,
        "distribucion": 0.85,
        "alineacion": 0.90,
    }
    with pytest.raises(ValueError) as exc:
        calculate_rum_score(metrics)
    assert "acotada entre 0.0 y 1.0" in str(exc.value)


def test_calculate_rum_score_missing_key():
    metrics = {
        "universalidad": 0.85,
        "intensidad": 0.90,
        # 'claridad' missing
        "shareability": 0.80,
        "distribucion": 0.85,
        "alineacion": 0.90,
    }
    with pytest.raises(KeyError) as exc:
        calculate_rum_score(metrics)
    assert "claridad" in str(exc.value)


def test_evaluate_rum_threshold_pass():
    passes, margin = evaluate_rum_threshold(rum_score=0.44477, threshold=0.050)
    assert passes is True
    assert margin == 0.39477


def test_evaluate_rum_threshold_fail():
    passes, margin = evaluate_rum_threshold(rum_score=0.030, threshold=0.050)
    assert passes is False
    assert margin == -0.020
