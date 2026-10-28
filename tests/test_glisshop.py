"""Offline tests of the Glisshop parsers, on hand-written fixtures (no network)."""

import datetime as dt
from pathlib import Path

import pytest

from pipeline.collect import glisshop
from pipeline.models import Gender

FIXTURES = Path(__file__).parent / "fixtures" / "glisshop"
TODAY = dt.date(2026, 10, 28)


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("text", "expected"), [(" 159,90 € ", 159.9), ("89,90 €", 89.9), ("", None)]
)
def test_parse_price(text: str, expected: float | None) -> None:
    assert glisshop.parse_price(text) == expected


def test_category_page_cards_and_next_link() -> None:
    cards, next_url = glisshop.parse_category_page(read("category_page.html"))
    assert next_url.endswith("/homme/?pageNumber-10=2")
    assert len(cards) == 2  # the advertising block is not a card
    first, second = cards
    assert first.brand == "Example Brand"
    assert first.title == "Chaussures de trail Fictional Trail 2 Sunset Ocean Blue"
    assert (first.price_eur, first.original_price_eur) == (89.9, 159.9)
    # The product's own rating, not the shop-wide 4.8 / 18822 of the page JSON-LD.
    assert (first.rating, first.review_count) == (4.6, 12)
    assert first.image_url == "https://images.example.com/90000001_0.jpeg"
    assert second.rating is None and second.original_price_eur is None
    assert second.price_eur == 140.0


def test_product_details_give_the_model_name_without_colour() -> None:
    details = glisshop.parse_product_details(read("product_page.html"))
    assert details.model_name == "Fictional Trail 2"
    assert details.gender_raw == "Homme"
    assert details.attributes == {
        "Type": "Chaussures de trail",
        "Terrain": "Sentiers accidentés, Chemin",
        "Distance": "Longue et ultra",
        "Genre": "Homme",
    }  # advice text and promotions are not in the whitelist


def test_page_without_product_json_is_an_error() -> None:
    with pytest.raises(ValueError, match="no product data"):
        glisshop.parse_product_details("<html></html>")


def test_build_listing_with_details() -> None:
    card = glisshop.parse_category_page(read("category_page.html"))[0][0]
    details = glisshop.parse_product_details(read("product_page.html"))
    listing = glisshop.build_listing(card, details, TODAY, "")
    assert listing.retailer_product_id == "90000001"
    assert listing.model_name == "Fictional Trail 2"
    assert listing.gender is Gender.MEN
    assert listing.in_stock is None
    assert set(listing.missing_reasons) == {"in_stock"}


def test_build_listing_falls_back_on_the_categories() -> None:
    card = glisshop.parse_category_page(read("category_page.html"))[0][1]
    card.category_genders = {"Homme", "Femme"}
    listing = glisshop.build_listing(card, None, TODAY, "product page unusable: timeout")
    assert listing.gender is Gender.UNISEX
    assert listing.gender_raw == "Femme, Homme"
    assert listing.model_name is None
    assert listing.missing_reasons["model_name"] == "product page unusable: timeout"
    assert {"rating", "review_count", "original_price_eur", "image_url"} <= set(
        listing.missing_reasons
    )


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Homme", Gender.MEN),
        ("Femme", Gender.WOMEN),
        ("Homme, Femme", Gender.UNISEX),
        ("Mixte", Gender.UNISEX),
        ("Enfant", None),
    ],
)
def test_gender_labels(label: str, expected: Gender | None) -> None:
    assert glisshop._gender(label) is expected


def test_traction_overshoes_are_not_shoes() -> None:
    card = glisshop.parse_category_page(read("category_page.html"))[0][0]
    assert glisshop.is_shoe(card, None)
    card.title = "Semelle Antidérapante Ice Grip Grey"
    assert not glisshop.is_shoe(card, None)
    details = glisshop.ProductDetails("Ice Grip", None, {"Type": "Semelle Antidérapante"})
    assert not glisshop.is_shoe(card, details)
