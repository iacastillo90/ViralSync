"""
test_scheduled_posts_api.py

Pruebas unitarias para la programación de publicaciones en el calendario editorial (Feature 1).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def test_schedule_video_publication():
    from backend.routers.calendar import schedule_video_publication, ScheduleVideoRequest
    from datetime import datetime, timezone

    mock_db = AsyncMock()
    mock_video = MagicMock()
    mock_video.id = "vid_123"
    mock_video.tenant_id = "tenant_123"
    mock_video.platform = "instagram_reels"

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_video
    mock_db.execute.return_value = mock_res

    req = ScheduleVideoRequest(
        video_id="vid_123",
        scheduled_at=datetime.now(timezone.utc),
        platform="instagram_reels",
    )

    res = asyncio.run(schedule_video_publication("tenant_123", req, db=mock_db))
    assert res["status"] == "success"
    assert res["video_id"] == "vid_123"
