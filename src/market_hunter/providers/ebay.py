import base64

import httpx

from market_hunter.config import get_settings
from market_hunter.models import Listing, ProviderSearchResult, SearchRequest, Source
from market_hunter.providers.base import Provider
from market_hunter.providers.common import listing_id, money_to_eur, now_utc, parse_amount


class EbayBrowseProvider(Provider):
    """eBay's supported Browse API adapter. It never scrapes an interactive page."""

    source = Source.ebay
    _token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    _search_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    async def search(self, request: SearchRequest) -> ProviderSearchResult:
        settings = get_settings()
        if not settings.ebay_client_id or not settings.ebay_client_secret:
            return ProviderSearchResult(
                provider_error="eBay API disabled: set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET"
            )
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                token = await self._access_token(client, settings.ebay_client_id, settings.ebay_client_secret)
                response = await client.get(
                    self._search_url,
                    params={"q": request.query, "limit": min(request.max_results, settings.max_results_per_source)},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-EBAY-C-MARKETPLACE-ID": settings.ebay_marketplace_id,
                        "X-EBAY-C-ENDUSERCTX": f"contextualLocation=country%3D{request.ship_to}",
                    },
                )
                response.raise_for_status()
            return ProviderSearchResult(listings=self._parse(response.json()))
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            return ProviderSearchResult(provider_error=f"eBay API search unavailable: {exc}")

    @staticmethod
    async def _access_token(client: httpx.AsyncClient, client_id: str, client_secret: str) -> str:
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        response = await client.post(
            EbayBrowseProvider._token_url,
            data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def _parse(self, payload: dict) -> list[Listing]:
        result: list[Listing] = []
        for item in payload.get("itemSummaries", []):
            url = item.get("itemWebUrl")
            title = item.get("title")
            if not url or not title:
                continue
            price = item.get("price", {})
            shipping = (item.get("shippingOptions") or [{}])[0].get("shippingCost", {})
            original_amount = parse_amount(str(price.get("value", "")))
            shipping_amount = parse_amount(str(shipping.get("value", "")))
            currency = price.get("currency")
            price_eur = money_to_eur(original_amount, currency)
            shipping_eur = money_to_eur(shipping_amount, shipping.get("currency") or currency)
            result.append(
                Listing(
                    id=listing_id(self.source, url),
                    source=self.source,
                    title=title,
                    url=url,
                    country=(item.get("itemLocation") or {}).get("country"),
                    price_eur=price_eur,
                    shipping_eur=shipping_eur,
                    delivered_eur=round(price_eur + shipping_eur, 2) if price_eur is not None and shipping_eur is not None else price_eur,
                    currency=currency,
                    original_price=f"{price.get('value', '')} {currency or ''}".strip(),
                    condition=item.get("condition"),
                    seller=(item.get("seller") or {}).get("username"),
                    image_url=(item.get("image") or {}).get("imageUrl"),
                    exact_hardware=item.get("shortDescription"),
                    source_text=item.get("shortDescription"),
                    found_at=now_utc(),
                )
            )
        return result
