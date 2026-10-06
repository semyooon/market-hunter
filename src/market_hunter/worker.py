import asyncio
import logging
import time

from market_hunter.config import get_settings
from market_hunter.models import SearchRequest
from market_hunter.service import MarketService
from market_hunter.storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("market_hunter.worker")


async def scan_due_watches(service: MarketService, storage: Storage) -> None:
    for watch in storage.due_watches():
        request = SearchRequest(
            query=watch.query,
            sources=watch.sources,
            ship_to=watch.ship_to,
            profile=watch.profile,
            max_delivered_price_eur=watch.max_delivered_price_eur,
            max_results=100,
        )
        response = await service.search(request)
        new_matches = storage.record_watch_run(watch.id, response.listings)
        if new_matches:
            logger.info("watch=%s new_matches=%s ids=%s", watch.id, len(new_matches), [x.id for x in new_matches])
        else:
            logger.info("watch=%s no new matches", watch.id)


def run() -> None:
    settings = get_settings()
    storage = Storage(settings.database_path)
    storage.initialize()
    service = MarketService(storage)
    while True:
        try:
            asyncio.run(scan_due_watches(service, storage))
        except Exception:
            logger.exception("watch scan failed")
        time.sleep(settings.scan_interval_seconds)
