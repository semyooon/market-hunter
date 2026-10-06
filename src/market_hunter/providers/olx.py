from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from market_hunter.config import get_settings
from market_hunter.models import Listing, ProviderSearchResult, SearchRequest, Source
from market_hunter.providers.base import Provider
from market_hunter.providers.common import listing_id, money_to_eur, now_utc, parse_amount


class OlxBgProvider(Provider):
    source = Source.olx_bg
    _search_url = "https://www.olx.bg/ads/q-{query}/"

    async def search(self, request: SearchRequest) -> ProviderSearchResult:
        settings = get_settings()
        url = self._search_url.format(query=quote(request.query.replace(" ", "-")))
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": settings.user_agent, "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.7"},
                timeout=settings.request_timeout_seconds,
            ) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
            return ProviderSearchResult(listings=self._parse(response.text, settings.max_results_per_source))
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderSearchResult(provider_error=f"OLX search unavailable: {exc}")

    def _parse(self, html: str, maximum: int) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select('[data-cy="l-card"]') or soup.select('div[data-testid="l-card"]')
        result: list[Listing] = []
        for card in cards[:maximum]:
            anchor = card.select_one('[data-testid="card-title-link"][href]') or card.select_one("a[href]")
            title_node = card.select_one('h4, h6, [data-cy="listing-ad-title"]')
            price_node = card.select_one('[data-testid="ad-price"], [data-cy="ad-card-price"]')
            if not anchor or not title_node:
                continue
            href = anchor.get("href", "")
            if href.startswith("/"):
                href = f"https://www.olx.bg{href}"
            if not href.startswith("https://www.olx.bg/"):
                continue
            if "extended_search_no_results" in href:
                # OLX inserts unrelated recommendations after an empty search.
                continue
            title = title_node.get_text(" ", strip=True)
            original_price = price_node.get_text(" ", strip=True) if price_node else None
            amount = parse_amount(original_price)
            currency = "EUR" if original_price and "€" in original_price else "BGN"
            price_eur = money_to_eur(amount, currency)
            location_node = card.select_one('[data-testid="location-date"], [data-cy="ad-card-location"]')
            image = card.select_one("img[src]")
            image_url = image.get("src") if image and image.get("src", "").startswith(("http://", "https://")) else None
            result.append(
                Listing(
                    id=listing_id(self.source, href),
                    source=self.source,
                    title=title,
                    url=href,
                    country="BG",
                    price_eur=price_eur,
                    delivered_eur=price_eur,
                    currency=currency,
                    original_price=original_price,
                    image_url=image_url,
                    source_text=location_node.get_text(" ", strip=True) if location_node else None,
                    found_at=now_utc(),
                )
            )
        return result
