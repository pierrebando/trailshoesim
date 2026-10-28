"""Phase 3b: specs shown on RETAILER product pages, as a separate, labelled fallback.

Tradeinn and Glisshop already gave us short "label: value" facts in phase 1
(`RetailerListing.attributes`). This module turns them into a `RetailerFallback` per
model, with the rules agreed for phase 3b:

* numbers only when the shop writes an exact value; filter buckets ("5-8 mm",
  "De 251 g à 300 g") go to `drop_range` / `weight_range`, never into numbers;
* weight from men's/unisex listings of the standard version (no GTX, mid, wide,
  refurbished), 120-480 g, combined only if the listings agree within 5 %;
* if listings disagree, the value is null and the reason says so;
* every value is checked again against the cached retailer page (no network).

Manufacturer fields are never touched: phase 6 decides which source wins.
"""

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from pipeline.collect import glisshop
from pipeline.models import (
    CanonicalModel,
    Gender,
    ModelOffer,
    RetailerFallback,
    RetailerListing,
    RetailerTags,
)
from pipeline.normalize.brands import fold
from pipeline.specs.extract import snippet_around
from pipeline.specs.pagetext import full_page_text

WEIGHT_RANGE_G = (120, 480)
WEIGHT_AGREEMENT = 0.05  # listings must agree within 5 % to be combined
MM_AGREEMENT = 0.5
NON_STANDARD_VARIANTS = ("gore_tex", "waterproof", "wide", "extra_wide", "mid", "refurbished")

EXACT_MM = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*mm\.?\s*$", re.IGNORECASE)
RANGE_MM = re.compile(r"^\s*\d+\s*-\s*\d+\s*mm\s*$", re.IGNORECASE)
GRAMS = re.compile(r"(\d+(?:[.,]\d+)?)\s*g\b", re.IGNORECASE)
BUCKET_WORDS = re.compile(r"\b(?:de|plus|sous|moins)\b|\bà\b", re.IGNORECASE)
CUSHION_LEVELS = {"bas", "faible", "minimal", "modere", "moyen", "haut", "eleve", "maximal"}

# Tag name -> retailer attribute labels, in order of preference.
TAG_LABELS = {
    "fit_width": ("Largeur des Chaussures", "Largeur de pied"),
    "terrain": ("Terrain", "Type de terrain", "Surface"),
    "cushioning_level": ("Amorti",),
    "runner_build": ("Gabarit",),
    "distance": ("Distance",),
    "pronation": ("Allure",),
}


@dataclass(frozen=True)
class Reading:
    """One value read from one retailer listing."""

    value: object
    kind: str  # "exact", "range" or "tag"
    label: str  # the retailer's attribute label, e.g. "Drop"
    raw: str  # the retailer's attribute value, e.g. "8 mm"
    offer: ModelOffer
    listing: RetailerListing

    @property
    def standard_version(self) -> bool:
        """True for the plain version of the model (not GTX, mid, wide or refurbished)."""
        return not any(getattr(self.offer.variant, name) for name in NON_STANDARD_VARIANTS)


def _number(text: str) -> float:
    return float(text.replace(",", "."))


# ---------------------------------------------------------------------------
# Readers: one listing's attributes -> zero or more (value, kind, label, raw)
# ---------------------------------------------------------------------------


def read_drop(attrs: dict[str, str]):
    """Exact drop ("8 mm") or a filter bucket ("5-8 mm")."""
    raw = attrs.get("Drop")
    if raw and (match := EXACT_MM.match(raw)):
        yield _number(match.group(1)), "exact", "Drop", raw
    elif raw and RANGE_MM.match(raw):
        yield raw, "range", "Drop", raw


def read_weight(attrs: dict[str, str]):
    """Exact weight in grams, or a bucket ("De 251 g à 300 g")."""
    raw = attrs.get("Poids")
    if raw and not BUCKET_WORDS.search(raw) and (match := GRAMS.search(raw)):
        yield _number(match.group(1)), "exact", "Poids", raw
        return
    for label in ("Poids", "Poids des Chaussures"):
        raw = attrs.get(label)
        if raw and BUCKET_WORDS.search(raw) and "non sp" not in raw.lower():
            yield raw, "range", label, raw
            return


def read_mm(label: str) -> Callable:
    """Reader of an exact "N mm" value under `label`."""

    def reader(attrs: dict[str, str]):
        raw = attrs.get(label)
        if raw and (match := EXACT_MM.match(raw)):
            yield _number(match.group(1)), "exact", label, raw

    return reader


def read_waterproof(attrs: dict[str, str]):
    """Explicit yes/no: Tradeinn writes "Imperméable: Non" too."""
    raw = attrs.get("Imperméable", "")
    if re.match(r"oui|gore", raw, re.IGNORECASE):
        yield True, "exact", "Imperméable", raw
    elif re.match(r"non\b", raw, re.IGNORECASE):
        yield False, "exact", "Imperméable", raw
    elif "Imperméable" in attrs.get("Caractéristiques", ""):
        yield True, "exact", "Caractéristiques", attrs["Caractéristiques"]


def read_plate(attrs: dict[str, str]):
    """Carbon plate, protection plate yes/no."""
    features = attrs.get("Caractéristiques", "")
    raw = attrs.get("Plaque de protection", "")
    if "carbone" in features.lower():
        yield "carbon", "exact", "Caractéristiques", features
    elif re.match(r"oui", raw, re.IGNORECASE):
        yield "rock_plate", "exact", "Plaque de protection", raw
    elif re.match(r"non\b", raw, re.IGNORECASE):
        yield "none", "exact", "Plaque de protection", raw


# Values a shop sometimes puts in the foam/rubber fields that are not names ("Zéro Drop").
NOT_A_NAME = re.compile(r"\bdrop\b|^(?:oui|non|yes|no|standard)$", re.IGNORECASE)


def read_text(*labels: str) -> Callable:
    """Reader of the first non-empty text attribute among `labels`."""

    def reader(attrs: dict[str, str]):
        for label in labels:
            if attrs.get(label) and not NOT_A_NAME.search(attrs[label]):
                yield attrs[label], "exact", label, attrs[label]
                return

    return reader


def read_tag(tag: str) -> Callable:
    """Reader of one retailer classification (see TAG_LABELS)."""

    def reader(attrs: dict[str, str]):
        for label in TAG_LABELS[tag]:
            raw = attrs.get(label)
            if not raw:
                continue
            # Tradeinn's "Amorti" mixes levels ("Haut") with foam names ("Phylon").
            if tag == "cushioning_level" and fold(raw) not in CUSHION_LEVELS:
                continue
            yield raw, "tag", label, raw
            return

    return reader


READERS: dict[str, Callable] = {
    "drop": read_drop,
    "weight": read_weight,
    "lug_depth_mm": read_mm("Profondeur de crampon"),
    "sole_height_unlabelled_mm": read_mm("Hauteur de la semelle"),
    "waterproof": read_waterproof,
    "plate": read_plate,
    "outsole_rubber": read_text("Matière de la semelle extérieure", "Technologie Semelle"),
    "midsole_foam": read_text("Technologie de la semelle intermédiaire"),
    **{f"tag:{tag}": read_tag(tag) for tag in TAG_LABELS},
}


def readings(
    model: CanonicalModel, listings: dict[str, RetailerListing]
) -> dict[str, list[Reading]]:
    """Every value every listing of the model gives, grouped by reader."""
    found: dict[str, list[Reading]] = {name: [] for name in READERS}
    for offer in model.offers:
        listing = listings.get(str(offer.url))
        if listing is None:
            continue
        for name, reader in READERS.items():
            for value, kind, label, raw in reader(listing.attributes):
                found[name].append(Reading(value, kind, label, raw, offer, listing))
    return found


# ---------------------------------------------------------------------------
# Verification against the cached retailer page
# ---------------------------------------------------------------------------


class PageVerifier:
    """Finds each reading in the cached page it came from (pages parsed once, lazily)."""

    def __init__(self, page_of: Callable[[str, str], str | None]) -> None:
        """`page_of(retailer, url)` returns the cached HTML of a listing, or None."""
        self.page_of = page_of
        self._texts: dict[str, str] = {}
        self._details: dict[str, dict[str, str]] = {}

    def snippet(self, reading: Reading) -> str | None:
        """A verbatim snippet proving the reading, or None if it cannot be found."""
        retailer = reading.listing.retailer.value
        url = str(reading.listing.product_url)
        html = self.page_of(retailer, url)
        if html is None:
            return None
        if retailer == "glisshop":
            # Glisshop facts come from the page's embedded product JSON, not visible text.
            if url not in self._details:
                self._details[url] = glisshop.parse_product_details(html).attributes
            if self._details[url].get(reading.label) == reading.raw:
                return f"{reading.label}: {reading.raw}"
            return None
        if url not in self._texts:
            self._texts[url] = full_page_text(html)
        text = self._texts[url]
        proof = f"{reading.label} | {reading.raw}"
        start = text.find(proof)
        return snippet_around(text, start, start + len(proof)) if start >= 0 else None


# ---------------------------------------------------------------------------
# Aggregation rules
# ---------------------------------------------------------------------------


def _missing(reason: str) -> dict:
    return {"value": None, "missing_reason": reason}


def _known(reading: Reading, snippet: str, value=None, note: str | None = None) -> dict:
    retailer = reading.listing.retailer.value.capitalize()
    origin = "embedded product data" if reading.listing.retailer.value == "glisshop" else "page"
    return {
        "value": reading.value if value is None else value,
        "source_name": f"{retailer} product {origin} (retailer, not manufacturer)",
        "source_url": str(reading.listing.product_url),
        "retrieved_at": reading.listing.retrieved_at,
        "raw_snippet": snippet,
        "note": note,
    }


def _first_verified(candidates: list[Reading], verifier: PageVerifier, **known) -> dict | None:
    for reading in candidates:
        if snippet := verifier.snippet(reading):
            return _known(reading, snippet, **known)
    return None


def agreed_number(
    candidates: list[Reading], verifier: PageVerifier, relative: bool = False
) -> dict:
    """One number if all exact readings agree; else null with the reason.

    The value is the lower median: a value one listing really shows, never an average.
    """
    if not candidates:
        return _missing("no retailer listing states an exact value")
    values = sorted(r.value for r in candidates)
    low, high = values[0], values[-1]
    tolerance = WEIGHT_AGREEMENT * low if relative else MM_AGREEMENT
    if high - low > tolerance:
        return _missing(f"retailer listings disagree: {low:g} to {high:g}")
    chosen = values[(len(values) - 1) // 2]
    note = f"value shown by {len(values)} listing(s)" + (
        f", range {low:g}-{high:g}" if high != low else ""
    )
    ordered = sorted(candidates, key=lambda r: abs(r.value - chosen))
    exact = [r for r in ordered if r.value == chosen]
    result = _first_verified(exact, verifier, note=note)
    return result or _missing("value not found again in the cached retailer page")


def agreed_value(candidates: list[Reading], verifier: PageVerifier) -> dict:
    """A categorical value (bool, plate) if every listing says the same thing."""
    if not candidates:
        return _missing("no retailer listing states it")
    values = Counter(r.value for r in candidates)
    if len(values) > 1:
        detail = ", ".join(f"{v} x{n}" for v, n in values.most_common())
        return _missing(f"retailer listings disagree: {detail}")
    result = _first_verified(candidates, verifier, note=f"stated by {len(candidates)} listing(s)")
    return result or _missing("value not found again in the cached retailer page")


def most_common_name(candidates: list[Reading], verifier: PageVerifier) -> dict:
    """The spelling most listings use; other spellings are listed in the note."""
    if not candidates:
        return _missing("no retailer listing states it")

    def key(text: str) -> str:
        return re.sub(r"[®™\s]+", " ", fold(text)).strip()

    counts = Counter(key(r.raw) for r in candidates)
    top = counts.most_common(1)[0][0]
    others = sorted({r.raw for r in candidates if key(r.raw) != top})
    note = f"{counts[top]} of {len(candidates)} listing(s)"
    if others:
        note += "; also listed as: " + "; ".join(others[:3])
    chosen = [r for r in candidates if key(r.raw) == top]
    result = _first_verified(chosen, verifier, note=note)
    return result or _missing("value not found again in the cached retailer page")


def build_fallback(
    model: CanonicalModel, listings: dict[str, RetailerListing], verifier: PageVerifier
) -> RetailerFallback:
    """The RetailerFallback of one model."""
    found = readings(model, listings)

    def exact(name: str) -> list[Reading]:
        return [r for r in found[name] if r.kind == "exact"]

    def weights(genders: set) -> list[Reading]:
        low, high = WEIGHT_RANGE_G
        return [
            r
            for r in exact("weight")
            if r.offer.gender in genders and r.standard_version and low <= r.value <= high
        ]

    def bucket(name: str, has_exact: bool) -> dict:
        if has_exact:
            return _missing("an exact value is available")
        return most_common_name([r for r in found[name] if r.kind == "range"], verifier)

    men = weights({Gender.MEN, Gender.UNISEX})
    women = weights({Gender.WOMEN})
    other_weights = bool(exact("weight"))
    tags = {tag: most_common_name(found[f"tag:{tag}"], verifier) for tag in TAG_LABELS}

    def weight_field(candidates: list[Reading]) -> dict:
        if not candidates and other_weights:
            return _missing(
                "only other versions (GTX, mid, wide) or the other gender state a weight"
            )
        return agreed_number(candidates, verifier, relative=True)

    weight_men, weight_women = weight_field(men), weight_field(women)
    if weight_women["value"] is not None and weight_women["value"] == weight_men["value"]:
        weight_women["note"] += "; identical to the men's value (the shop may repeat it)"
    return RetailerFallback(
        weight_g=weight_men,
        weight_women_g=weight_women,
        drop_mm=agreed_number(exact("drop"), verifier),
        lug_depth_mm=agreed_number(exact("lug_depth_mm"), verifier),
        sole_height_unlabelled_mm=agreed_number(exact("sole_height_unlabelled_mm"), verifier),
        waterproof=agreed_value([r for r in exact("waterproof") if r.standard_version], verifier),
        plate=agreed_value(exact("plate"), verifier),
        outsole_rubber=most_common_name(exact("outsole_rubber"), verifier),
        midsole_foam=most_common_name(exact("midsole_foam"), verifier),
        drop_range=bucket("drop", bool(exact("drop"))),
        weight_range=bucket("weight", bool(exact("weight"))),
        tags=RetailerTags(**tags),
    )
