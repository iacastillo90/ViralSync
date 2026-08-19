"""
test_competitor_mining_api.py

Pruebas unitarias para la Minería de Tendencias de Competidores (Feature 5).
"""

import asyncio
from backend.services.competitor_miner import extract_competitor_viral_patterns
from backend.routers.competitor_mining import mine_competitor_trends, MineCompetitorReq


def test_extract_competitor_viral_patterns():
    patterns = extract_competitor_viral_patterns("Fitness B2B", "@top_fitness_app")
    assert isinstance(patterns, list)
    assert len(patterns) >= 1
    assert "viral_score" in patterns[0]
    assert "pattern_text" in patterns[0]


def test_mine_competitor_trends_router():
    req = MineCompetitorReq(competitor_url_or_topic="@top_agency", niche="Marketing SaaS")
    res = asyncio.run(mine_competitor_trends("tenant_123", req))
    assert res["status"] == "success"
    assert res["patterns_extracted"] >= 1
