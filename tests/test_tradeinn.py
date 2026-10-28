"""Offline tests of the Tradeinn parsers, on hand-written fixtures (no network)."""

import datetime as dt
from pathlib import Path

import pytest

from pipeline.collect import tradeinn
from pipeline.models import Gender

FIXTURES = Path(__file__).parent / "fixtures" / "tradeinn"
TODAY = dt.date(2026, 10, 28)
PRODUCT_URL = (
    "https://www.tradeinn.com/runnerinn/fr/"
    "example-brand-chaussures-de-trail-running-fictional-trail-1/100000002/p"
)


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("text", "expected"),
    [(" 159.49 €", 159.49), ("1 234,50 €", 1234.5), ("140 €", 140.0), ("—", None)],
)
def test_parse_price(text: str, expected: float | None) -> None:
    assert tradeinn.parse_price(text) == expected


def test_listing_cards_come_from_the_main_grid_only() -> None:
    cards = tradeinn.parse_listing_cards(read("listing_page.html"))
    assert [card.url.rsplit("/", 2)[1] for card in cards] == ["100000002", "100000003"]
    first, second = cards
    assert first.title == "Example Brand Chaussures de trail running Fictional Trail 1"
    assert first.price_eur == 149.99
    assert second.price_eur == 1234.5
    assert second.url.startswith("https://www.tradeinn.com/runnerinn/fr/")  # made absolute
    assert second.image_url == "https://www.tradeinn.com/h/10000/100000003/imaginary-pro.webp"


def test_brand_links_are_found() -> None:
    assert tradeinn.parse_brand_ids(read("listing_page.html")) == {
        "9001": "example-brand",
        "9002": "other-brand",
    }
    assert tradeinn.parse_brand_trail_link(read("product_page.html")) == ("example-brand", "9001")
    assert tradeinn.brand_trail_url("example-brand", "9001").endswith(
        "/chaussures-chaussures-trail-running/example-brand/10005-9001/sm"
    )


def test_product_page_full() -> None:
    card = tradeinn.parse_listing_cards(read("listing_page.html"))[0]
    listing = tradeinn.parse_product_page(read("product_page.html"), PRODUCT_URL, TODAY, card)

    assert listing.retailer_product_id == "100000002"
    assert listing.brand == "Example brand"
    assert listing.raw_title == card.title
    assert listing.gender_raw == "Femme" and listing.gender is Gender.WOMEN
    # Lowest IN-STOCK variant price, not the cheaper out-of-stock size.
    assert listing.price_eur == 152.49 and listing.in_stock is True
    # Product rating (not the shop-wide Organization rating). bestRating == ratingValue on
    # Tradeinn, so it must not be used as the scale maximum.
    assert listing.rating == 4.0 and listing.review_count == 13
    assert listing.category_breadcrumb == ["Accueil", "Chaussures", "Chaussures trail running"]
    assert listing.attributes == {
        "Drop": "5-8 mm",
        "Genre": "Femme",
        "Largeur des Chaussures": "Standard",
    }  # the long description is not stored
    assert listing.original_price_eur is None
    assert set(listing.missing_reasons) == {"original_price_eur", "model_name"}


def test_product_page_sparse_explains_every_missing_value() -> None:
    listing = tradeinn.parse_product_page(
        read("product_page_sparse.html"),
        "https://www.tradeinn.com/runnerinn/fr/nameless-shoe/100000009/p",
        TODAY,
    )
    assert listing.raw_title == "Nameless Shoe"
    assert listing.in_stock is False
    assert listing.price_eur is None
    assert listing.original_price_eur == 120.0
    assert listing.rating is None and listing.review_count is None
    assert set(listing.missing_reasons) == {
        "brand",
        "model_name",
        "gender_raw",
        "price_eur",
        "rating",
        "review_count",
        "image_url",
    }


@pytest.mark.parametrize(
    ("aggregate", "expected"),
    [
        ({"ratingValue": "4", "bestRating": "4"}, 4.0),  # Tradeinn style
        ({"ratingValue": "4.6"}, 4.6),
        ({"ratingValue": "9", "bestRating": "10"}, 4.5),  # another scale, announced
    ],
)
def test_rating_scale(aggregate: dict, expected: float) -> None:
    assert tradeinn._rating_0_5(aggregate) == expected


def test_default_rating_without_any_review_is_ignored() -> None:
    html = read("product_page.html").replace(
        '"review": [{"@type": "Review", "reviewRating": {"@type": "Rating", "ratingValue": "4"}}],',
        "",
    )
    listing = tradeinn.parse_product_page(html, PRODUCT_URL, TODAY)
    assert listing.rating is None and listing.review_count is None
    assert listing.missing_reasons["rating"] == tradeinn.PLACEHOLDER_RATING


def test_page_without_product_data_is_a_parse_error() -> None:
    with pytest.raises(ValueError, match=r"no schema\.org Product"):
        tradeinn.parse_product_page("<html></html>", PRODUCT_URL, TODAY)


@pytest.mark.parametrize(
    ("breadcrumb", "expected"),
    [
        (["Accueil", "Chaussures", "Chaussures trail running"], True),
        (["Accueil", "Vêtements", "T-shirts"], False),
        ([], True),
    ],
)
def test_trail_breadcrumb_filter(breadcrumb: list[str], expected: bool) -> None:
    assert tradeinn.is_trail_breadcrumb(breadcrumb) is expected
