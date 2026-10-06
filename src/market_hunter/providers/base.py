from abc import ABC, abstractmethod

from market_hunter.models import ProviderSearchResult, SearchRequest, Source


class Provider(ABC):
    source: Source

    @abstractmethod
    async def search(self, request: SearchRequest) -> ProviderSearchResult:
        """Return normalized public listing data only; do not make stateful marketplace calls."""
