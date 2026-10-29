"""Phase 3: manufacturer specs for every model of data/interim/catalog.json.

    python -m pipeline.specs [--brand X] [--refresh]

For each model: find its page in the brand's sitemap (locate.py), read the page text
(pagetext.py), extract the specs with quoted snippets (extract.py), keep only verified
values, and write data/interim/specs.json (InterimSpecs) and docs/data-coverage.md.
Brands whose site may not be collected (pipeline/config/manufacturers.yaml) get null
values with the reason.
"""

import argparse
import datetime as dt
import logging
import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from bs4 import BeautifulSoup
from pydantic import TypeAdapter

from pipeline.models import (
    CanonicalModel,
    InterimCatalog,
    InterimSpecs,
    LabFallback,
    ModelSpecs,
    RetailerListing,
)
from pipeline.normalize.matching import split_key
from pipeline.reviews.common import names_model, text_tokens
from pipeline.specs.coverage import write_coverage
from pipeline.specs.extract import Found, extract, verify
from pipeline.specs.locate import best_candidate, find_candidates, read_sitemap, wide_candidate
from pipeline.specs.pagetext import page_text
from pipeline.specs.retailer import PageVerifier, build_fallback
from pipeline.utils.http import AccessBlockedError, PoliteClient

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "data" / "interim" / "catalog.json"
LISTINGS_PATH = ROOT / "data" / "interim" / "retailer_listings.json"
SPECS_PATH = ROOT / "data" / "interim" / "specs.json"
COVERAGE_PATH = ROOT / "docs" / "data-coverage.md"
CONFIG_PATH = ROOT / "pipeline" / "config" / "manufacturers.yaml"

SPEC_FIELDS = [
    "weight_g",
    "weight_women_g",
    "stack_heel_mm",
    "stack_forefoot_mm",
    "drop_mm",
    "lug_depth_mm",
    "midsole_foam",
    "midsole_foam_family",
    "plate",
    "outsole_rubber",
    "waterproof",
    "upper_notes",
    "width_options",
    "release_year",
]
log = logging.getLogger("pipeline.specs")


def _missing(reason: str) -> dict:
    return {"value": None, "missing_reason": reason}


def _known(found: Found, url: str, retrieved_at: dt.date, brand: str) -> dict:
    return {
        "value": found.value,
        "source_name": f"{brand} official site",
        "source_url": url,
        "retrieved_at": retrieved_at,
        "raw_snippet": found.snippet,
        "derivation": found.derivation,
        "note": found.note,
    }


def _lab_fallback() -> LabFallback:
    reason = "lab measurements from review sources are collected in phase 4, used in phase 6"
    return LabFallback(
        stack_heel_mm=_missing(reason),
        stack_forefoot_mm=_missing(reason),
        lug_depth_mm=_missing(reason),
    )


def _page_title(html: str) -> str:
    """The product name shown on the page: the first <h1>, else the <title>."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1") or soup.find("title")
    return heading.get_text(" ", strip=True) if heading else ""


def empty_record(model: CanonicalModel, reason: str) -> ModelSpecs:
    """A record with every field null for the same reason (brand blocked, page not found)."""
    return ModelSpecs(
        model_id=model.id,
        brand=model.brand,
        model=model.model,
        version=model.version,
        manufacturer_url=None,
        manufacturer_url_missing_reason=reason,
        retrieved_at=None,
        lab_fallback=_lab_fallback(),
        **{name: _missing(reason) for name in SPEC_FIELDS},
    )


def record_from_page(
    model: CanonicalModel,
    url: str,
    html: str,
    retrieved_at: dt.date,
    page_is_women: bool,
    wide_url: tuple[str, str] | None = None,
    url_extra_words: tuple[str, ...] = (),
) -> tuple[ModelSpecs, list[str]]:
    """Build the record of one model from its product page. Returns (record, rejections)."""
    page = page_text(html)
    skipped: dict[str, str] = {}
    found = extract(page.text, page.product_name, page_is_women, skipped)
    fields, rejected = {}, []
    for name in SPEC_FIELDS:
        value = found.get(name)
        if value is not None and verify(value, page.text):
            fields[name] = _known(value, url, retrieved_at, model.brand)
        else:
            if value is not None:
                rejected.append(f"{name}: snippet or value not found in page text")
            fields[name] = _missing(skipped.get(name, "not stated on the manufacturer page"))
    if fields["width_options"]["value"] is None and wide_url:
        wide, sitemap = wide_url
        fields["width_options"] = {
            "value": ["wide"],
            "source_name": f"{model.brand} official sitemap",
            "source_url": sitemap,
            "retrieved_at": retrieved_at,
            "raw_snippet": wide,
            "derivation": "from_sitemap_url",
            "note": "the sitemap lists a wide version of this model; base width not stated",
        }
    record = ModelSpecs(
        model_id=model.id,
        brand=model.brand,
        model=model.model,
        version=model.version,
        manufacturer_url=url,
        manufacturer_url_missing_reason=None,
        url_extra_words=list(url_extra_words),
        retrieved_at=retrieved_at,
        lab_fallback=_lab_fallback(),
        **fields,
    )
    return record, rejected


def collect_brand(brand: str, config: dict, models: list[CanonicalModel], refresh: bool):
    """Records for all models of one allowed brand, plus a small report."""
    report = Counter()
    if not config.get("sitemaps"):
        reason = "no sitemap published by the manufacturer; product page not searched"
        return [empty_record(m, reason) for m in models], report
    client = PoliteClient(f"specs/{fold_name(brand)}", refresh=refresh)
    pages: dict[str, str] = {}
    for sitemap in config["sitemaps"]:
        pages.update(read_sitemap(client, sitemap, config.get("child_filter")))
    report["sitemap_urls"] = len(pages)
    records = []
    for model in models:
        _, model_key, version = split_key(model.key)
        candidates = find_candidates(
            model_key,
            version or None,
            pages,
            config["product_url"],
            config.get("last_segment_only", False),
        )
        choice = best_candidate(candidates, config.get("men_hint"), config.get("women_hint"))
        if choice is None:
            records.append(
                empty_record(model, "no matching product page in the manufacturer sitemap")
            )
            report["not_found"] += 1
            continue
        allowed = config.get("allowed_extra_words")
        if allowed is not None and set(choice.extra_tokens) - set(allowed):
            # Stricter brands: "mesa-summit-men" is NOT the "Mesa"; leave it for a person.
            extra = " ".join(sorted(set(choice.extra_tokens) - set(allowed)))
            reason = f"loose match only ({choice.url}, extra words: {extra}); check by hand"
            records.append(empty_record(model, reason))
            report["loose_match_rejected"] += 1
            continue
        url = choice.url
        if config.get("url_rewrite"):
            url = url.replace(*config["url_rewrite"])
        try:
            response = client.get(url)
        except AccessBlockedError:
            raise
        except Exception as error:  # recorded; the other models continue
            records.append(empty_record(model, f"product page could not be read: {error}"))
            report["fetch_failed"] += 1
            continue
        if response.status != 200:
            records.append(empty_record(model, f"product page answered HTTP {response.status}"))
            report["fetch_failed"] += 1
            continue
        title = _page_title(response.text)
        if allowed is not None and not names_model(text_tokens(title), model):
            # Same check as the reviews (decision 15): Topo's URL ".../mens-pursuit" has no
            # version, but its title says "Pursuit 3", which is not our "Pursuit".
            reason = f"page title names another model or version: {title[:60]!r}; check by hand"
            records.append(empty_record(model, reason))
            report["title_mismatch"] += 1
            continue
        women = bool(config.get("women_hint")) and bool(re.search(config["women_hint"], url))
        wide = wide_candidate(candidates)
        record, rejected = record_from_page(
            model,
            url,
            response.text,
            response.retrieved_at,
            women,
            (wide.url, wide.sitemap_url) if wide else None,
            choice.extra_tokens,
        )
        report["found"] += 1
        report["rejected_values"] += len(rejected)
        records.append(record)
    return records, report


def add_retailer_fallback(records: dict[str, ModelSpecs], catalog: InterimCatalog) -> None:
    """Fill `retailer_fallback` of every record from the retailers' cached pages (no network)."""
    adapter = TypeAdapter(list[RetailerListing])
    listings = {
        str(item.product_url): item for item in adapter.validate_json(LISTINGS_PATH.read_bytes())
    }
    clients = {item.retailer.value: PoliteClient(item.retailer.value) for item in listings.values()}

    def page_of(retailer: str, url: str) -> str | None:
        cached = clients[retailer].read_cached(url)
        return cached.text if cached else None

    verifier = PageVerifier(page_of)
    for model in catalog.models:
        if model.id in records:
            fallback = build_fallback(model, listings, verifier)
            records[model.id] = records[model.id].model_copy(update={"retailer_fallback": fallback})


def fold_name(brand: str) -> str:
    """'La Sportiva' -> 'la-sportiva' (cache folder name)."""
    return re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")


def main(argv: list[str] | None = None) -> int:
    """Run phase 3 for all brands (or one) and write specs.json and the coverage page."""
    parser = argparse.ArgumentParser(description="Phase 3: manufacturer specs.")
    parser.add_argument("--brand", help="only this brand (others are kept from specs.json)")
    parser.add_argument("--refresh", action="store_true", help="ignore the cache in data/raw/")
    parser.add_argument(
        "--retailer-only",
        action="store_true",
        help="only rebuild the retailer fallback of the existing specs.json (no network)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    catalog = InterimCatalog.model_validate_json(CATALOG_PATH.read_bytes())
    brands_config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["brands"]
    existing = (
        InterimSpecs.model_validate_json(SPECS_PATH.read_bytes()).models
        if SPECS_PATH.exists()
        else {}
    )
    by_brand: dict[str, list[CanonicalModel]] = {}
    for model in catalog.models:
        by_brand.setdefault(model.brand, []).append(model)

    records: dict[str, ModelSpecs] = dict(existing) if args.retailer_only else {}
    for brand, models in sorted(by_brand.items()):
        if args.retailer_only:
            break
        if args.brand and brand.lower() != args.brand.lower():
            records.update({m.id: existing[m.id] for m in models if m.id in existing})
            continue
        config = brands_config.get(brand)
        if config is None or config["status"] != "allowed":
            reason = (
                f"manufacturer site not collected: {config['reason']}"
                if config
                else "manufacturer site not checked yet (brand missing from manufacturers.yaml)"
            )
            records.update({m.id: empty_record(m, reason) for m in models})
            continue
        brand_records, report = collect_brand(brand, config, models, args.refresh)
        records.update({r.model_id: r for r in brand_records})
        log.info("%s: %d models, %s", brand, len(models), dict(report))

    add_retailer_fallback(records, catalog)
    specs = InterimSpecs(
        generated_at=dt.datetime.now(dt.UTC).replace(microsecond=0), models=records
    )
    SPECS_PATH.write_text(specs.model_dump_json(indent=1) + "\n", encoding="utf-8")
    write_coverage(specs, SPEC_FIELDS, COVERAGE_PATH)
    found = sum(r.manufacturer_url is not None for r in records.values())
    log.info("%d models, %d with a manufacturer page; wrote %s", len(records), found, SPECS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
