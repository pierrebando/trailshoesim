"""Matching, human review, versions, Bayesian ratings and the phase 2 pipeline."""

import datetime as dt
from pathlib import Path

import pytest

from pipeline.models import Gender, ModelOffer, Retailer, RetailerListing, VariantFlags
from pipeline.normalize.__main__ import _mark_versions, build, parse_listing, slugify
from pipeline.normalize.apply_review import load_decisions, write_review_csv
from pipeline.normalize.matching import (
    Decision,
    flag_proposals,
    fuzzy_proposals,
    resolve,
)
from pipeline.normalize.ratings import bayesian_summary, rating_pairs
from pipeline.normalize.versions import version_order

COUNTS = {
    "ua|charged bandit tr|3": 3,
    "ua|charged bandit|3": 1,
    "ls|prodigio pro|": 2,
    "ls|prodigio|": 2,
    "nb|dynasoft nitrel|6": 4,
    "nb|dynasoft nitrell|6": 1,  # typo: should be merged automatically
    "hoka|speedgoat|6": 1,
    "hoka|speedgoat|5": 1,
}


def _by_keys(proposals):
    # Proposal keys are stored sorted; look them up as sets to ignore the order.
    return {frozenset(proposal.keys): proposal for proposal in proposals}


def test_fuzzy_proposals_are_conservative() -> None:
    proposals = _by_keys(fuzzy_proposals(COUNTS, merge_threshold=92, review_threshold=80))
    typo = proposals[frozenset({"nb|dynasoft nitrel|6", "nb|dynasoft nitrell|6"})]
    assert typo.applied_by_default and typo.proposed_key == "nb|dynasoft nitrel|6"
    bandit = proposals[frozenset({"ua|charged bandit tr|3", "ua|charged bandit|3"})]
    assert bandit.reason == "possible_duplicate" and not bandit.applied_by_default
    assert not proposals[frozenset({"ls|prodigio pro|", "ls|prodigio|"})].applied_by_default
    # Different versions are never compared.
    assert frozenset({"hoka|speedgoat|5", "hoka|speedgoat|6"}) not in proposals


def test_resolve_applies_defaults_and_decisions() -> None:
    proposals = fuzzy_proposals(COUNTS, 92, 80)
    final_of, fuzzy = resolve(COUNTS, proposals, {})
    assert final_of["nb|dynasoft nitrell|6"] == "nb|dynasoft nitrel|6"
    assert "nb|dynasoft nitrel|6" in fuzzy
    assert final_of["ua|charged bandit|3"] == "ua|charged bandit|3"  # not merged by default

    ids = {key: p.review_id for key, p in _by_keys(proposals).items()}
    decisions = {
        ids[frozenset({"nb|dynasoft nitrel|6", "nb|dynasoft nitrell|6"})]: Decision("x", "split"),
        ids[frozenset({"ua|charged bandit tr|3", "ua|charged bandit|3"})]: Decision(
            "y", "rename", "ua|charged bandit trail|3"
        ),
    }
    final_of, _ = resolve(COUNTS, proposals, decisions)
    assert final_of["nb|dynasoft nitrell|6"] == "nb|dynasoft nitrell|6"  # split
    assert final_of["ua|charged bandit|3"] == "ua|charged bandit trail|3"  # renamed
    assert final_of["ua|charged bandit tr|3"] == "ua|charged bandit trail|3"


def test_version_unknown_is_flagged_not_merged() -> None:
    counts = {"s|speedcross|": 2, "s|speedcross|6": 1, "s|speedcross|5": 1}
    (flag,) = flag_proposals(counts, {})
    assert flag.reason == "version_unknown" and flag.proposed_key == "s|speedcross|6"
    assert not flag.applied_by_default


def test_review_csv_round_trip_keeps_decisions(tmp_path: Path) -> None:
    proposals = fuzzy_proposals(COUNTS, 92, 80)
    path = tmp_path / "needs_review.csv"
    write_review_csv(path, proposals, {}, {}, {})
    first_id = proposals[0].review_id

    # Simulate the owner typing "split" in the decision column of one row.
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    row = next(i for i, line in enumerate(lines) if line.startswith(first_id))
    cells = lines[row].split(",")
    cells[header.index("decision")] = "split"
    lines[row] = ",".join(cells)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    decisions = load_decisions(path)
    assert decisions[first_id].decision == "split"
    write_review_csv(path, proposals, {}, {}, decisions)  # regenerated...
    assert load_decisions(path)[first_id].decision == "split"  # ...decision survives


def test_invalid_decision_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "needs_review.csv"
    path.write_text("review_id,decision,rename_to\nabc,merge,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown decision"):
        load_decisions(path)


def test_version_order() -> None:
    assert sorted(["9+", "2", "10", "9", "6.5"], key=version_order) == ["2", "6.5", "9", "9+", "10"]


def _offer(price: float, rating=None, count=None, retailer=Retailer.TRADEINN) -> ModelOffer:
    return ModelOffer(
        retailer=retailer,
        url=f"https://example.com/{price}-{rating}-{count}",
        retailer_product_id=None,
        raw_title="t",
        title_key="k",
        gender=None,
        variant=VariantFlags(),
        price_eur=price,
        in_stock=True,
        rating=rating,
        review_count=count,
        retrieved_at=dt.date(2026, 10, 28),
    )


def test_old_version_on_sale_is_flagged() -> None:
    models = [
        {"key": "h|speedgoat|5", "id": "h-speedgoat-5", "version": "5", "offers": [_offer(99)]},
        {"key": "h|speedgoat|6", "id": "h-speedgoat-6", "version": "6", "offers": [_offer(149)]},
        {"key": "h|speedgoat|", "id": "h-speedgoat", "version": None, "offers": [_offer(120)]},
    ]
    _mark_versions(models)
    old, new, unknown = models
    assert new["is_latest_version"] is True
    assert old["is_latest_version"] is False and old["is_discounted_old_version"] is True
    assert old["newer_version_id"] == "h-speedgoat-6"
    assert unknown["is_latest_version"] is None  # version unknown: no guess


def test_bayesian_average_matches_the_spec_example() -> None:
    assert bayesian_summary([(5.0, 3)], prior_mean=4.3).bayesian_mean_0_5 == 4.391
    assert bayesian_summary([(4.6, 200)], prior_mean=4.3).bayesian_mean_0_5 == 4.573
    empty = bayesian_summary([], prior_mean=4.3)
    assert empty.review_count_total == 0 and empty.bayesian_mean_0_5 is None


def test_identical_rating_pairs_at_one_retailer_count_once() -> None:
    offers = [_offer(100, 4.0, 12), _offer(101, 4.0, 12), _offer(102, 5.0, 2), _offer(103)]
    assert rating_pairs(offers) == [(4.0, 12), (5.0, 2)]


def test_slugify() -> None:
    assert slugify("altra|lone peak|9+") == "altra-lone-peak-9-plus"
    assert slugify("la sportiva|bushido|3") == "la-sportiva-bushido-3"


def _listing(
    title: str,
    gender: Gender | None,
    price: float,
    in_stock: bool = True,
    gender_raw: str | None = None,
    retailer: Retailer = Retailer.TRADEINN,
    model_name: str | None = None,
    brand: str = "Example",
    attributes: dict | None = None,
):
    return RetailerListing(
        retailer=retailer,
        product_url=f"https://example.com/{abs(hash((title, gender, price, retailer)))}/p",
        retailer_product_id="1",
        brand=brand,
        raw_title=title,
        model_name=model_name,
        attributes=attributes or {},
        gender_raw=gender_raw or (gender.value if gender else None),
        gender=gender,
        price_eur=price,
        original_price_eur=None,
        in_stock=in_stock,
        rating=4.0,
        review_count=10,
        category_breadcrumb=["Chaussures trail running"],
        image_url=None,
        retrieved_at=dt.date(2026, 10, 28),
        missing_reasons={
            "original_price_eur": "test",
            "image_url": "test",
            **({} if model_name else {"model_name": "test"}),
            **({} if gender or gender_raw else {"gender_raw": "test"}),
        },
    )


def test_build_merges_genders_into_one_model(tmp_path: Path) -> None:
    listings = [
        _listing("Salomon Speedcross 6", Gender.MEN, 130),
        _listing("Salomon Speedcross 6 GORE-TEX®", Gender.WOMEN, 150),
        _listing("Salomon Speedcross 5", Gender.MEN, 90),
        _listing("Salomon Speedcross 6 Junior", None, 70),  # kids (title): dropped
        _listing("Salomon Speedcross 6", None, 75, gender_raw="Garçon"),  # kids (label): dropped
        _listing("Salomon Genesis 2", Gender.MEN, 140, in_stock=False),  # not on sale
    ]
    result = build(listings, tmp_path / "needs_review.csv")
    models = {model.key: model for model in result.catalog.models}
    assert set(models) == {"salomon|speedcross|6", "salomon|speedcross|5"}
    latest = models["salomon|speedcross|6"]
    assert latest.gender_variants == [Gender.MEN, Gender.WOMEN]
    assert latest.variants.gore_tex and latest.is_latest_version
    assert models["salomon|speedcross|5"].is_discounted_old_version
    assert result.report["dropped"] == {"kids": 2, "not_in_stock": 1}


def test_clean_model_name_beats_a_title_full_of_colours() -> None:
    listing = _listing(
        "Chaussures de trail Xa Pro 3D V9 Gore-Tex Turbulence Black Burnt Ochre",
        Gender.MEN,
        139.9,
        retailer=Retailer.GLISSHOP,
        model_name="Xa Pro 3D V9 Gore-Tex",
        brand="Salomon",
    )
    parsed = parse_listing(listing)
    assert parsed.key == "salomon|xa pro 3d|9"
    assert {"gore_tex", "waterproof"} <= parsed.variants


def test_gravel_from_retailer_facts() -> None:
    listing = _listing(
        "Chaussures Wave Rider TT 3",
        Gender.MEN,
        74.9,
        model_name="Wave Rider TT 3",
        brand="Mizuno",
        attributes={"Type": "Chaussures Gravel Running"},
    )
    assert parse_listing(listing).category == "gravel"


def test_unknown_brand_from_the_retailer_field_is_trusted() -> None:
    listing = _listing("Speedster 3", Gender.MEN, 99, brand="Brandnew")
    parsed = parse_listing(listing)
    assert parsed.key == "brandnew|speedster|3"
    assert "brand 'Brandnew' is not in brands.yaml" in parsed.warnings


def test_same_model_at_two_retailers_is_one_model(tmp_path: Path) -> None:
    listings = [
        _listing(
            "Salomon Chaussures de trail running XA Pro 3D V9 GORE-TEX®",
            Gender.MEN,
            150,
            brand="Salomon",
        ),
        _listing(
            "Chaussures de trail Xa Pro 3D V9 Gore-Tex Turbulence Black Burnt Ochre",
            Gender.WOMEN,
            139.9,
            retailer=Retailer.GLISSHOP,
            model_name="Xa Pro 3D V9 Gore-Tex",
            brand="Salomon",
        ),
    ]
    result = build(listings, tmp_path / "needs_review.csv")
    (model,) = result.catalog.models
    assert model.retailers == [Retailer.GLISSHOP, Retailer.TRADEINN]  # sorted by name
    assert model.gender_variants == [Gender.MEN, Gender.WOMEN]
    assert result.report["models_by_retailer_count"] == {2: 1}
