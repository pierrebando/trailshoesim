"""Criterion scores (spec §2), terrain scores (§3) and confidence (§8) of one shoe.

All constants come from pipeline/config/scoring.yaml (`config` below is that file, read
once). Every score keeps a `provenance` list: each input that was used, the kind of
source it came from, and its share of the final value (the shares sum to 1).
"""

import datetime as dt

from pipeline.build.evaluator import SubScore, evaluate
from pipeline.models import (
    Confidence,
    ConfidenceLevel,
    CriteriaScores,
    CriterionScore,
    ExpertReview,
    RetailOffer,
    ScoreInput,
    Specs,
    TerrainScore,
    TerrainScores,
)

EXPERT_INPUT = "expert_reviews"
PRIOR_INPUT = "neutral_prior"


def _provenance(sub: SubScore, specs: Specs, share: float) -> list[ScoreInput]:
    """Provenance of the spec inputs of a sub-score that counts for `share` of the score."""
    known_weight = sum(i.weight for i in sub.used)
    return [
        ScoreInput(
            input=i.name,
            source=specs.sources[i.name.removeprefix("specs.")].value,
            value=i.label,
            input_score_0_10=i.score,
            weight=share * i.weight / known_weight,
        )
        for i in sub.used
    ]


def expert_sub_score(criterion: str, reviews: list[ExpertReview]) -> tuple[float | None, int]:
    """E_c = mean of the reviews' aspect scores; each review counts once (spec §2.4)."""
    scores = [r.aspects[criterion].score_0_10 for r in reviews if criterion in r.aspects]
    return (sum(scores) / len(scores) if scores else None), len(scores)


def criterion_score(
    criterion: str, specs: Specs, values: dict, reviews: list[ExpertReview], config: dict
) -> CriterionScore:
    """Blend of the spec and expert sub-scores of one criterion (spec §2.3-2.5)."""
    settings = config["criteria"][criterion]
    sub = evaluate(
        settings["spec_inputs"],
        values,
        config["lookups"],
        # fit_width lowers the bar: the shop's tag (weight 0.3) is most shoes' only input.
        settings.get("min_spec_input_coverage", config["common"]["min_spec_input_coverage"]),
        required=tuple(settings.get("required_inputs", ())),
    )
    expert, n_reviews = expert_sub_score(criterion, reviews)
    full_count = config["expert_reviews"]["full_weight_review_count"]
    trust = min(1.0, n_reviews / full_count)
    w_spec = settings["blend"]["spec"] if sub.score is not None else 0.0
    w_expert = settings["blend"]["expert"] * trust if expert is not None else 0.0
    w_prior = 0.0
    if sub.score is None and expert is not None:
        # No spec to weigh against: without this, one review would make 100% of the score.
        # The neutral prior takes the share the reviews have not earned yet (spec §2.5).
        w_expert, w_prior = trust, 1.0 - trust
    prior = config["expert_reviews"]["prior_score_without_specs"]
    total = w_spec + w_expert + w_prior
    score = None
    if total:
        weighted = w_spec * (sub.score or 0.0) + w_expert * (expert or 0.0) + w_prior * prior
        score = weighted / total

    provenance: list[ScoreInput] = []
    if sub.score is not None:
        provenance += _provenance(sub, specs, w_spec / total)
    if expert is not None:
        provenance.append(
            ScoreInput(
                input=EXPERT_INPUT,
                source=EXPERT_INPUT,
                value=f"{n_reviews} review{'s' if n_reviews > 1 else ''}",
                input_score_0_10=expert,
                weight=w_expert / total,
            )
        )
    if w_prior:
        provenance.append(
            ScoreInput(
                input=PRIOR_INPUT,
                source=PRIOR_INPUT,
                value=f"too few reviews ({n_reviews} of {full_count})",
                input_score_0_10=prior,
                weight=w_prior / total,
            )
        )
    return CriterionScore(
        score_0_10=score,
        spec_score_0_10=sub.score,
        expert_score_0_10=expert,
        spec_input_coverage=sub.coverage,
        expert_review_count=n_reviews,
        inputs_used=[i.name for i in sub.used] + ([EXPERT_INPUT] if expert is not None else []),
        inputs_missing=[i.name for i in sub.missing] + ([EXPERT_INPUT] if expert is None else []),
        provenance=provenance,
    )


def criteria_scores(
    specs: Specs, values: dict, reviews: list[ExpertReview], config: dict
) -> CriteriaScores:
    """The eight criterion scores."""
    return CriteriaScores(
        **{
            c: criterion_score(c, specs, values, reviews, config)
            for c in CriteriaScores.model_fields
        }
    )


def terrain_scores(specs: Specs, values: dict, config: dict) -> TerrainScores:
    """The five terrain scores: specs only, lug depth required (spec §3)."""
    settings = config["terrain"]
    scores = {}
    for terrain in TerrainScores.model_fields:
        sub = evaluate(
            settings["scores"][terrain],
            values,
            config["lookups"],
            settings["min_input_coverage"],
            required=tuple(settings["required_inputs"]),
        )
        scores[terrain] = TerrainScore(
            score_0_10=sub.score,
            inputs_used=[i.name for i in sub.used],
            inputs_missing=[i.name for i in sub.missing],
            provenance=_provenance(sub, specs, 1.0) if sub.score is not None else [],
        )
    return TerrainScores(**scores)


def spec_completeness(values: dict, config: dict) -> float:
    """Weighted share of known spec fields (spec §8); weight counts men's OR women's."""
    weights = config["confidence"]["spec_completeness_weights"]
    known = dict(values)
    known["weight_g"] = (
        values["weight_g"] if values["weight_g"] is not None else values["weight_women_g"]
    )
    return sum(w for f, w in weights.items() if known[f] is not None) / sum(weights.values())


def confidence(
    values: dict,
    reviews: list[ExpertReview],
    retail: list[RetailOffer],
    build_date: dt.date,
    config: dict,
) -> Confidence:
    """Confidence block and level (spec §8), with the reasons it is not higher."""
    completeness = spec_completeness(values, config)
    n_expert = len(reviews)
    n_buyer = sum(o.review_count or 0 for o in retail)
    dates = [o.price_date for o in retail]
    age = (build_date - max(dates)).days if dates else None

    def failures(level: str) -> list[str]:
        rules = config["confidence"]["levels"][level]
        evidence = rules["evidence"]
        problems = []
        if completeness < rules["min_spec_completeness"]:
            problems.append(
                f"Spec completeness {completeness:.0%} ({level} needs "
                f"{rules['min_spec_completeness']:.0%})"
            )
        if age is None:
            problems.append("No price date")
        elif age > rules["max_price_age_days"]:
            problems.append(
                f"Prices are {age} days old ({level} needs <= {rules['max_price_age_days']})"
            )
        expert_ok = n_expert >= evidence["min_expert_reviews"]
        buyer_ok = n_buyer >= evidence["min_buyer_reviews"]
        expert_text = (
            f"{n_expert} expert review{'s' if n_expert != 1 else ''} "
            f"({level} needs {evidence['min_expert_reviews']})"
        )
        buyer_text = f"{n_buyer} buyer reviews ({level} needs {evidence['min_buyer_reviews']})"
        if evidence["require"] == "all":
            problems += [
                t for ok, t in ((expert_ok, expert_text), (buyer_ok, buyer_text)) if not ok
            ]
        elif not (expert_ok or buyer_ok):
            problems.append(f"{expert_text} and {buyer_text}; {level} needs one of them")
        return problems

    high, medium = failures("high"), failures("medium")
    if not high:
        level, reasons = ConfidenceLevel.HIGH, []
    elif not medium:
        level, reasons = ConfidenceLevel.MEDIUM, high
    else:
        level, reasons = ConfidenceLevel.LOW, medium
    return Confidence(
        spec_completeness_0_1=completeness,
        expert_review_count=n_expert,
        buyer_review_count=n_buyer,
        price_age_days=age,
        level=level,
        reasons=reasons,
    )
