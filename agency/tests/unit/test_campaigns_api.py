"""
test_campaigns_api.py

Pruebas unitarias para el router de Modo Campaña (Fase 4A).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def test_create_and_list_campaigns():
    from backend.routers.campaigns import create_new_campaign, list_campaigns, CampaignCreateReq

    mock_campaign = MagicMock()
    mock_campaign.id = "camp_123"
    mock_campaign.tenant_id = "tenant_123"
    mock_campaign.name = "Lanzamiento Noviembre"
    mock_campaign.objective = "Posicionamiento"
    mock_campaign.target_reels_count = 8
    mock_campaign.status = "active"
    mock_campaign.created_at = None

    with patch("backend.routers.campaigns.insert_campaign", new_callable=AsyncMock) as mock_insert, \
         patch("backend.routers.campaigns.get_campaigns_by_tenant", new_callable=AsyncMock) as mock_get:
        
        mock_insert.return_value = mock_campaign
        mock_get.return_value = [mock_campaign]

        req = CampaignCreateReq(name="Lanzamiento Noviembre", objective="Posicionamiento", target_reels_count=8)
        created = asyncio.run(create_new_campaign("tenant_123", req))
        assert created["id"] == "camp_123"

        listed = asyncio.run(list_campaigns("tenant_123"))
        assert len(listed) == 1
        assert listed[0]["name"] == "Lanzamiento Noviembre"
