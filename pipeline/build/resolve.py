"""Pick one value per spec field: manufacturer > lab measurement > retailer (decision 14).

* manufacturer: data/interim/specs.json (phase 3), every value quoting the brand's page;
* lab measurement: values MEASURED by a review source (RunRepeat, phase 4), used for the
  stack heights, the lug depth and (since scoring 0.2.0) the platform widths;
* retailer: what Tradeinn / Glisshop show (phase 3b), lower confidence.

The chosen value keeps its own provenance (source name, URL, date, snippet) and
`Specs.sources` records which tier it came from. When no tier knows a value, the field is
null and its `missing_reason` says why each tier failed. Nothing is ever estimated.
"""

from pipeline.models import (
    CollectedReview,
    MatchConfidence,
    ModelSpecs,
    RetailerFallback,
    SourcedValue,
    Specs,
    SpecSource,
)

# Spec field -> key of the lab measurement in CollectedReview.lab_values. RunRepeat's
# "midsole width" at the heel / forefoot is the platform width of the spec (stability).
LAB_FIELDS = {
    "stack_heel_mm": "stack_heel_mm",
    "stack_forefoot_mm": "stack_forefoot_mm",
    "lug_depth_mm": "lug_depth_mm",
    "platform_width_heel_mm": "midsole_width_heel_mm",
    "platform_width_forefoot_mm": "midsole_width_forefoot_mm",
}
LAB_SOURCE = "runrepeat"
# An exact review is a better proxy for the standard model than one of a variant (GTX...).
MATCH_ORDER = [MatchConfidence.EXACT, MatchConfidence.MANUAL, MatchConfidence.VARIANT]
NEVER_COLLECTED = {
    "lug_spacing": "not published by manufacturers or retailers (no source collected)",
}
NOT_FROM_MANUFACTURER = "rarely published by manufacturers; not collected"


def lab_value(field: str, reviews: list[CollectedReview]) -> SourcedValue | None:
    """The lab measurement of spec `field` from the best-matching lab review, if any."""
    key = LAB_FIELDS[field]
    candidates = [r for r in reviews if r.source == LAB_SOURCE and key in r.lab_values]
    if not candidates:
        return None
    review = min(candidates, key=lambda r: MATCH_ORDER.index(r.review_match_confidence))
    value = review.lab_values[key]
    if value.value is None:
        return None
    if review.review_match_confidence == MatchConfidence.VARIANT:
        # Say so: a GTX or wide version can measure slightly differently.
        note = f"{value.note}; measured on a variant ({review.match_note})"
        value = value.model_copy(update={"note": note})
    return value


def _lab_reason(field: str, reviews: list[CollectedReview]) -> str:
    if not any(r.source == LAB_SOURCE for r in reviews):
        return "no RunRepeat lab test of this model"
    return "RunRepeat lab test does not give it"


def resolve_specs(specs: ModelSpecs, reviews: list[CollectedReview]) -> Specs:
    """The final `Specs` of one model, each field from the best available tier."""
    retailer: RetailerFallback | None = specs.retailer_fallback
    resolved: dict[str, object] = {}
    sources: dict[str, SpecSource] = {}
    for name, field_info in Specs.model_fields.items():
        if name == "sources":
            continue
        target = field_info.annotation  # SourcedFloat, SourcedStr, ...
        if name in NEVER_COLLECTED:
            resolved[name] = target(missing_reason=NEVER_COLLECTED[name])
            continue
        tiers: list[tuple[SpecSource, SourcedValue | None, str]] = []
        if name in ModelSpecs.model_fields:
            value = getattr(specs, name)
            tiers.append((SpecSource.MANUFACTURER, value, value.missing_reason or ""))
        else:
            tiers.append((SpecSource.MANUFACTURER, None, NOT_FROM_MANUFACTURER))
        if name in LAB_FIELDS:
            tiers.append(
                (SpecSource.LAB_MEASUREMENT, lab_value(name, reviews), _lab_reason(name, reviews))
            )
        if name in RetailerFallback.model_fields:
            value = getattr(retailer, name) if retailer else None
            reason = value.missing_reason if value else "retailer fallback not built"
            tiers.append((SpecSource.RETAILER, value, reason or ""))
        for tier, value, _ in tiers:
            if value is not None and value.value is not None:
                resolved[name] = target.model_validate(value.model_dump())
                sources[name] = tier
                break
        else:
            reasons = "; ".join(f"{tier.value}: {reason}" for tier, _, reason in tiers if reason)
            resolved[name] = target(missing_reason=reasons or "no source gives it")
    return Specs(**resolved, sources=sources)


def spec_values(specs: Specs) -> dict[str, object]:
    """Plain values of the resolved specs (None = missing), as the evaluator reads them."""
    values: dict[str, object] = {}
    for name in Specs.model_fields:
        if name == "sources":
            continue
        value = getattr(specs, name).value
        if isinstance(value, list):
            value = [str(v.value if hasattr(v, "value") else v) for v in value]
        elif hasattr(value, "value"):  # enums (plate, lug spacing) as their text value
            value = value.value
        values[name] = value
    return values
