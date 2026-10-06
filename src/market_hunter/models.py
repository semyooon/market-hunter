from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Source(StrEnum):
    ebay = "ebay"
    olx_bg = "olx_bg"


class Profile(StrEnum):
    generic = "generic"
    nas_hdd = "nas_hdd"


class Verdict(StrEnum):
    excellent = "excellent_candidate"
    good = "good_candidate"
    only_if_cheap = "only_if_cheap"
    skip = "skip"
    unscored = "unscored"


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=180)
    sources: list[Source] = Field(default_factory=lambda: [Source.ebay, Source.olx_bg])
    ship_to: str = Field(default="BG", min_length=2, max_length=2)
    profile: Profile = Profile.generic
    max_results: int = Field(default=20, ge=1, le=100)
    max_delivered_price_eur: float | None = Field(default=None, gt=0, le=100_000)

    @field_validator("query")
    @classmethod
    def normalise_query(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("sources")
    @classmethod
    def unique_sources(cls, value: list[Source]) -> list[Source]:
        if not value:
            raise ValueError("At least one source is required")
        return list(dict.fromkeys(value))


class Listing(BaseModel):
    id: str
    source: Source
    title: str
    url: HttpUrl
    country: str | None = None
    price_eur: float | None = Field(default=None, ge=0)
    shipping_eur: float | None = Field(default=None, ge=0)
    delivered_eur: float | None = Field(default=None, ge=0)
    currency: str | None = None
    original_price: str | None = None
    condition: str | None = None
    seller: str | None = None
    image_url: HttpUrl | None = None
    exact_hardware: str | None = None
    score: int = Field(default=0, ge=0, le=100)
    verdict: Verdict = Verdict.unscored
    max_attractive_price_eur: float | None = None
    caveats: list[str] = Field(default_factory=list)
    source_text: str | None = None
    found_at: datetime
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


class ProviderSearchResult(BaseModel):
    listings: list[Listing] = Field(default_factory=list)
    provider_error: str | None = None


class SearchResponse(BaseModel):
    query: str
    profile: Profile
    listings: list[Listing]
    provider_errors: dict[Source, str] = Field(default_factory=dict)
    searched_at: datetime


class WatchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    query: str = Field(min_length=2, max_length=180)
    sources: list[Source] = Field(default_factory=lambda: [Source.ebay, Source.olx_bg])
    ship_to: str = Field(default="BG", min_length=2, max_length=2)
    profile: Profile = Profile.generic
    max_delivered_price_eur: float | None = Field(default=None, gt=0, le=100_000)
    interval_minutes: int = Field(default=360, ge=30, le=10_080)


class Watch(WatchCreate):
    id: int
    active: bool = True
    created_at: datetime
    last_run_at: datetime | None = None
    last_match_count: int = 0
