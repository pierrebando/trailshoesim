"""What the three review collectors share: matching rules and text helpers.

Matching is STRICT on purpose. A review is a candidate for a model when the model's
words appear in order in the review URL slug, immediately followed by the model's
version (or by no version at all when the model has none). The review's title must then
say the same thing. So "Speedgoat 5" can never be attached to "Speedgoat 6", and
"Tomir" (version 1) is not attached to "Tomir 2.0".
"""

import json
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from pipeline.models import MAX_EXCERPT_WORDS, CanonicalModel, MatchConfidence
from pipeline.normalize.brands import fold
from pipeline.normalize.matching import split_key
from pipeline.normalize.titles import GLUED_VERSION_RE, version_value

# Words that make a review about a VARIANT of the model (still the same model line).
VARIANT_WORDS = {"gtx", "gore", "tex", "boa", "wide", "mid", "wp", "waterproof", "ptx"}
COMPARISON_WORDS = {"vs", "versus"}
# Words some sources add or drop in names: "Gel-Trabuco" vs "Trabuco", "S/Lab Genesis".
OPTIONAL_LEADING_WORDS = {"gel", "terrex"}
# Words that, right before or after a model name, turn it into ANOTHER shoe of the same
# family: "Prodigio Pro" is not "Prodigio", "S/Lab Genesis" is not "Genesis", "Peregrine
# 13 ST" is not "Peregrine 13". Free text is fine ("Ultra Glide 4: Something for
# Everyone", "test-peregrine-13-legerete-et-rapidite"). The list is completed at run time
# with the modifiers seen in our own catalogue (see `catalogue_modifiers`).
MODIFIER_WORDS = {
    "pro",
    "max",
    "ultra",
    "speed",
    "flow",
    "sl",
    "tt",
    "lite",
    "light",
    "evo",
    "st",
    "spine",
    "ride",
    "gravel",
    "mt",
    "elite",
    "sky",
    "cross",
    "hybrid",
    "race",
    "racer",
    "tech",
    "carbon",
    "plus",
    "lab",
    "s",
    "reflective",
    "atr",
    "lt",
    "xt",
    "boa2",
}


@dataclass
class ParsedReview:
    """What a collector read from one review page."""

    title: str
    date: str | None  # ISO date as found in the page
    ratings: list[dict] = field(default_factory=list)  # SourceRating fields
    lab_values: dict[str, dict] = field(default_factory=dict)  # SourcedFloat fields
    conclusion: str | None = None  # full text: local cache only, never committed
    conclusion_heading: str | None = None
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Match:
    """A review URL proposed for a model, and how confident we are."""

    url: str
    confidence: MatchConfidence | None  # None = ambiguous, needs a human decision
    note: str


def text_tokens(text: str) -> list[str]:
    """Normalised words: 'Lone Peak 9+' -> [lone, peak, 9+]; 'Tomir 2.0' -> [tomir, 2]."""
    tokens: list[str] = []
    for raw in re.split(r"[^a-z0-9+]+", fold(text).replace("\u2019", "'")):
        if not raw:
            continue
        if raw == "plus" and tokens and tokens[-1].isdigit():
            tokens[-1] += "+"  # "9-plus" in a URL is "9+"
            continue
        if raw == "0" and tokens and tokens[-1].isdigit():
            continue  # "2-0" / "2.0" is version 2
        glued = GLUED_VERSION_RE.match(raw)
        if glued:  # "tr3" -> tr, 3 ; "410v9" -> 410, 9
            tokens += [glued.group(1) or glued.group(2), glued.group(3)]
            continue
        tokens.append(raw)
    return tokens


def _version(token: str | None) -> str:
    if token is None:
        return ""
    if re.fullmatch(r"\d{1,2}\+", token):
        return token
    return version_value(token) or ""


def model_word_variants(model: CanonicalModel) -> list[list[str]]:
    """The model's words, plus the same words without optional leading words."""
    _, model_key, _ = split_key(model.key)
    words = text_tokens(model_key)
    variants = [words]
    trimmed = words
    while trimmed and trimmed[0] in OPTIONAL_LEADING_WORDS and len(trimmed) > 1:
        trimmed = trimmed[1:]
        variants.append(trimmed)
    return variants


def names_model(
    tokens: list[str], model: CanonicalModel, modifiers: set[str] = MODIFIER_WORDS
) -> bool:
    """True if `tokens` name the model with exactly its version, and no modifier word."""
    version = split_key(model.key)[2]
    for words in model_word_variants(model):
        size = len(words)
        for start in range(len(tokens) - size + 1):
            if tokens[start : start + size] != words:
                continue
            following = tokens[start + size] if start + size < len(tokens) else None
            if _version(following) != version:
                continue
            after = start + size + (1 if version else 0)
            before_ok = start == 0 or tokens[start - 1] not in modifiers
            after_ok = after >= len(tokens) or tokens[after] not in modifiers
            if before_ok and after_ok:
                return True
    return False


def catalogue_modifiers(models: list[CanonicalModel]) -> set[str]:
    """MODIFIER_WORDS plus words that extend one catalogue model into another.

    If the catalogue has both "Prodigio" and "Prodigio Pro", then "pro" is a modifier.
    """
    names = {tuple(text_tokens(split_key(m.key)[1])) for m in models}
    extra = set()
    for name in names:
        for other in names:
            if len(other) == len(name) + 1 and other[: len(name)] == name:
                extra.add(other[-1])
            if len(other) == len(name) + 1 and other[1:] == name:
                extra.add(other[0])
    return MODIFIER_WORDS | extra


def reviews_numbered_versions(
    model: CanonicalModel, urls: list[str], modifiers: set[str] = MODIFIER_WORDS
) -> bool:
    """True if some URL names this model's words followed by a version number."""
    for url in urls:
        tokens = text_tokens(slug_of(url))
        for words in model_word_variants(model):
            for start in range(len(tokens) - len(words)):
                if tokens[start : start + len(words)] == words and _version(
                    tokens[start + len(words)]
                ):
                    return True
    return False


def brand_named(tokens: list[str], model: CanonicalModel) -> bool:
    """True if all words of the brand appear together ("new balance", not just "new")."""
    brand_words = text_tokens(model.brand)
    size = len(brand_words)
    return any(tokens[i : i + size] == brand_words for i in range(len(tokens) - size + 1))


def slug_of(url: str) -> str:
    """Last path segment of a URL."""
    return url.rstrip("/").rsplit("/", 1)[-1]


def candidate_urls(
    model: CanonicalModel, urls: list[str], modifiers: set[str] = MODIFIER_WORDS
) -> list[str]:
    """Review URLs whose slug names the model and its version."""
    return [url for url in urls if names_model(text_tokens(slug_of(url)), model, modifiers)]


def classify(
    model: CanonicalModel, url: str, title: str, modifiers: set[str] = MODIFIER_WORDS
) -> Match:
    """Confidence of a candidate, once its title is known."""
    slug_tokens = text_tokens(slug_of(url))
    title_tokens = text_tokens(title)
    words = set(slug_tokens) | set(title_tokens)
    if COMPARISON_WORDS & words:
        return Match(url, None, "comparison of several shoes")
    if not names_model(title_tokens, model, modifiers):
        return Match(url, None, f"title does not confirm model and version: {title!r}")
    if not (brand_named(title_tokens, model) or brand_named(slug_tokens, model)):
        return Match(url, None, "brand not named in URL or title")
    variant = sorted(VARIANT_WORDS & words)
    if variant:
        return Match(url, MatchConfidence.VARIANT, f"review of a variant: {', '.join(variant)}")
    return Match(url, MatchConfidence.EXACT, "URL and title name the model and version")


# ---------------------------------------------------------------------------
# Page helpers
# ---------------------------------------------------------------------------


def json_ld_date(soup: BeautifulSoup) -> str | None:
    """Publication date (JSON-LD `datePublished`) of the page, as YYYY-MM-DD."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        items = data.get("@graph", [data]) if isinstance(data, dict) else data
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and item.get("datePublished"):
                return str(item["datePublished"])[:10]
    return None


# Headings that start the comments / author / related-articles part of a page: the
# review is over, whatever the heading level ("Leave a Reply" is an h3 under an h2).
END_OF_REVIEW = re.compile(
    r"leave a reply|join the conversation|comments?\b|the authors?|related|have you run"
    r"|you may also like|laisser un commentaire|articles similaires|commentaires?",
    re.IGNORECASE,
)


def _inside_comments(element) -> bool:
    for parent in element.parents:
        marker = " ".join([*(parent.get("class") or []), parent.get("id") or ""]).lower()
        if "comment" in marker:
            return True
    return False


def section_text(soup: BeautifulSoup, heading_pattern: str) -> tuple[str | None, str | None]:
    """(heading, text) of the first section whose heading matches `heading_pattern`.

    The text is every paragraph and list item after the heading, up to the next heading
    of the same or a higher level.
    """
    for heading in soup.find_all(["h2", "h3", "h4"]):
        title = heading.get_text(" ", strip=True)
        if not re.search(heading_pattern, title, re.IGNORECASE):
            continue
        level = int(heading.name[1])
        parts = []
        for element in heading.find_all_next():
            is_heading = element.name in ("h1", "h2", "h3", "h4")
            if is_heading and (
                int(element.name[1]) <= level or END_OF_REVIEW.search(element.get_text())
            ):
                break
            if element.name in ("p", "li") and not _inside_comments(element):
                text = element.get_text(" ", strip=True)
                if text:
                    parts.append(text)
        if parts:
            return title, " ".join(parts)
    return None, None


def excerpt_of(text: str | None, max_words: int = MAX_EXCERPT_WORDS) -> str | None:
    """Our selection: the first sentences of the conclusion, at most `max_words` words.

    Whole sentences are kept while they fit; if the first sentence alone is too long,
    its first words are kept and marked with an ellipsis.
    """
    if not text:
        return None
    # Skip a leading reviewer tag ("SAM : Some shoe updates..."): it is not the verdict.
    text = re.sub(r"^[A-Z][A-Z .'-]{1,20}\s*:\s*", "", " ".join(text.split()))
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chosen: list[str] = []
    for sentence in sentences:
        if len(" ".join([*chosen, sentence]).split()) > max_words:
            break
        chosen.append(sentence)
    if chosen:
        return " ".join(chosen)
    return " ".join(sentences[0].split()[: max_words - 1]) + " …"
