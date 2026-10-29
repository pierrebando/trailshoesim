"""Collector for Tradeinn's running store (Runnerinn), French site.

Method (see docs/sources.md): server-rendered HTML + schema.org JSON-LD.

* Category pages list up to 96 product cards (title, price, URL, image).
* Product pages give brand, product rating, review count, per-size prices, breadcrumb
  and a "Caractéristiques" list (gender, width, drop range...).

The "load more" button of category pages calls an internal search backend that we
deliberately do not use. Coverage comes from two server-rendered sources instead:
* one brand x trail page per brand, the brands being read from the store's brand links
  (homepage and the brand menu of every category page);
* the links to other trail shoes that every product page shows ("you may also like",
  other colours), followed until no new product appears.
"""

import datetime as dt
import json
import logging
import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from bs4 import BeautifulSoup

from pipeline.collect.common import CollectResult
from pipeline.models import Gender, Retailer, RetailerListing
from pipeline.utils.http import AccessBlockedError, CachedResponse, PoliteClient

log = logging.getLogger(__name__)

SITE = "tradeinn"
BASE_URL = "https://www.tradeinn.com"
STORE_URL = f"{BASE_URL}/runnerinn/fr"
TRAIL_SUBFAMILY_ID = "10005"
TRAIL_CATEGORY_URL = f"{STORE_URL}/chaussures-chaussures-trail-running/{TRAIL_SUBFAMILY_ID}/s"
MAX_CARDS_PER_PAGE = 96  # server-side page size; a page this full may be truncated

GENDER_LABELS = {
    "homme": Gender.MEN,
    "femme": Gender.WOMEN,
    "unisexe": Gender.UNISEX,
    "unisex": Gender.UNISEX,
}

ORIGINAL_PRICE_MISSING = "not in the server-rendered HTML (filled in by JavaScript)"
PLACEHOLDER_RATING = "page shows a default aggregate rating but contains no review"


@dataclass
class ListingCard:
    """One product card of a category page."""

    url: str
    title: str
    price_eur: float | None
    image_url: str | None


# ---------------------------------------------------------------------------
# Parsers (pure functions of the HTML, tested offline in tests/test_tradeinn.py)
# ---------------------------------------------------------------------------


def parse_price(text: str) -> float | None:
    """Turn '159.49 €' or '1 234,50 €' into a float; None if there is no number."""
    cleaned = text.replace("€", "").replace("\xa0", "").replace(" ", "").strip()
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def absolute_url(href: str) -> str:
    """Make a site-relative link absolute."""
    return href if href.startswith("http") else BASE_URL + href


def parse_listing_cards(html: str) -> list[ListingCard]:
    """Return the product cards of the main product grid of a category page."""
    soup = BeautifulSoup(html, "html.parser")
    grid = soup.find(id="js-producto-listado-grid")
    if grid is None:
        return []
    cards = []
    for item in grid.find_all("li", class_="product-listing-wrapper"):
        link = item.find("a", href=re.compile(r"/p$"))
        title = item.find(class_="js-nombre_producto_listado")
        if link is None or title is None:
            continue
        price = item.find(class_="js-precio_producto")
        image = item.find("img", class_="js-image_list_product")
        cards.append(
            ListingCard(
                url=absolute_url(link["href"]),
                title=title.get_text(strip=True),
                price_eur=parse_price(price.get_text()) if price else None,
                image_url=absolute_url(image["src"]) if image and image.get("src") else None,
            )
        )
    return cards


def parse_brand_ids(html: str) -> dict[str, str]:
    """Return {brand_id: brand_slug} from brand links such as /runnerinn/fr/salomon/179/m.

    Both quote styles: the brand menu of category pages writes href='...' (60 brands),
    the homepage href="..." (14 brands); reading only the latter missed Hoka, Nike, On...
    """
    links = re.findall(r"""href=['"]/runnerinn/fr/([a-z0-9\-]+)/(\d+)/m['"]""", html)
    return {brand_id: slug for slug, brand_id in links}


# Tradeinn names every trail-shoe product URL "...chaussures-de-trail-running-...".
TRAIL_PRODUCT_LINK = re.compile(
    r"""href=['"]((?:https://www\.tradeinn\.com)?/runnerinn/fr/"""
    r"""[^'"/]*chaussures-de-trail-running[^'"/]*/\d+/p)['"]"""
)


def parse_trail_product_links(html: str) -> list[str]:
    """Absolute URLs of the trail-shoe product pages linked from a page, in page order."""
    urls = [
        m if m.startswith("http") else f"{BASE_URL}{m}" for m in TRAIL_PRODUCT_LINK.findall(html)
    ]
    return list(dict.fromkeys(urls))


def brand_trail_url(slug: str, brand_id: str) -> str:
    """URL of the trail-shoe category page restricted to one brand."""
    return (
        f"{STORE_URL}/chaussures-chaussures-trail-running/{slug}/{TRAIL_SUBFAMILY_ID}-{brand_id}/sm"
    )


def parse_brand_trail_link(html: str) -> tuple[str, str] | None:
    """Return (slug, brand_id) of the brand x trail link of a product page, if any."""
    match = re.search(
        rf"/runnerinn/fr/chaussures-chaussures-trail-running/([a-z0-9\-]+)/"
        rf"{TRAIL_SUBFAMILY_ID}-(\d+)/sm",
        html,
    )
    return (match.group(1), match.group(2)) if match else None


def _json_ld_blocks(soup: BeautifulSoup) -> list[dict]:
    blocks = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict):
                blocks.append(item)
    return blocks


def _find_product(blocks: list[dict]) -> dict | None:
    for block in blocks:
        entity = block.get("mainEntity", block)
        if isinstance(entity, dict) and entity.get("@type") in ("ProductGroup", "Product"):
            return entity
    return None


def _find_breadcrumb(blocks: list[dict]) -> list[str]:
    for block in blocks:
        crumb = block.get("breadcrumb") if block.get("@type") == "WebPage" else None
        if crumb is None and block.get("@type") == "BreadcrumbList":
            crumb = block
        if crumb:
            return [item["name"].strip() for item in crumb.get("itemListElement", [])]
    return []


def _offers(product: dict) -> list[dict]:
    """All offers of a product group: one per variant, or the group's own offers."""
    offers = []
    for variant in product.get("hasVariant", []) or [product]:
        variant_offers = variant.get("offers", [])
        offers.extend(variant_offers if isinstance(variant_offers, list) else [variant_offers])
    return [offer for offer in offers if isinstance(offer, dict)]


def _parse_attributes(soup: BeautifulSoup) -> dict[str, str]:
    """The 'Caractéristiques' list: <li><p class=txt__uppercase>KEY</p><p class=txt__bold>VALUE."""
    attributes: dict[str, str] = {}
    for item in soup.find_all("li"):
        key = item.find("p", class_="txt__uppercase", recursive=False)
        value = item.find("p", class_="txt__bold", recursive=False)
        if key and value:
            key_text, value_text = key.get_text(strip=True), value.get_text(strip=True)
            # Short facts only: long text would be third-party prose we must not store.
            if key_text and value_text and len(value_text) <= 80:
                attributes.setdefault(key_text, value_text)
    return attributes


def parse_product_page(
    html: str, url: str, retrieved_at: dt.date, card: ListingCard | None = None
) -> RetailerListing:
    """Build a RetailerListing from a product page (and its listing card, if known)."""
    soup = BeautifulSoup(html, "html.parser")
    blocks = _json_ld_blocks(soup)
    product = _find_product(blocks)
    if product is None:
        raise ValueError("no schema.org Product/ProductGroup in the page")

    missing: dict[str, str] = {}
    id_match = re.search(r"/(\d+)/p$", url)

    brand = (product.get("brand") or {}).get("name")
    if not brand:
        missing["brand"] = "no brand in product JSON-LD"

    attributes = _parse_attributes(soup)
    gender_raw = attributes.get("Genre")
    if gender_raw is None:
        missing["gender_raw"] = "no 'Genre' in the product characteristics"
    gender = GENDER_LABELS.get(gender_raw.lower()) if gender_raw else None

    offers = _offers(product)
    in_stock_prices = [
        float(offer["price"])
        for offer in offers
        if "price" in offer and str(offer.get("availability", "")).endswith("InStock")
    ]
    in_stock = bool(in_stock_prices) if offers else None
    if in_stock is None:
        missing["in_stock"] = "no offers in product JSON-LD"
    if in_stock_prices:
        price = min(in_stock_prices)
    elif card and card.price_eur:
        price = card.price_eur  # nothing in stock: keep the price shown on the listing
    else:
        price = None
        missing["price_eur"] = "no in-stock offer and no listing price"

    original_price = None
    old_price_tag = soup.find(id="js-txt_precio_anterior")
    if old_price_tag and old_price_tag.get_text(strip=True):
        original_price = parse_price(old_price_tag.get_text())
    if original_price is None:
        missing["original_price_eur"] = ORIGINAL_PRICE_MISSING

    rating = review_count = None
    aggregate = product.get("aggregateRating")
    if aggregate and not product.get("review"):
        # Observed on 437 of 924 pages: Tradeinn emits "1 review, 4 stars" when a product
        # has no review at all (no review in the page). We do not count that as a rating.
        aggregate = None
        missing["rating"] = missing["review_count"] = PLACEHOLDER_RATING
    if aggregate:
        review_count = int(aggregate.get("reviewCount") or aggregate.get("ratingCount") or 0)
        if review_count > 0 and aggregate.get("ratingValue") is not None:
            rating = _rating_0_5(aggregate)
        else:
            missing["rating"] = "aggregateRating present but with zero reviews"
    elif "rating" not in missing:
        missing["rating"] = missing["review_count"] = "no aggregateRating for this product"

    image_url = card.image_url if card and card.image_url else product.get("image")
    if not image_url:
        missing["image_url"] = "no image on card or in JSON-LD"

    title = card.title if card else str(product.get("name", "")).strip()
    return RetailerListing(
        retailer=Retailer.TRADEINN,
        product_url=url,
        retailer_product_id=id_match.group(1) if id_match else None,
        brand=brand,
        raw_title=title,
        model_name=None,
        gender_raw=gender_raw,
        gender=gender,
        price_eur=price,
        original_price_eur=original_price,
        in_stock=in_stock,
        rating=rating,
        review_count=review_count,
        category_breadcrumb=_find_breadcrumb(blocks),
        image_url=image_url,
        attributes=attributes,
        retrieved_at=retrieved_at,
        missing_reasons=missing
        | {"model_name": "Tradeinn gives no model name separate from the title"}
        | ({} if id_match else {"retailer_product_id": "no numeric id in URL"}),
    )


def _rating_0_5(aggregate: dict) -> float:
    """Product rating on a 0-5 scale.

    Tradeinn shows 5 stars, but its JSON-LD sets `bestRating` to the rating itself
    (ratingValue 4, bestRating 4), so `bestRating` is NOT the top of the scale there.
    We only rescale when `bestRating` clearly announces another scale (e.g. 10 or 100).
    Note: Tradeinn rounds `ratingValue` to a whole number of stars.
    """
    value = float(aggregate["ratingValue"])
    best = float(aggregate.get("bestRating") or 5)
    return round(value / best * 5, 2) if best > 5 else value


def is_trail_breadcrumb(breadcrumb: list[str]) -> bool:
    """True if the breadcrumb says trail (or is unknown, in which case we keep the product)."""
    return not breadcrumb or any("trail" in step.lower() for step in breadcrumb)


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------


def collect(client: PoliteClient, limit: int | None = None) -> CollectResult:
    """Collect all discoverable trail shoes. `limit` caps product pages (for quick tests)."""
    result = CollectResult()
    category_queue: deque[str] = deque([TRAIL_CATEGORY_URL])
    queued_categories = {TRAIL_CATEGORY_URL}
    # (url, card): the card is None for products found through links on product pages
    # (their title then comes from the page's own JSON-LD, which repeats the card title).
    product_queue: deque[tuple[str, ListingCard | None]] = deque()
    cards_by_url: dict[str, ListingCard | None] = {}

    def queue_brand(slug: str, brand_id: str) -> None:
        url = brand_trail_url(slug, brand_id)
        result.brands_seen.add(slug)
        if url not in queued_categories:
            queued_categories.add(url)
            category_queue.append(url)

    home = client.get(STORE_URL)
    for brand_id, slug in parse_brand_ids(home.text).items():
        queue_brand(slug, brand_id)

    while category_queue or product_queue:
        if category_queue:
            _read_category_page(
                client, category_queue.popleft(), result, cards_by_url, product_queue, queue_brand
            )
            continue
        if limit is not None and len(result.listings) + len(result.failures) >= limit:
            break
        url, card = product_queue.popleft()
        page = _safe_get(client, url, result)
        if page is None:
            continue
        try:
            listing = parse_product_page(page.text, url, page.retrieved_at, card)
        except Exception as error:  # one bad page must not stop the crawl
            result.failures.append({"url": url, "error": f"parse: {error}"})
            continue
        if not is_trail_breadcrumb(listing.category_breadcrumb):
            result.excluded_not_trail.append(url)
            continue
        result.listings.append(listing)
        brand_link = parse_brand_trail_link(page.text)
        if brand_link:
            queue_brand(*brand_link)
        for linked in parse_trail_product_links(page.text):
            if linked not in cards_by_url:
                cards_by_url[linked] = None
                product_queue.append((linked, None))

    log.info(
        "tradeinn: %d listings, %d failures, %d category pages (%d possibly truncated)",
        len(result.listings),
        len(result.failures),
        result.category_pages,
        len(result.truncated_pages),
    )
    return result


def _safe_get(client: PoliteClient, url: str, result: CollectResult) -> CachedResponse | None:
    try:
        page = client.get(url)
    except AccessBlockedError:
        raise  # the site refuses us: stop the whole crawl, never retry around it
    except Exception as error:  # recorded as a failure; the crawl continues
        result.failures.append({"url": url, "error": f"fetch: {error}"})
        return None
    if page.status != 200:
        result.failures.append({"url": url, "error": f"HTTP {page.status}"})
        return None
    return page


def _read_category_page(
    client: PoliteClient,
    url: str,
    result: CollectResult,
    cards_by_url: dict[str, ListingCard | None],
    product_queue: deque[tuple[str, ListingCard | None]],
    queue_brand: Callable[[str, str], None],
) -> None:
    page = _safe_get(client, url, result)
    if page is None:
        return
    result.category_pages += 1
    for brand_id, slug in parse_brand_ids(page.text).items():  # the brand menu
        queue_brand(slug, brand_id)
    cards = parse_listing_cards(page.text)
    if len(cards) >= MAX_CARDS_PER_PAGE:
        result.truncated_pages.append(url)
    new_cards = [card for card in cards if card.url not in cards_by_url]
    for card in new_cards:
        cards_by_url[card.url] = card
        product_queue.append((card.url, card))
    log.info("%s: %d cards, %d new", url, len(cards), len(new_cards))
