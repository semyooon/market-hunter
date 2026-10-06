import pytest
from fastapi import HTTPException

import market_hunter.api as api
from market_hunter.models import WatchCreate
from market_hunter.service import MarketService
from market_hunter.storage import Storage


@pytest.mark.asyncio
async def test_health_and_watch_lifecycle(tmp_path) -> None:
    api.storage = Storage(tmp_path / "market-hunter.db")
    api.service = MarketService(api.storage, providers={})
    api.settings.api_token = "test-token"

    async with api.lifespan(api.app):
        with pytest.raises(HTTPException) as unauthorized:
            await api.require_token()
        assert unauthorized.value.status_code == 401
        await api.require_token("Bearer test-token")
        assert await api.health() == {"status": "ok"}
        created = await api.create_watch(
            WatchCreate(
                name="NAS disks",
                query="WD Ultrastar 20TB SATA",
                profile="nas_hdd",
                sources=["olx_bg"],
            )
        )
        assert created.id == 1
        watches = await api.list_watches()
        assert len(watches) == 1
        assert watches[0].query == "WD Ultrastar 20TB SATA"
