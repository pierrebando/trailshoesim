"""Why is data missing? A gap-by-gap diagnosis, written to docs/coverage-diagnosis.md.

    python -m pipeline.diagnose

Every gap (a model without a price/rating, without a manufacturer page, a null spec
field, a model without an expert review) gets ONE cause:

  (a) our crawler missed it   (b) JavaScript-rendered, our HTTP parser saw nothing
  (c) matching failed         (d) the source does not publish it   (e) access forbidden

It reads the committed data and, for a few checks, the local HTTP cache (data/raw/); it
never downloads anything.
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from pipeline.models import InterimCatalog, InterimReviews, InterimSpecs
from pipeline.reviews.__main__ import SOURCES as REVIEW_SOURCES
from pipeline.reviews.common import (
    candidate_urls,
    catalogue_modifiers,
    model_word_variants,
    slug_of,
    text_tokens,
)
from pipeline.utils.http import PoliteClient

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "docs" / "coverage-diagnosis.md"
CAUSES = {
    "a": "crawler missed it",
    "b": "JavaScript-rendered",
    "c": "matching failed",
    "d": "not published by the source",
    "e": "access forbidden or blocked",
}
TRADEINN_TRAIL = "https://www.tradeinn.com/runnerinn/fr/chaussures-chaussures-trail-running/10005/s"
# Shoe brands among Tradeinn's trail menu (the rest of the menu is clothing and accessories).
SHOE_BRANDS = {
    "hoka", "nike", "on-running", "topo-athletic", "scott", "scarpa", "dynafit", "craft",
    "inov8", "skechers", "vivobarefoot", "xero-shoes", "newton-running", "mount-to-coast",
    "columbia", "42k-running", "otso",
}  # fmt: skip
SPEC_FIELDS = [
    "weight_g", "stack_heel_mm", "stack_forefoot_mm", "drop_mm", "lug_depth_mm",
    "midsole_foam", "outsole_rubber", "plate", "waterproof", "width_options",
]  # fmt: skip


class Gaps:
    """Counts and examples of gaps per (source, cause)."""

    def __init__(self) -> None:
        """Start with no gap."""
        self.counts: Counter = Counter()
        self.examples: dict[tuple, list[str]] = defaultdict(list)

    def add(self, source: str, cause: str, what: str, example: str, n: int = 1) -> None:
        """Count `n` gaps of one kind and keep up to 3 examples."""
        self.counts[(source, cause, what)] += n
        if len(self.examples[(source, cause, what)]) < 3:
            self.examples[(source, cause, what)].append(example)


def _has_undecodable_json_ld(html: str) -> bool:
    """True if a JSON-LD block of the page is not valid JSON (our parser skips it)."""
    blocks = re.findall(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", html, re.S)
    for block in blocks:
        try:
            json.loads(block)
        except json.JSONDecodeError:
            return True
    return False


def retailer_gaps(gaps: Gaps) -> None:
    """Tradeinn crawl completeness, missing ratings, and the two blocked retailers."""
    report = json.loads((INTERIM / "collect_report.json").read_text(encoding="utf-8"))
    listings = json.loads((INTERIM / "retailer_listings.json").read_text(encoding="utf-8"))
    listings = listings["listings"] if isinstance(listings, dict) else listings
    client = PoliteClient("tradeinn")
    page = client.read_cached(TRADEINN_TRAIL)
    if page is not None:
        menu = set(re.findall(r"""href=['"]/runnerinn/fr/([a-z0-9-]+)/\d+/m['"]""", page.text))
        missed = sorted((menu & SHOE_BRANDS) - set(report["tradeinn"]["brands_seen"]))
        gaps.add(
            "Tradeinn",
            "a",
            "shoe brands of the trail menu never visited",
            ", ".join(missed[:6]),
            len(missed),
        )
    truncated = report["tradeinn"]["possibly_truncated_category_pages"]
    gaps.add(
        "Tradeinn",
        "a",
        "category pages cut at 96 products",
        truncated[0].rsplit("/", 2)[-2] if truncated else "",
        len(truncated),
    )
    known = {item["product_url"] for item in listings}
    linked = set()
    for item in [i for i in listings if i["retailer"] == "tradeinn"]:
        cached = client.read_cached(item["product_url"])
        if cached is None:
            continue
        for href in re.findall(
            r"""href=['"]((?:https://www\.tradeinn\.com)?/runnerinn/fr/[^'"]*trail[^'"]*/\d+/p)['"]""",
            cached.text,
        ):
            linked.add(href if href.startswith("http") else f"https://www.tradeinn.com{href}")
    unseen = sorted(linked - known)
    gaps.add(
        "Tradeinn",
        "a",
        "trail products linked from product pages, never collected",
        unseen[0] if unseen else "",
        len(unseen),
    )
    for failure in report["tradeinn"]["failures"]:
        # Server-rendered pages (not JavaScript): either a product block that is not valid
        # JSON (our parser skips it), or no product block at all.
        cached = client.read_cached(failure["url"])
        if cached is not None and _has_undecodable_json_ld(cached.text):
            gaps.add("Tradeinn", "a", "product data block our parser cannot decode", failure["url"])
        else:
            gaps.add("Tradeinn", "d", "product page without product data", failure["url"])
    for item in listings:
        reason = item["missing_reasons"].get("rating")
        if reason:
            gaps.add(item["retailer"].capitalize(), "d", "listings without a buyer rating", reason)
    gaps.add("Le Pape", "e", "whole retailer", "Cloudflare bot challenge on every page")
    gaps.add("i-Run", "e", "whole retailer", "terms forbid extracting any part of the site")


def manufacturer_cause(brand_config: dict, record) -> str:
    """Cause of a model having no manufacturer page."""
    if brand_config.get("status") == "unreachable":
        return "a"  # a technical failure, not a refusal: re-checked by pipeline.recheck
    if brand_config.get("status") == "blocked":
        return "b" if "JavaScript" in brand_config["reason"] else "e"
    if not brand_config.get("sitemaps"):
        return "a"  # allowed, but no way to find product pages yet
    return "d"  # the brand's sitemap has no page for this model (often an older version)


def spec_gaps(gaps: Gaps, specs: InterimSpecs, shoes: list[dict]) -> dict:
    """Manufacturer pages and null spec fields, with the manufacturer-side cause."""
    brands = yaml.safe_load((ROOT / "pipeline" / "config" / "manufacturers.yaml").read_text())[
        "brands"
    ]
    causes = {}
    for model_id, record in specs.models.items():
        if record.manufacturer_url is None:
            cause = manufacturer_cause(brands.get(record.brand, {"status": "allowed"}), record)
            causes[model_id] = cause
            gaps.add(
                "Manufacturer pages",
                cause,
                "models without a manufacturer page",
                f"{model_id} ({record.manufacturer_url_missing_reason})",
            )
        else:
            causes[model_id] = "d"
    by_field: dict[str, Counter] = defaultdict(Counter)
    for shoe in shoes:
        for field in SPEC_FIELDS:
            value = shoe["specs"][field]["value"]
            if field == "weight_g":
                value = value if value is not None else shoe["specs"]["weight_women_g"]["value"]
            if value is None:
                by_field[field][causes.get(shoe["id"], "d")] += 1
    for field, counter in by_field.items():
        for cause, n in counter.items():
            gaps.add("Spec fields (all tiers)", cause, f"null `{field}`", "", n)
    derivable = sum(
        1 for s in shoes
        if s["specs"]["drop_mm"]["value"] is None
        and s["specs"]["stack_heel_mm"]["value"] is not None
        and s["specs"]["stack_forefoot_mm"]["value"] is not None
    )  # fmt: skip
    return {"by_field": by_field, "derivable_drop": derivable}


def review_gaps(gaps: Gaps, catalog: InterimCatalog, reviews: InterimReviews) -> None:
    """For every model without a review from a source: missed match or no review at all."""
    modifiers = catalogue_modifiers(catalog.models)
    with (INTERIM / "reviews_needs_review.csv").open(encoding="utf-8") as file:
        pending = {(row["source"], row["model_id"]) for row in csv.DictReader(file)}
    for name, module in REVIEW_SOURCES.items():
        urls = module.discover(PoliteClient(f"reviews/{name}"))
        for model in catalog.models:
            if any(r.source == name for r in reviews.models.get(model.id, [])):
                continue
            if candidate_urls(model, urls, modifiers):
                what = (
                    "URL names the model, rejected or left for a human"
                    if (name, model.id) in pending
                    else "URL names the model, page title did not confirm"
                )
                gaps.add(name, "c", what, model.id)
                continue
            loose = [
                u
                for u in urls
                if any(
                    all(w in text_tokens(slug_of(u)) for w in words)
                    for words in model_word_variants(model)
                )
            ]
            what = (
                "only another version or a variant is reviewed"
                if loose
                else "no review of this model"
            )
            gaps.add(name, "d", what, f"{model.id}" + (f" -> {slug_of(loose[0])}" if loose else ""))
    gaps.add(
        "doctors_of_running",
        "e",
        "whole source",
        "robots.txt disallows anthropic-ai and Claude-Web",
        len(catalog.models),
    )


def catalogue_gaps(gaps: Gaps, catalog: InterimCatalog) -> None:
    """Models split in two by the title parser, and merges still waiting for a decision."""
    keys = {m.key: m for m in catalog.models}
    for model in catalog.models:
        brand, words, version = model.key.split("|")
        if version:
            continue
        tokens = words.split()
        for i in range(1, len(tokens)):
            if tokens[
                i
            ].isdigit():  # "golden gate 2 atr" with no version: is "golden gate|2" there?
                other = f"{brand}|{' '.join(tokens[:i])}|{tokens[i]}"
                if other in keys:
                    gaps.add(
                        "Catalogue (phase 2)",
                        "c",
                        "same shoe split in two models (word after the version)",
                        f"{model.id} = {keys[other].id}",
                    )
    with (INTERIM / "needs_review.csv").open(encoding="utf-8") as file:
        undecided = [row for row in csv.DictReader(file) if not row["decision"]]
    for row in undecided:
        gaps.add(
            "Catalogue (phase 2)",
            "c",
            "possible duplicates waiting for a decision in needs_review.csv",
            row["keys"][:70],
        )


def render(gaps: Gaps, extra: dict) -> str:
    """The markdown report."""
    sources = list(dict.fromkeys(source for source, _, _ in gaps.counts))
    lines = [
        "# Coverage diagnosis: why data is missing",
        "",
        "Generated by `python -m pipeline.diagnose` from the committed data and the local cache.",
        "Causes: " + "; ".join(f"**({k})** {v}" for k, v in CAUSES.items()) + ".",
        "Counts are gaps (a model, a listing or a field), not requests.",
        "",
        "## Counts per source and cause",
        "",
        "| Source | " + " | ".join(f"({k})" for k in CAUSES) + " |",
        "|---|" + "---|" * len(CAUSES),
    ]
    for source in sources:
        row = [
            sum(n for (s, c, _), n in gaps.counts.items() if s == source and c == k) for k in CAUSES
        ]
        lines.append(f"| {source} | " + " | ".join(str(n) if n else "" for n in row) + " |")
    lines += ["", "## Details and examples", ""]
    for source in sources:
        lines += [f"### {source}", "", "| Cause | Gap | Count | Examples |", "|---|---|---|---|"]
        for (s, cause, what), n in sorted(gaps.counts.items()):
            if s != source:
                continue
            examples = "; ".join(e for e in gaps.examples[(s, cause, what)] if e).replace("|", "/")
            lines.append(f"| ({cause}) {CAUSES[cause]} | {what} | {n} | {examples[:220]} |")
        lines.append("")
    lines += [
        "## Notes",
        "",
        f"* Spec fields: the cause shown is the manufacturer side (the first tier); the lab and "
        f"retailer tiers had no value either. {extra['derivable_drop']} null drops could be "
        "derived from the two stack heights (see the defaults review).",
        "* Reviews: '(d) only another version' means the source tested e.g. the Speedgoat 5 but "
        "not the Speedgoat 6; versions are never mixed (decision 15).",
        "* Manufacturer pages '(d)': the brand's own sitemap has no page for the model, usually "
        "because it is an older version still sold by retailers.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Diagnose every gap and write docs/coverage-diagnosis.md."""
    catalog = InterimCatalog.model_validate_json((INTERIM / "catalog.json").read_bytes())
    specs = InterimSpecs.model_validate_json((INTERIM / "specs.json").read_bytes())
    reviews = InterimReviews.model_validate_json((INTERIM / "expert_reviews.json").read_bytes())
    shoes = json.loads((ROOT / "data" / "processed" / "shoes.json").read_text(encoding="utf-8"))[
        "shoes"
    ]
    gaps = Gaps()
    retailer_gaps(gaps)
    extra = spec_gaps(gaps, specs, shoes)
    review_gaps(gaps, catalog, reviews)
    catalogue_gaps(gaps, catalog)
    OUT.write_text(render(gaps, extra), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
