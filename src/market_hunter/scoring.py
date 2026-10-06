import re

from market_hunter.models import Listing, Profile, Verdict


def score_listing(listing: Listing, profile: Profile) -> Listing:
    if profile == Profile.nas_hdd:
        return _score_nas_hdd(listing)
    listing.score = 0
    listing.verdict = Verdict.unscored
    return listing


def _score_nas_hdd(listing: Listing) -> Listing:
    text = f"{listing.title} {listing.source_text or ''}".lower()
    caveats: list[str] = []
    score = 35
    capacity_tb = _capacity_tb(text)

    if capacity_tb is None:
        caveats.append("Capacity is not clear from the listing")
        score -= 20
    elif capacity_tb < 12:
        caveats.append("Below the 12 TB target")
        score -= 30
    elif capacity_tb <= 20:
        score += 20

    if any(name in text for name in ("ultrastar", "exos", "toshiba mg", "mg0", "mg1")):
        score += 15
    else:
        caveats.append("Drive family needs independent verification")

    if "sas" in text:
        caveats.append("SAS: include HBA and cabling in total cost")
        score -= 25
    if "smr" in text:
        caveats.append("SMR drive — unsuitable for the ZFS mirror target")
        score -= 65
    if "sata" in text:
        score += 8
    if "smart" not in text and "tested" not in text:
        caveats.append("Ask for a current SMART report before buying")
    if "warranty" in text or "гаранц" in text:
        score += 6

    eur_per_tb = listing.delivered_eur / capacity_tb if listing.delivered_eur and capacity_tb else None
    if eur_per_tb is not None:
        if eur_per_tb <= 20:
            score += 22
        elif eur_per_tb <= 22:
            score += 17
        elif eur_per_tb <= 24:
            score += 10
        elif eur_per_tb > 30:
            score -= 15
            caveats.append(f"€{eur_per_tb:.2f}/TB is above the target")
        listing.max_attractive_price_eur = round(capacity_tb * 24, 2)

    listing.caveats = caveats
    listing.score = max(0, min(100, score))
    if "smr" in text or score < 25:
        listing.verdict = Verdict.skip
    elif score >= 75:
        listing.verdict = Verdict.excellent
    elif score >= 55:
        listing.verdict = Verdict.good
    else:
        listing.verdict = Verdict.only_if_cheap
    return listing


def _capacity_tb(text: str) -> float | None:
    match = re.search(r"\b(\d{1,2}(?:[.,]\d+)?)\s*(?:tb|тб)\b", text)
    return float(match.group(1).replace(",", ".")) if match else None
