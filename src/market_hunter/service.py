import asyncio
from datetime import UTC, datetime

from market_hunter.models import Listing, SearchRequest, SearchResponse, Source
from market_hunter.providers import EbayBrowseProvider, OlxBgProvider
from market_hunter.providers.base import Provider
from market_hunter.scoring import score_listing
from market_hunter.storage import Storage


class MarketService:
    def __init__(self, storage: Storage, providers: dict[Source, Provider] | None = None) -> None:
        self.storage = storage
        self.providers = providers or {Source.ebay: EbayBrowseProvider(), Source.olx_bg: OlxBgProvider()}

    async def search(self, request: SearchRequest) -> SearchResponse:
        active_providers = [self.providers[source] for source in request.sources if source in self.providers]
        provider_results = await asyncio.gather(*(provider.search(request) for provider in active_providers))
        listings: list[Listing] = []
        errors: dict[Source, str] = {}
        for provider, result in zip(active_providers, provider_results, strict=True):
            if result.provider_error:
                errors[provider.source] = result.provider_error
            listings.extend(result.listings)

        seen: set[str] = set()
        ranked: list[Listing] = []
        for listing in listings:
            if listing.id in seen:
                continue
            seen.add(listing.id)
            scored = score_listing(listing, request.profile)
            if request.max_delivered_price_eur and (scored.delivered_eur or float("inf")) > request.max_delivered_price_eur:
                continue
            ranked.append(scored)
        ranked.sort(key=lambda listing: (listing.score, listing.found_at), reverse=True)
        ranked = ranked[: request.max_results]
        self.storage.upsert_listings(ranked)
        return SearchResponse(
            query=request.query,
            profile=request.profile,
            listings=ranked,
            provider_errors=errors,
            searched_at=datetime.now(UTC),
        )
