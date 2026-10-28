"""Buyer-rating aggregate per model: the Bayesian average of docs/scoring-spec.md §4."""

from pipeline.models import BuyerRatingSummary, ModelOffer
from pipeline.utils.config import load_scoring_config


def rating_pairs(offers: list[ModelOffer]) -> list[tuple[float, int]]:
    """(rating, review_count) pairs to count, one per distinct pair and retailer.

    Tradeinn shows the same reviews on every colour of a product, so identical
    (rating, count) pairs at one retailer are almost certainly the same reviews and are
    counted once. This is a heuristic: two colourways could coincidentally share a pair.
    """
    seen: set[tuple[str, float, int]] = set()
    pairs = []
    for offer in offers:
        if offer.rating is None or not offer.review_count:
            continue
        marker = (offer.retailer.value, offer.rating, offer.review_count)
        if marker not in seen:
            seen.add(marker)
            pairs.append((offer.rating, offer.review_count))
    return pairs


def catalogue_prior(all_pairs: list[tuple[float, int]]) -> float:
    """Review-weighted mean rating of the catalogue, or the fallback if too few reviews."""
    config = load_scoring_config()["buyer_rating"]
    total = sum(count for _, count in all_pairs)
    if total < config["min_reviews_for_catalogue_prior"]:
        return float(config["fallback_prior_mean"])
    return sum(rating * count for rating, count in all_pairs) / total


def bayesian_summary(pairs: list[tuple[float, int]], prior_mean: float) -> BuyerRatingSummary:
    """Pool the pairs of one model and shrink them towards the prior (spec §4)."""
    strength = float(load_scoring_config()["buyer_rating"]["prior_strength"])
    total = sum(count for _, count in pairs)
    weighted_sum = sum(rating * count for rating, count in pairs)
    return BuyerRatingSummary(
        review_count_total=total,
        raw_mean_0_5=round(weighted_sum / total, 3) if total else None,
        bayesian_mean_0_5=(
            round((strength * prior_mean + weighted_sum) / (strength + total), 3) if total else None
        ),
        prior_mean_0_5=round(prior_mean, 3),
        prior_strength=strength,
    )
