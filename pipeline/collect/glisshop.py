"""Collector for Glisshop (glisshop.com), French site.

Method (see docs/sources.md): server-rendered HTML.

* Category pages (men's, women's, gravel) list 24 product cards per page, with brand,
  title, price, recommended price, rating and review count. Pages are followed through
  their `rel="next"` link.
* Each product page embeds a JSON object (`window.__change[...] = {...}`) that gives the
  model name WITHOUT the colour ("Prodigio" for "Prodigio Yellow Black"), the gender and
  a few short facts (terrain, distance, foot width). Glisshop titles contain marketing
  colour names, so this clean model name is what phase 2 parses.
"""

import datetime as dt
import json
import logging
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from pipeline.collect.common import CollectResult
from pipeline.models import Gender, Retailer, RetailerListing
from pipeline.utils.http import AccessBlockedError, CachedResponse, PoliteClient

log = logging.getLogger(__name__)

SITE = "glisshop"
BASE_URL = "https://www.glisshop.com"
TRAIL_SHOES_URL = f"{BASE_URL}/trail-running/chaussures-trail"
# (entry URL, gender label of the category or None, breadcrumb we record)
CATEGORIES = [
    (f"{TRAIL_SHOES_URL}/homme/", "Homme", ["Trail running", "Chaussures trail", "Homme"]),
    (f"{TRAIL_SHOES_URL}/femme/", "Femme", ["Trail running", "Chaussures trail", "Femme"]),
    (
        f"{BASE_URL}/trail-running/chaussures-gravel-running/",
        None,
        ["Trail running", "Chaussures gravel running"],
    ),
]
MAX_PAGES_PER_CATEGORY = 50  # safety stop if pagination ever loops

GENDER_LABELS = {
    "homme": Gender.MEN,
    "femme": Gender.WOMEN,
    "mixte": Gender.UNISEX,
    "unisexe": Gender.UNISEX,
}

# Product facts we keep (technical name -> label). A whitelist, so promotions and
# advice texts in the same JSON are never stored.
KEPT_ATTRIBUTES = {
    "glis_char_typology": "Type",
    "glis_char_terrain": "Terrain",
    "GLIS_CHAR_TRAIL_DISTANCE": "Distance",
    "glis_char_ski_boot_foot_width": "Largeur de pied",
    "GLIS_CHAR_USER_WEIGHT": "Gabarit",
    "GLIS_CHAR_PACE": "Allure",
}


@dataclass
class GlisshopCard:
    """One product card of a category page."""

    url: str
    title: str
    brand: str | None
    price_eur: float | None
    original_price_eur: float | None
    rating: float | None
    review_count: int | None
    image_url: str | None
    category_genders: set[str] = field(default_factory=set)
    breadcrumb: list[str] = field(default_factory=list)


@dataclass
class ProductDetails:
    """What the embedded JSON of a product page tells us."""

    model_name: str | None
    gender_raw: str | None
    attributes: dict[str, str]


# ---------------------------------------------------------------------------
# Parsers (pure functions of the HTML, tested offline in tests/test_glisshop.py)
# ---------------------------------------------------------------------------


def parse_price(text: str) -> float | None:
    """Turn '159,90 €' into 159.9; None if there is no number."""
    cleaned = text.replace("€", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _text(node) -> str | None:
    return node.get_text(" ", strip=True) if node else None


def parse_category_page(html: str) -> tuple[list[GlisshopCard], str | None]:
    """Return the product cards of a category page and the URL of the next page."""
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    for item in soup.select("div.product-list-item"):
        link = item.select_one(".product-label a[href]")
        title = _text(item.select_one(".product-label_title"))
        if link is None or not title:
            continue
        rating = review_count = None
        stars = item.select_one("span.reviews[title]")
        match = re.search(r"([\d.,]+)\s*sur\s*(\d+)", stars["title"]) if stars else None
        if match:
            value, scale = float(match.group(1).replace(",", ".")), float(match.group(2))
            rating = round(value / scale * 5, 2)
            count = re.search(r"\d+", _text(item.select_one(".reviews .btn_link")) or "")
            review_count = int(count.group()) if count else None
        current = _text(item.select_one(".price-value"))
        advised = _text(item.select_one(".advice-price__price"))
        image = item.select_one("img[data-lazy]")
        cards.append(
            GlisshopCard(
                url=link["href"],
                title=title,
                brand=_text(item.select_one(".product-brand span")),
                price_eur=parse_price(current) if current else None,
                original_price_eur=parse_price(advised) if advised else None,
                rating=rating,
                review_count=review_count,
                image_url=image["data-lazy"] if image else None,
            )
        )
    next_link = soup.find("link", rel="next")
    return cards, (next_link["href"] if next_link else None)


def _embedded_objects(html: str):
    """Yield the JSON objects assigned to window.__change[...] in the page."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"window\.__change\['\d+'\]\s*=\s*", html):
        try:
            obj, _ = decoder.raw_decode(html, match.end())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def _attribute_text(attribute: dict) -> str | None:
    """Readable value of one typology attribute (single or multiple values)."""
    formatted = (attribute.get("formattedValue") or {}).get("common", {})
    if isinstance(formatted, dict) and formatted.get("title"):
        return formatted["title"]
    values = attribute.get("value")
    if isinstance(values, list):
        titles = [v.get("common", {}).get("title") for v in values if isinstance(v, dict)]
        return ", ".join(t for t in titles if t) or None
    return None


def parse_product_details(html: str) -> ProductDetails:
    """Model name without colour, gender and short facts from a product page."""
    for obj in _embedded_objects(html):
        root = obj.get("rootProduct")
        if not isinstance(root, dict):
            continue
        attributes_json = (obj.get("typology") or root.get("typology") or {}).get("attributes", {})
        attributes = {}
        for technical_name, label in KEPT_ATTRIBUTES.items():
            value = _attribute_text(attributes_json.get(technical_name) or {})
            if value and len(value) <= 80:
                attributes[label] = value
        gender = _attribute_text(attributes_json.get("glis_char_gender") or {})
        if gender:
            attributes["Genre"] = gender
        return ProductDetails(
            model_name=(root.get("common") or {}).get("title"),
            gender_raw=gender,
            attributes=attributes,
        )
    raise ValueError("no product data (window.__change with rootProduct) in the page")


def _gender(label: str | None) -> Gender | None:
    """'Homme' -> men; 'Homme, Femme' (sold for both) -> unisex."""
    if not label:
        return None
    genders = {GENDER_LABELS.get(part.strip().lower()) for part in label.split(",")} - {None}
    if genders == {Gender.MEN, Gender.WOMEN}:
        return Gender.UNISEX
    return genders.pop() if len(genders) == 1 else None


def build_listing(
    card: GlisshopCard, details: ProductDetails | None, retrieved_at: dt.date, details_error: str
) -> RetailerListing:
    """Combine a card and (if available) its product page into a RetailerListing."""
    missing = {"in_stock": "not shown on Glisshop listing cards"}
    if details and details.gender_raw:
        gender_raw = details.gender_raw
        gender = _gender(gender_raw)
    elif card.category_genders:
        # No product page data: fall back on the category the card was listed in.
        gender_raw = ", ".join(sorted(card.category_genders))
        gender = _gender(gender_raw)
    else:
        gender_raw = gender = None
        missing["gender_raw"] = "not in a gendered category and no product page data"
    model_name = details.model_name if details else None
    if not model_name:
        missing["model_name"] = details_error or "product page gives no model name"
    if card.original_price_eur is None:
        missing["original_price_eur"] = "no recommended price shown (not discounted)"
    if card.rating is None:
        missing["rating"] = missing["review_count"] = "no review shown on the card"
    for name in ("brand", "price_eur", "image_url"):
        if getattr(card, name) is None:
            missing[name] = "not found on the listing card"
    id_match = re.search(r"(\d+)$", card.url.rstrip("/"))
    if not id_match:
        missing["retailer_product_id"] = "no numeric id at the end of the URL"
    return RetailerListing(
        retailer=Retailer.GLISSHOP,
        product_url=card.url,
        retailer_product_id=id_match.group(1) if id_match else None,
        brand=card.brand,
        raw_title=card.title,
        model_name=model_name,
        gender_raw=gender_raw,
        gender=gender,
        price_eur=card.price_eur,
        original_price_eur=card.original_price_eur,
        in_stock=None,
        rating=card.rating,
        review_count=card.review_count,
        category_breadcrumb=card.breadcrumb,
        image_url=card.image_url,
        attributes=details.attributes if details else {},
        retrieved_at=retrieved_at,
        missing_reasons=missing,
    )


def is_shoe(card: GlisshopCard, details: ProductDetails | None) -> bool:
    """False for the traction overshoes ("Semelle Antidérapante") listed with trail shoes."""
    product_type = (details.attributes.get("Type") if details else None) or card.title
    return "chaussure" in product_type.lower()


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------


def _get(client: PoliteClient, url: str) -> CachedResponse:
    page = client.get(url)
    if page.status != 200:
        raise RuntimeError(f"HTTP {page.status}")
    return page


def collect(client: PoliteClient, limit: int | None = None) -> CollectResult:
    """Collect every trail and gravel shoe. `limit` caps product pages (for quick tests)."""
    result = CollectResult()
    cards: dict[str, GlisshopCard] = {}
    retrieved: dict[str, dt.date] = {}

    for entry_url, gender_label, breadcrumb in CATEGORIES:
        url, pages = entry_url, 0
        while url and pages < MAX_PAGES_PER_CATEGORY:
            try:
                page = _get(client, url)
            except AccessBlockedError:
                raise  # the site refuses us: stop, never work around it
            except Exception as error:  # recorded; the other categories continue
                result.failures.append({"url": url, "error": f"fetch: {error}"})
                break
            pages += 1
            result.category_pages += 1
            page_cards, url = parse_category_page(page.text)
            for card in page_cards:
                known = cards.setdefault(card.url, card)
                if not known.breadcrumb:
                    known.breadcrumb = breadcrumb
                if gender_label:
                    known.category_genders.add(gender_label)
                retrieved.setdefault(card.url, page.retrieved_at)
                if card.brand:
                    result.brands_seen.add(card.brand)
            log.info("%s: %d cards", page.url, len(page_cards))

    for index, card in enumerate(cards.values()):
        details, error = None, ""
        if limit is None or index < limit:
            try:
                details = parse_product_details(_get(client, card.url).text)
            except AccessBlockedError:
                raise
            except Exception as exc:  # the card alone is still a valid listing
                error = f"product page unusable: {exc}"
        else:
            error = "product page not fetched (--limit)"
        if not is_shoe(card, details):
            result.excluded_not_trail.append(card.url)
            continue
        try:
            result.listings.append(build_listing(card, details, retrieved[card.url], error))
        except Exception as exc:  # one bad card must not stop the crawl
            result.failures.append({"url": card.url, "error": f"parse: {exc}"})

    log.info(
        "glisshop: %d listings, %d failures, %d category pages",
        len(result.listings),
        len(result.failures),
        result.category_pages,
    )
    return result
