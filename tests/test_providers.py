from pathlib import Path
import json

from market_hunter.models import Profile, Source
from market_hunter.providers.ebay import EbayBrowseProvider
from market_hunter.providers.olx import OlxBgProvider
from market_hunter.scoring import score_listing

FIXTURES = Path(__file__).parent / "fixtures"


def test_ebay_api_normalizes_listing() -> None:
    listings = EbayBrowseProvider()._parse(json.loads((FIXTURES / "ebay.json").read_text()))
    assert len(listings) == 1
    assert listings[0].source == Source.ebay
    assert listings[0].price_eur == 240.0
    assert listings[0].delivered_eur == 252.0


def test_olx_normalizes_listing() -> None:
    listings = OlxBgProvider()._parse((FIXTURES / "olx.html").read_text(), 10)
    assert len(listings) == 1
    assert listings[0].source == Source.olx_bg
    assert listings[0].price_eur == 240.31
    assert listings[0].country == "BG"


def test_nas_profile_scores_a_good_drive() -> None:
    listing = EbayBrowseProvider()._parse(json.loads((FIXTURES / "ebay.json").read_text()))[0]
    scored = score_listing(listing, Profile.nas_hdd)
    assert scored.score >= 75
    assert scored.max_attractive_price_eur == 480.0
