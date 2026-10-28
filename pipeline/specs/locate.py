"""Find the manufacturer product page of a model, using the brand's own sitemap.

A product URL is matched by its slug: "…/fr_FR/peregrine-16/60848M.html" has the tokens
[peregrine, 16]. The model's name tokens must appear in order, and the token right after
them, if it is a version, must be the model's version. So "Peregrine 15" does not match
"peregrine-16", and "Kjerag" does not match "kjerag-2".
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from pipeline.normalize.brands import fold
from pipeline.normalize.titles import GLUED_VERSION_RE, version_value
from pipeline.utils.http import PoliteClient

NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
# Words that make a URL a variant of the base model: prefer the URL without them.
VARIANT_TOKENS = {"gtx", "gore", "tex", "wide", "large", "larges", "mid", "wp", "boa", "ltr"}
WIDE_TOKENS = {"wide", "large", "larges", "2e", "4e"}


@dataclass(frozen=True)
class Candidate:
    """A product URL that matches the model, and why."""

    url: str
    sitemap_url: str
    extra_tokens: tuple[str, ...]


def read_sitemap(client: PoliteClient, url: str, child_filter: str | None) -> dict[str, str]:
    """All page URLs of a sitemap (following sitemap indexes): {page_url: sitemap_url}."""
    root = ET.fromstring(client.get(url).text.encode("utf-8"))
    locations = [loc.text.strip() for loc in root.iter(f"{NAMESPACE}loc") if loc.text]
    if root.tag == f"{NAMESPACE}sitemapindex":
        pages: dict[str, str] = {}
        for child in locations:
            if child_filter is None or re.search(child_filter, child):
                pages.update(read_sitemap(client, child, None))
        return pages
    return {location: url for location in locations}


def slug_tokens(url: str, last_segment_only: bool = False) -> list[str]:
    """Name tokens of a product URL path, stopping at the first product code.

    `last_segment_only` ignores folders: NNormal files a "Kboix" page under ".../tomir/".
    """
    path = re.sub(r"^https?://[^/]+", "", url)
    if last_segment_only:
        path = path.rstrip("/").rsplit("/", 1)[-1]
    tokens = []
    for token in re.split(r"[^a-z0-9]+", fold(path)):
        if not token:
            continue
        digits = sum(ch.isdigit() for ch in token)
        mixed_code = (
            len(token) >= 5 and digits and not token.isdigit() and not GLUED_VERSION_RE.match(token)
        )
        if digits >= 4 or mixed_code:  # "60848m", "33068", "n2zkxm1": a code, the name ended
            break
        if tokens and token == "0" and tokens[-1].isdigit():
            continue  # "tomir-2-0" is "Tomir 2.0"
        glued = GLUED_VERSION_RE.match(token)
        if glued:  # "ride-tr3" -> ride, tr, 3 (same rule as the title parser)
            name_part = glued.group(1) or glued.group(2)
            tokens += [name_part, glued.group(3)]
            continue
        tokens.append(token)
    return tokens


def _match(model_tokens: list[str], version: str | None, tokens: list[str]) -> list[str] | None:
    """Tokens left over if the model name and version match the slug, else None."""
    size = len(model_tokens)
    for start in range(len(tokens) - size + 1):
        if tokens[start : start + size] != model_tokens:
            continue
        after = tokens[start + size] if start + size < len(tokens) else None
        slug_version = version_value(after) if after else None
        if slug_version != version:
            continue
        used = size + (1 if slug_version else 0)
        return tokens[:start] + tokens[start + used :]
    return None


def find_candidates(
    model_key: str,
    version: str | None,
    pages: dict[str, str],
    product_url: str,
    last_segment_only: bool = False,
) -> list[Candidate]:
    """Product URLs of the sitemap that match this model."""
    model_tokens = [fold(t) for t in re.split(r"[^a-z0-9]+", fold(model_key)) if t]
    candidates = []
    for url, sitemap_url in pages.items():
        if not re.search(product_url, url):
            continue
        left = _match(model_tokens, version, slug_tokens(url, last_segment_only))
        if left is not None:
            candidates.append(Candidate(url, sitemap_url, tuple(left)))
    return candidates


def best_candidate(
    candidates: list[Candidate], men_hint: str | None, women_hint: str | None
) -> Candidate | None:
    """Prefer the base model (no GTX/wide...), then the men's page, then the shortest slug."""

    def rank(candidate: Candidate) -> tuple[int, int, int, str]:
        variant_words = sum(token in VARIANT_TOKENS for token in candidate.extra_tokens)
        gender = 0
        if men_hint and re.search(men_hint, candidate.url):
            gender = -1
        elif women_hint and re.search(women_hint, candidate.url):
            gender = 1
        return (variant_words, gender, len(candidate.extra_tokens), candidate.url)

    return min(candidates, key=rank, default=None)


def wide_candidate(candidates: list[Candidate]) -> Candidate | None:
    """A URL of the same model whose slug says it is a wide version, if any."""
    wide = [c for c in candidates if WIDE_TOKENS & set(c.extra_tokens)]
    return min(wide, key=lambda c: c.url, default=None)
