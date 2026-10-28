"""Phase 6: the scoring functions of docs/scoring-spec.md, spec resolution, confidence,
and an end-to-end build of the committed interim data validated against the schemas."""

import datetime as dt
from itertools import pairwise
from pathlib import Path

import pytest

from pipeline.build.evaluator import evaluate, interp, lookup_class
from pipeline.build.resolve import resolve_specs, spec_values
from pipeline.build.scores import confidence, criterion_score, terrain_scores
from pipeline.models import (
    AspectAssessment,
    CollectedReview,
    ExpertReview,
    LabFallback,
    MatchConfidence,
    ModelSpecs,
    RetailerFallback,
    RetailerTags,
    RetailOffer,
    SourcedFloat,
    Specs,
    SpecSource,
)
from pipeline.utils.config import load_scoring_config

CONFIG = load_scoring_config()
URL = "https://example.org/fictional"
DAY = dt.date(2026, 10, 28)


def known(cls, value, source="example.org"):
    return cls(
        value=value, source_name=source, source_url=URL, retrieved_at=DAY, raw_snippet=str(value)
    )


def missing(cls, reason="not on the page"):
    return cls(missing_reason=reason)


def make_specs(**values) -> Specs:
    """Specs with the given known values (from the manufacturer) and everything else missing."""
    fields = {}
    for name, info in Specs.model_fields.items():
        if name == "sources":
            continue
        cls = info.annotation
        fields[name] = known(cls, values[name]) if name in values else missing(cls)
    return Specs(**fields, sources=dict.fromkeys(values, SpecSource.MANUFACTURER))


def review(**aspects: float) -> ExpertReview:
    return ExpertReview(
        source="fictional_source",
        url=URL,
        date=None,
        retrieved_at=DAY,
        conclusion_excerpt=None,
        aspects={
            c: AspectAssessment(
                score_0_10=s, evidence_excerpt="A fictional sentence.", mention_count=1
            )
            for c, s in aspects.items()
        },
    )


def score(criterion: str, reviews: tuple = (), **values):
    specs = make_specs(**values)
    return criterion_score(criterion, specs, spec_values(specs), list(reviews), CONFIG)


# --- helpers (spec §0.3, §2.1) --------------------------------------------------------


def test_interp_is_piecewise_linear_and_held_outside() -> None:
    anchors = [[30, 5], [35, 7]]
    assert interp(33, anchors) == pytest.approx(6.2)
    assert interp(10, anchors) == 5 and interp(99, anchors) == 7
    with pytest.raises(ValueError):
        interp(1, [[2, 0], [1, 1]])


def test_lookup_takes_the_first_matching_rule_and_unknown_is_missing() -> None:
    rules = CONFIG["lookups"]["foam_classes"]["rules"]
    assert lookup_class("Supercritical EVA", rules) == "supercritical_or_gas_infused"
    assert lookup_class("FloatPro", rules) is None
    result = evaluate({"midsole_foam": {"weight": 1, "lookup": "foam_classes.cushioning"}},
                      {"midsole_foam": "FloatPro"}, CONFIG["lookups"], 0.4)  # fmt: skip
    assert result.score is None and result.coverage == 0


# --- criterion scores (spec §2) -------------------------------------------------------


def test_worked_example_of_the_spec() -> None:
    result = score(
        "cushioning",
        (review(cushioning=8), review(cushioning=7)),
        stack_heel_mm=33.0,
        stack_forefoot_mm=27.0,
        midsole_foam="supercritical EVA",
    )
    assert result.spec_score_0_10 == pytest.approx(6.525)
    assert result.expert_score_0_10 == pytest.approx(7.5)
    assert result.score_0_10 == pytest.approx(6.83, abs=0.005)
    assert sum(p.weight for p in result.provenance) == pytest.approx(1)
    assert {p.input for p in result.provenance} == {
        "specs.stack_heel_mm", "specs.stack_forefoot_mm", "specs.midsole_foam", "expert_reviews"
    }  # fmt: skip


def test_missing_input_is_dropped_and_the_rest_renormalised() -> None:
    result = score("cushioning", stack_heel_mm=33.0, midsole_foam="supercritical EVA")
    assert result.spec_score_0_10 == pytest.approx((0.45 * 6.2 + 0.25 * 7.5) / 0.70)
    assert result.spec_input_coverage == pytest.approx(0.70)
    assert result.inputs_missing == ["specs.stack_forefoot_mm", "expert_reviews"]


def test_nothing_known_gives_null_never_a_default() -> None:
    result = score("cushioning")
    assert result.score_0_10 is None and result.spec_score_0_10 is None
    assert result.provenance == []


def test_coverage_below_minimum_gives_no_spec_score() -> None:
    # midsole_foam alone is 0.25 of the cushioning inputs, below min coverage 0.45.
    assert score("cushioning", midsole_foam="EVA").spec_score_0_10 is None
    # The heel stack alone (0.45) is enough.
    assert score("cushioning", stack_heel_mm=33.0).spec_score_0_10 == pytest.approx(6.2)
    # Protection requires the forefoot stack: a plate alone gives nothing...
    assert score("protection", plate="rock_plate").spec_score_0_10 is None
    # ...but the stack alone counts: 15 mm under the forefoot = little protection.
    assert score("protection", stack_forefoot_mm=15.0).spec_score_0_10 == pytest.approx(2)
    both = score("protection", plate="rock_plate", stack_forefoot_mm=25.0)
    assert both.spec_score_0_10 == pytest.approx(0.55 * 9 + 0.45 * 6.5)


def test_reviews_without_specs_shrink_towards_neutral() -> None:
    one = score("cushioning", (review(cushioning=8),), midsole_foam="EVA")
    assert one.spec_score_0_10 is None
    assert one.score_0_10 == pytest.approx(5 + (8 - 5) / 3)  # a third of the way from 5
    prior = one.provenance[-1]
    assert prior.input == "neutral_prior" and prior.weight == pytest.approx(2 / 3)
    three = score("cushioning", (review(cushioning=8),) * 3)
    assert three.score_0_10 == pytest.approx(8)
    assert [p.input for p in three.provenance] == ["expert_reviews"]


def test_expert_weight_grows_with_the_number_of_reviews() -> None:
    specs = {"lug_depth_mm": 2.5, "outsole_rubber": "Vibram Megagrip"}
    one = score("grip", (review(grip=10),), **specs)
    three = score("grip", (review(grip=10),) * 3, **specs)
    assert one.spec_score_0_10 < one.score_0_10 < three.score_0_10 < 10
    assert three.provenance[-1].weight == pytest.approx(0.5)  # blend 0.5 / 0.5 at 3 reviews


def test_buyer_ratings_are_never_a_criterion_input() -> None:
    result = score("grip", (review(grip=8),), lug_depth_mm=4.0, outsole_rubber="Vibram Megagrip")
    assert {p.source for p in result.provenance} <= {"manufacturer", "lab_measurement",
                                                     "retailer", "expert_reviews"}  # fmt: skip


def test_women_weight_is_used_only_as_fallback_with_its_own_anchors() -> None:
    men = score("lightness", weight_g=230.0)
    women = score("lightness", weight_women_g=200.0)
    assert men.spec_score_0_10 == women.spec_score_0_10 == pytest.approx(8.5)
    assert women.inputs_used == ["specs.weight_women_g"]


# --- monotonicity: a "better" spec never lowers the score ----------------------------


RUBBER = {"outsole_rubber": "Vibram Megagrip"}


@pytest.mark.parametrize(
    ("criterion", "field", "values", "direction", "others"),
    [
        ("grip", "lug_depth_mm", [0.5 * i for i in range(17)], +1, RUBBER),
        ("cushioning", "stack_heel_mm", [15.0 + i for i in range(36)], +1,
         {"stack_forefoot_mm": 24.0}),
        ("protection", "stack_forefoot_mm", [10.0 + i for i in range(30)], +1, {"plate": "none"}),
        ("stability", "stack_heel_mm", [15.0 + i for i in range(36)], -1, {}),
        ("stability", "platform_width_forefoot_mm", [90.0 + i for i in range(40)], +1,
         {"stack_heel_mm": 30.0}),
        ("lightness", "weight_g", [180.0 + 10 * i for i in range(25)], -1, {}),
    ],
)  # fmt: skip
def test_monotonic(
    criterion: str, field: str, values: list[float], direction: int, others: dict
) -> None:
    scores = [score(criterion, **{field: v}, **others).spec_score_0_10 for v in values]
    assert None not in scores
    steps = [direction * (b - a) for a, b in pairwise(scores)]
    assert all(step >= 0 for step in steps), list(zip(values, scores, strict=True))


def test_more_width_options_never_lower_fit_and_deeper_lugs_help_in_mud() -> None:
    widths = [["standard"], ["standard", "wide"], ["narrow", "standard", "wide"]]
    fits = [score("fit_width", width_options=w).spec_score_0_10 for w in widths]
    assert fits == sorted(fits)
    muddy = []
    for depth in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]:
        specs = make_specs(lug_depth_mm=depth)
        muddy.append(terrain_scores(specs, spec_values(specs), CONFIG).muddy_soft.score_0_10)
    assert muddy == sorted(muddy)


# --- terrain (spec §3) --------------------------------------------------------------


def test_terrain_needs_lug_depth() -> None:
    specs = make_specs(outsole_rubber="Vibram Megagrip", stack_heel_mm=30.0)
    terrain = terrain_scores(specs, spec_values(specs), CONFIG)
    assert all(t.score_0_10 is None for t in terrain.__dict__.values())
    specs = make_specs(lug_depth_mm=5.0)
    assert terrain_scores(specs, spec_values(specs), CONFIG).muddy_soft.score_0_10 == pytest.approx(
        8.5
    )


# --- spec resolution: manufacturer > lab > retailer ------------------------------------


def _all_missing(cls, **overrides):
    fields = {}
    for name, info in cls.model_fields.items():
        if name in overrides:
            fields[name] = overrides[name]
        elif isinstance(info.annotation, type) and hasattr(info.annotation, "model_fields"):
            fields[name] = info.annotation(missing_reason=f"{cls.__name__} has no {name}")
    return fields


IDENTITY_FIELDS = {
    "model_id",
    "brand",
    "model",
    "version",
    "manufacturer_url",
    "manufacturer_url_missing_reason",
    "retrieved_at",
    "url_extra_words",
}


def _model_specs(manufacturer: dict, retailer: dict) -> ModelSpecs:
    tags = RetailerTags(**_all_missing(RetailerTags))
    fallback = RetailerFallback(**_all_missing(RetailerFallback, tags=tags, **retailer))
    lab = LabFallback(**_all_missing(LabFallback))
    fields = _all_missing(ModelSpecs, lab_fallback=lab, retailer_fallback=fallback, **manufacturer)
    return ModelSpecs(
        model_id="fictional-shoe", brand="Fictional", model="Shoe", version=None,
        manufacturer_url=None, manufacturer_url_missing_reason="fictional", retrieved_at=None,
        **{k: v for k, v in fields.items() if k not in IDENTITY_FIELDS},
    )  # fmt: skip


def _lab_review(lug_depth: float, match: MatchConfidence, **extra: float) -> CollectedReview:
    lab = {"lug_depth_mm": known(SourcedFloat, lug_depth, "lab")}
    lab |= {key: known(SourcedFloat, value, "lab") for key, value in extra.items()}
    return CollectedReview(
        source="runrepeat", url=URL, title="Fictional test", language="en", date=None,
        retrieved_at=DAY, review_match_confidence=match, match_note="fictional",
        ratings=[], lab_values=lab,
        conclusion_excerpt=None, conclusion_heading=None,
    )  # fmt: skip


def test_source_priority_and_missing_reasons() -> None:
    specs = _model_specs(
        manufacturer={"weight_g": known(SourcedFloat, 280.0, "brand")},
        retailer={"weight_g": known(SourcedFloat, 300.0, "shop"),
                  "lug_depth_mm": known(SourcedFloat, 4.0, "shop")},
    )  # fmt: skip
    lab = [
        _lab_review(5.0, MatchConfidence.VARIANT),
        _lab_review(4.5, MatchConfidence.EXACT, midsole_width_forefoot_mm=112.0),
    ]
    resolved = resolve_specs(specs, lab)
    assert resolved.weight_g.value == 280.0 and resolved.sources["weight_g"] == "manufacturer"
    assert resolved.lug_depth_mm.value == 4.5  # lab beats retailer; exact beats variant
    assert resolved.sources["lug_depth_mm"] == "lab_measurement"
    # RunRepeat's "midsole width" is the platform width of the spec.
    assert resolved.platform_width_forefoot_mm.value == 112.0
    assert resolved.platform_width_heel_mm.value is None
    no_lab = resolve_specs(specs, [])
    assert no_lab.lug_depth_mm.value == 4.0 and no_lab.sources["lug_depth_mm"] == "retailer"
    assert no_lab.stack_heel_mm.value is None
    assert "no RunRepeat lab test" in no_lab.stack_heel_mm.missing_reason


# --- confidence (spec §8) -----------------------------------------------------------


def _offer(reviews: int, day: dt.date = DAY) -> RetailOffer:
    rating = 4.5 if reviews else None
    return RetailOffer(retailer="tradeinn", url=URL, price_eur=100, price_date=day,
                       rating=rating, review_count=reviews)  # fmt: skip


FULL = {"weight_g": 250.0, "stack_heel_mm": 30.0, "stack_forefoot_mm": 24.0, "drop_mm": 6.0,
        "lug_depth_mm": 4.0, "midsole_foam": "EVA", "outsole_rubber": "Vibram",
        "plate": "none", "waterproof": False}  # fmt: skip


def test_confidence_levels() -> None:
    values = spec_values(make_specs(**FULL))
    high = confidence(values, [review(), review()], [_offer(25)], DAY, CONFIG)
    assert high.level == "high" and high.reasons == []
    medium = confidence(values, [review()], [_offer(0)], DAY, CONFIG)
    assert medium.level == "medium"
    assert any("expert review" in r for r in medium.reasons)
    old = confidence(values, [review()], [_offer(0, DAY - dt.timedelta(days=40))], DAY, CONFIG)
    assert old.level == "low" and old.price_age_days == 40
    empty = confidence(spec_values(make_specs()), [], [_offer(0)], DAY, CONFIG)
    assert empty.level == "low" and empty.spec_completeness_0_1 == 0


# --- end to end on the committed interim data ---------------------------------------------


def test_build_on_committed_data_validates_against_the_schemas() -> None:
    from pipeline.build.__main__ import INTERIM, build

    if not (INTERIM / "expert_aspects.json").exists():
        pytest.skip("interim data not built")
    data, meta, _ = build(DAY)  # validates against schema/*.json, raises otherwise
    assert meta["shoe_count"] == len(data["shoes"]) > 0
    for shoe in data["shoes"]:
        for name, criterion in shoe["criteria_scores"].items():
            if criterion["score_0_10"] is None:
                assert criterion["provenance"] == [], name
            else:
                assert sum(p["weight"] for p in criterion["provenance"]) == pytest.approx(
                    1, abs=0.02
                )
    assert Path(INTERIM).exists()
