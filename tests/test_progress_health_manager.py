import asyncio
from unittest.mock import AsyncMock

import pytest

from src.web.managers.campaigns import CampaignProgressManager


@pytest.mark.asyncio
async def test_progress_health_warning_is_stored_broadcast_and_cleared():
    broadcaster = AsyncMock()
    manager = CampaignProgressManager(broadcaster)
    warning = {
        "id": "PH-001",
        "kind": "progress_stalled",
        "message": "Progress may be stalled",
    }

    manager.set_health_warning(warning)
    await asyncio.sleep(0)
    assert manager.get_health_warning() == warning
    broadcaster.emit.assert_awaited_with("progress_health", warning)

    manager.clear_health_warning()
    await asyncio.sleep(0)
    assert manager.get_health_warning() is None
    broadcaster.emit.assert_awaited_with("progress_health", None)
