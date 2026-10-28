"""Phase 3b: retailer-specs fallback rules (no network: pages are given in memory)."""

import datetime as dt
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.models import (
    CanonicalModel,
    Gender,
    ModelSpecs,
    Retailer,
    RetailerListing,
)
from pipeline.specs.__main__ import empty_record
from pipeline.specs.retailer import PageVerifier, build_fallback

GLISSHOP_PAGE = (Path(__file__).parent / "fixtures" / "glisshop" / "product_page.html").read_text(
    encoding="utf-8"
)
TODAY = dt.date(2026, 10, 28)


def tradeinn_page(attrs: dict[str, str]) -> str:
    """A minimal page with Tradeinn's 'Caractéristiques' markup."""
    items = "".join(f"<li><p>{k}</p><p>{v}</p></li>" for k, v in attrs.items())
    return f"<html><body><h1>Shoe</h1><ul>{items}</ul></body></html>"


def listing(
    url: str, attrs: dict, retailer=Retailer.TRADEINN, gender=Gender.MEN
) -> RetailerListing:
    return RetailerListing(
        retailer=retailer,
        product_url=url,
        retailer_product_id="1",
        brand="Example",
        raw_title="Example Shoe 2",
        model_name=None,
        gender_raw=gender.value,
        gender=gender,
        price_eur=100,
        original_price_eur=None,
        in_stock=True,
        rating=None,
        review_count=None,
        category_breadcrumb=[],
        image_url=None,
        attributes=attrs,
        retrieved_at=TODAY,
        missing_reasons={
            k: "test"
            for k in ("model_name", "original_price_eur", "rating", "review_count", "image_url")
        },
    )


def model(offers: list[tuple[str, Gender, dict]]) -> CanonicalModel:
    """A canonical model whose offers are (url, gender, variant flags)."""
    return CanonicalModel.model_validate(
        {
            "id": "example-shoe-2",
            "key": "example|shoe|2",
            "brand": "Example",
            "model": "Shoe",
            "version": "2",
            "category": "trail",
            "gender_variants": ["men"],
            "variants": {},
            "match_confidence": "exact",
            "is_latest_version": None,
            "is_discounted_old_version": False,
            "newer_version_id": None,
            "retailers": ["tradeinn"],
            "offers": [
                {
                    "retailer": "glisshop" if "glisshop" in url else "tradeinn",
                    "url": url,
                    "retailer_product_id": None,
                    "raw_title": "Example Shoe 2",
                    "title_key": "example|shoe|2",
                    "gender": gender.value,
                    "variant": variant,
                    "price_eur": 100,
                    "in_stock": True,
                    "rating": None,
                    "review_count": None,
                    "retrieved_at": "2026-10-28",
                }
                for url, gender, variant in offers
            ],
            "buyer_rating": {
                "review_count_total": 0,
                "raw_mean_0_5": None,
                "bayesian_mean_0_5": None,
                "prior_mean_0_5": 4.3,
                "prior_strength": 20,
            },
            "review_flags": [],
        }
    )


def fallback_for(pages: dict[str, tuple[dict, Gender, dict]], html_override: dict | None = None):
    """Build the fallback of a model whose listings have the given attributes."""
    listings = {url: listing(url, attrs, gender=g) for url, (attrs, g, _) in pages.items()}
    html = {url: tradeinn_page(attrs) for url, (attrs, _, _) in pages.items()} | (
        html_override or {}
    )
    verifier = PageVerifier(lambda retailer, url: html.get(url))
    the_model = model([(url, g, variant) for url, (_, g, variant) in pages.items()])
    return build_fallback(the_model, listings, verifier)


GTX = {"gore_tex": True, "waterproof": True}


def test_exact_values_agreeing_listings_and_snippets() -> None:
    fallback = fallback_for(
        {
            "https://t.com/a/1/p": (
                {"Drop": "8 mm", "Poids": "280 g", "Profondeur de crampon": "4 mm"},
                Gender.MEN,
                {},
            ),
            "https://t.com/b/2/p": ({"Drop": "8 mm", "Poids": "284 g"}, Gender.MEN, {}),
        }
    )
    assert fallback.drop_mm.value == 8.0
    assert "Drop | 8 mm" in fallback.drop_mm.raw_snippet
    assert "retailer, not manufacturer" in fallback.drop_mm.source_name
    assert fallback.weight_g.value == 280.0  # lower median: a value a listing really shows
    assert "range 280-284" in fallback.weight_g.note
    assert fallback.lug_depth_mm.value == 4.0
    assert fallback.drop_range.value is None  # an exact value exists


def test_buckets_are_kept_as_ranges_not_numbers() -> None:
    fallback = fallback_for(
        {
            "https://t.com/a/1/p": (
                {"Drop": "5-8 mm", "Poids des Chaussures": "De 251 g à 300 g"},
                Gender.MEN,
                {},
            )
        }
    )
    assert fallback.drop_mm.value is None and fallback.weight_g.value is None
    assert fallback.drop_range.value == "5-8 mm"
    assert fallback.weight_range.value == "De 251 g à 300 g"


def test_weight_uses_mens_standard_version_only() -> None:
    fallback = fallback_for(
        {
            "https://t.com/a/1/p": ({"Poids": "280 g"}, Gender.MEN, {}),
            "https://t.com/gtx/2/p": ({"Poids": "330 g"}, Gender.MEN, GTX),
            "https://t.com/w/3/p": ({"Poids": "240 g"}, Gender.WOMEN, {}),
        }
    )
    assert fallback.weight_g.value == 280.0
    assert fallback.weight_women_g.value == 240.0


def test_disagreeing_weights_give_null_with_reason() -> None:
    fallback = fallback_for(
        {
            "https://t.com/a/1/p": ({"Poids": "260 g"}, Gender.MEN, {}),
            "https://t.com/b/2/p": ({"Poids": "300 g"}, Gender.MEN, {}),
        }
    )
    assert fallback.weight_g.value is None
    assert fallback.weight_g.missing_reason == "retailer listings disagree: 260 to 300"


def test_weight_only_on_other_versions() -> None:
    fallback = fallback_for({"https://t.com/gtx/2/p": ({"Poids": "330 g"}, Gender.MEN, GTX)})
    assert fallback.weight_g.value is None
    assert "only other versions" in fallback.weight_g.missing_reason


def test_explicit_no_is_kept_for_waterproof_and_plate() -> None:
    fallback = fallback_for(
        {
            "https://t.com/a/1/p": (
                {"Imperméable": "Non", "Plaque de protection": "Non"},
                Gender.MEN,
                {},
            )
        }
    )
    assert fallback.waterproof.value is False
    assert fallback.plate.value == "none"


def test_value_missing_from_the_cached_page_is_rejected() -> None:
    fallback = fallback_for(
        {"https://t.com/a/1/p": ({"Drop": "8 mm"}, Gender.MEN, {})},
        html_override={"https://t.com/a/1/p": "<html><body>nothing here</body></html>"},
    )
    assert fallback.drop_mm.value is None
    assert fallback.drop_mm.missing_reason == "value not found again in the cached retailer page"


def test_junk_names_are_rejected() -> None:
    fallback = fallback_for(
        {
            "https://t.com/a/1/p": (
                {"Technologie de la semelle intermédiaire": "Zéro Drop"},
                Gender.MEN,
                {},
            )
        }
    )
    assert fallback.midsole_foam.value is None


def test_womens_weight_identical_to_mens_is_flagged() -> None:
    fallback = fallback_for(
        {
            "https://t.com/a/1/p": ({"Poids": "270 g"}, Gender.MEN, {}),
            "https://t.com/w/2/p": ({"Poids": "270 g"}, Gender.WOMEN, {}),
        }
    )
    assert "identical to the men's value" in fallback.weight_women_g.note


def test_glisshop_tags_are_verified_in_the_embedded_json() -> None:
    url = "https://www.glisshop.com/chaussures-trail/example/shoe90000001"
    attrs = {"Terrain": "Sentiers accidentés, Chemin", "Distance": "Longue et ultra"}
    glisshop_listing = listing(url, attrs, retailer=Retailer.GLISSHOP)
    verifier = PageVerifier(lambda retailer, u: GLISSHOP_PAGE)
    fallback = build_fallback(model([(url, Gender.MEN, {})]), {url: glisshop_listing}, verifier)
    assert fallback.tags.terrain.value == "Sentiers accidentés, Chemin"
    assert fallback.tags.terrain.raw_snippet == "Terrain: Sentiers accidentés, Chemin"
    assert "embedded product data" in fallback.tags.terrain.source_name


def test_fallback_values_also_need_snippets() -> None:
    fallback = fallback_for({"https://t.com/a/1/p": ({"Drop": "8 mm"}, Gender.MEN, {})})
    record = empty_record(model([("https://t.com/a/1/p", Gender.MEN, {})]), "test")
    data = record.model_copy(update={"retailer_fallback": fallback}).model_dump()
    data["retailer_fallback"]["drop_mm"]["raw_snippet"] = None
    with pytest.raises(ValidationError, match=r"retailer_fallback\.drop_mm"):
        ModelSpecs.model_validate(data)
