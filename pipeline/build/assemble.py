"""Merge the interim files into one `Shoe` record per catalogue model (phase 6)."""

import datetime as dt

from pipeline.build.resolve import resolve_specs, spec_values
from pipeline.build.scores import confidence, criteria_scores, terrain_scores
from pipeline.models import (
    AspectAssessment,
    CanonicalModel,
    CollectedReview,
    ExpertReview,
    InterimAspects,
    ModelSpecs,
    RetailOffer,
    ReviewAspects,
    Shoe,
    SourcedValue,
)


def retail_offers(model: CanonicalModel) -> list[RetailOffer]:
    """One offer per retailer listing; the day a price was read is its price date."""
    offers = []
    for offer in model.offers:
        if offer.price_eur is None:
            continue  # a listing without a price cannot be shown as an offer
        offers.append(
            RetailOffer(
                retailer=offer.retailer,
                url=offer.url,
                price_eur=offer.price_eur,
                price_date=offer.retrieved_at,
                rating=offer.rating if offer.review_count else None,
                review_count=offer.review_count,
            )
        )
    return offers


def expert_reviews(
    reviews: list[CollectedReview], aspects: list[ReviewAspects], aspects_file: InterimAspects
) -> list[ExpertReview]:
    """The reviews of one model with the aspects phase 5 found in each of them."""
    by_url = {str(a.review_url): a for a in aspects}
    nlp_model = aspects_file.nlp_model
    if aspects_file.direction_model:
        nlp_model = f"{nlp_model} + {aspects_file.direction_model}"
    result = []
    for review in reviews:
        found = by_url.get(str(review.url))
        result.append(
            ExpertReview(
                source=review.source,
                url=review.url,
                date=review.date,
                retrieved_at=review.retrieved_at,
                language=review.language,
                conclusion_excerpt=review.conclusion_excerpt,
                aspects={
                    criterion: AspectAssessment(
                        score_0_10=a.score_0_10,
                        evidence_excerpt=a.evidence_excerpt,
                        mention_count=a.n_sentences,
                    )
                    for criterion, a in (found.aspects.items() if found else [])
                },
                nlp_model=nlp_model if found else None,
            )
        )
    return result


def build_shoe(
    model: CanonicalModel,
    specs: ModelSpecs,
    reviews: list[CollectedReview],
    aspects_file: InterimAspects,
    build_date: dt.date,
    config: dict,
    manual: dict[str, SourcedValue] | None = None,
) -> Shoe:
    """The final record of one model (raises if a rule of the data model is broken)."""
    resolved = resolve_specs(specs, reviews, manual)
    values = spec_values(resolved)
    model_aspects = aspects_file.models.get(model.id)
    review_list = expert_reviews(
        reviews, model_aspects.reviews if model_aspects else [], aspects_file
    )
    retail = retail_offers(model)
    return Shoe(
        id=model.id,
        brand=model.brand,
        model=model.model,
        version=model.version,
        category=model.category,
        newer_version_id=model.newer_version_id,
        gender_variants=model.gender_variants,
        release_year=specs.release_year,
        retail=retail,
        specs=resolved,
        expert_reviews=review_list,
        buyer_rating=model.buyer_rating,
        criteria_scores=criteria_scores(resolved, values, review_list, config),
        terrain_scores=terrain_scores(resolved, values, config),
        confidence=confidence(values, review_list, retail, build_date, config),
    )
