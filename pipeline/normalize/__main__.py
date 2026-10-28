"""Phase 2: turn retailer listings into one record per canonical model.

    python -m pipeline.normalize

Reads  data/interim/retailer_listings.json (phase 1) and needs_review.csv decisions.
Writes data/interim/catalog.json, needs_review.csv and normalize_report.json.

Steps: filter (kids, not in stock, no price) -> parse titles -> exact keys -> fuzzy
proposals + review decisions -> models -> version flags -> Bayesian buyer rating.
"""

import datetime as dt
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

import yaml
from pydantic import TypeAdapter

from pipeline.models import (
    CanonicalModel,
    Gender,
    InterimCatalog,
    ModelOffer,
    RetailerListing,
    VariantFlags,
)
from pipeline.normalize.apply_review import load_decisions, write_review_csv
from pipeline.normalize.brands import fold
from pipeline.normalize.matching import (
    Proposal,
    flag_proposals,
    fuzzy_proposals,
    is_accepted,
    resolve,
    split_key,
)
from pipeline.normalize.ratings import bayesian_summary, catalogue_prior, rating_pairs
from pipeline.normalize.titles import TITLES_PATH, ParsedTitle, parse_title
from pipeline.normalize.versions import line_key, version_order

INTERIM_DIR = Path(__file__).resolve().parents[2] / "data" / "interim"
log = logging.getLogger("pipeline.normalize")


@dataclass
class _Item:
    listing: RetailerListing
    parsed: ParsedTitle


def slugify(key: str) -> str:
    """'altra|lone peak|9+' -> 'altra-lone-peak-9-plus'."""
    text = key.replace("+", " plus").replace("|", " ")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_listing(listing: RetailerListing) -> ParsedTitle:
    """Parse a listing, preferring the retailer's clean model name when it has one.

    Glisshop titles end with marketing colour names ("Prodigio Yellow Black") but its
    product pages give the model name alone ("Prodigio"). The key comes from that clean
    name; variants, gender and kids/gravel hints still come from the full title.
    """
    full = parse_title(listing.raw_title, listing.brand)
    parsed = parse_title(listing.model_name, listing.brand) if listing.model_name else full
    retailer_hints = " ".join([*listing.category_breadcrumb, *listing.attributes.values()])
    category = full.category if full.category != "trail" else parsed.category
    if category == "trail" and "gravel" in fold(retailer_hints):
        category = "gravel"
    return replace(
        parsed,
        raw_title=listing.raw_title,
        variants=parsed.variants | full.variants,
        gender=parsed.gender or full.gender,
        category=category,
    )


def _keep(item: _Item, dropped: Counter, kids_labels: set[str]) -> bool:
    """Filter: only adult trail/gravel shoes that can be bought now."""
    gender_label = fold(item.listing.gender_raw or "")
    if item.parsed.category == "kids" or gender_label in kids_labels:
        dropped["kids"] += 1
    elif item.listing.in_stock is False:
        dropped["not_in_stock"] += 1
    elif item.listing.price_eur is None:
        dropped["no_price"] += 1
    else:
        return True
    return False


def _offer(item: _Item) -> ModelOffer:
    listing, parsed = item.listing, item.parsed
    return ModelOffer(
        retailer=listing.retailer,
        url=listing.product_url,
        retailer_product_id=listing.retailer_product_id,
        raw_title=listing.raw_title,
        title_key=parsed.key,
        # The retailer's own gender field is more reliable than words in the title.
        gender=listing.gender or parsed.gender,
        variant=VariantFlags(**{name: True for name in parsed.variants}),
        price_eur=listing.price_eur,
        in_stock=listing.in_stock,
        rating=listing.rating,
        review_count=listing.review_count,
        retrieved_at=listing.retrieved_at,
    )


def _display_name(final_key: str, items: list[_Item]) -> tuple[str, str]:
    """Brand and model as they should be shown: the most common spelling in the titles."""
    exact = [item for item in items if item.parsed.key == final_key]
    if not exact:  # a human renamed the model to a key no title produces
        brand_key, model_key, _ = split_key(final_key)
        brands = Counter(item.parsed.brand for item in items if item.parsed.brand)
        return (brands.most_common(1)[0][0] if brands else brand_key.title()), model_key.title()
    brand = Counter(item.parsed.brand or "?" for item in exact).most_common(1)[0][0]
    model = Counter(item.parsed.model for item in exact).most_common(1)[0][0]
    return brand, model


@dataclass
class Phase2Result:
    """Everything phase 2 produces, before it is written to disk."""

    catalog: InterimCatalog
    report: dict
    proposals: list[Proposal]
    listings_by_title_key: dict[str, list[_Item]]


def build(listings: list[RetailerListing], review_path: Path) -> Phase2Result:
    """Run phase 2 in memory, without writing anything."""
    title_config = yaml.safe_load(TITLES_PATH.read_text(encoding="utf-8"))
    thresholds = title_config["matching"]
    kids_labels = set(title_config["kids_gender_labels"])
    dropped: Counter = Counter()
    items = [_Item(listing, parse_listing(listing)) for listing in listings]
    items = [item for item in items if _keep(item, dropped, kids_labels)]

    by_title_key: dict[str, list[_Item]] = defaultdict(list)
    warnings: dict[str, set[str]] = defaultdict(set)
    for item in items:
        by_title_key[item.parsed.key].append(item)
        warnings[item.parsed.key].update(item.parsed.warnings)
    counts = {key: len(group) for key, group in by_title_key.items()}

    proposals = fuzzy_proposals(
        counts, thresholds["fuzzy_merge_threshold"], thresholds["fuzzy_review_threshold"]
    ) + flag_proposals(counts, warnings)
    decisions = load_decisions(review_path)
    final_key_of, fuzzy_keys = resolve(counts, proposals, decisions)

    by_final_key: dict[str, list[_Item]] = defaultdict(list)
    for title_key, group in by_title_key.items():
        by_final_key[final_key_of[title_key]].extend(group)

    flags_of: dict[str, list[str]] = defaultdict(list)
    for proposal in proposals:
        for key in {*proposal.keys, proposal.proposed_key}:
            flags_of[final_key_of.get(key, key)].append(f"{proposal.reason}:{proposal.review_id}")

    all_offers = {key: [_offer(i) for i in group] for key, group in by_final_key.items()}
    prior = catalogue_prior([p for offers in all_offers.values() for p in rating_pairs(offers)])

    models = []
    for final_key, group in sorted(by_final_key.items()):
        offers = sorted(all_offers[final_key], key=lambda o: str(o.url))
        brand, model = _display_name(final_key, group)
        version = split_key(final_key)[2] or None
        categories = {i.parsed.category for i in group}
        models.append(
            {
                "id": slugify(final_key),
                "key": final_key,
                "brand": brand,
                "model": model,
                "version": version,
                "category": "gravel" if categories == {"gravel"} else "trail",
                "gender_variants": sorted(
                    {o.gender for o in offers if o.gender}, key=list(Gender).index
                ),
                "variants": VariantFlags(
                    **{
                        name: any(getattr(o.variant, name) for o in offers)
                        for name in VariantFlags.model_fields
                    }
                ),
                "match_confidence": "fuzzy" if final_key in fuzzy_keys else "exact",
                "retailers": sorted({o.retailer for o in offers}),
                "offers": offers,
                "buyer_rating": bayesian_summary(rating_pairs(offers), prior),
                "review_flags": sorted(set(flags_of.get(final_key, []))),
            }
        )
    _mark_versions(models)
    catalog = InterimCatalog(
        generated_at=dt.datetime.now(dt.UTC).replace(microsecond=0),
        listings_in=len(listings),
        models=[CanonicalModel(**m) for m in models],
    )
    report = _report(catalog, dropped, proposals, decisions, fuzzy_keys, thresholds)
    return Phase2Result(catalog, report, proposals, by_title_key)


def _mark_versions(models: list[dict]) -> None:
    """Flag older versions of a line that are still on sale next to a newer one (spec task 2)."""
    lines: dict[str, list[dict]] = defaultdict(list)
    for model in models:
        lines[line_key(model["key"])].append(model)
    for members in lines.values():
        numbered = [m for m in members if m["version"]]
        latest = max(numbered, key=lambda m: version_order(m["version"]), default=None)
        for model in members:
            model["is_latest_version"] = None
            model["is_discounted_old_version"] = False
            model["newer_version_id"] = None
            if latest is None or len(numbered) < 2 or not model["version"]:
                continue  # single version, or version unknown: we cannot compare
            model["is_latest_version"] = model is latest
            if model is not latest:
                model["newer_version_id"] = latest["id"]
                cheapest = min(o.price_eur for o in model["offers"])
                latest_cheapest = min(o.price_eur for o in latest["offers"])
                model["is_discounted_old_version"] = cheapest < latest_cheapest


def _report(catalog, dropped, proposals, decisions, fuzzy_keys, thresholds) -> dict:
    models = catalog.models
    fuzzy = [p for p in proposals if p.reason in ("fuzzy_merge", "possible_duplicate")]
    merge_at = thresholds["fuzzy_merge_threshold"]
    uncertain = sorted(fuzzy, key=lambda p: abs(p.score - merge_at))[:15]
    return {
        "listings_in": catalog.listings_in,
        "dropped": dict(dropped),
        "listings_used": sum(len(m.offers) for m in models),
        "models_out": len(models),
        "models_exact": sum(m.match_confidence == "exact" for m in models),
        "models_fuzzy": len(fuzzy_keys),
        "fuzzy_merges_applied": sum(is_accepted(p, decisions) for p in fuzzy),
        "review_rows_by_reason": dict(Counter(p.reason for p in proposals)),
        "decisions_applied": len(decisions),
        "most_uncertain_matches": [
            {"score": p.score, "merged": p.applied_by_default, "keys": list(p.keys)}
            for p in uncertain
        ],
        "brands": dict(Counter(m.brand for m in models).most_common()),
        "models_by_retailer_count": dict(Counter(len(m.retailers) for m in models)),
        "old_versions_on_sale": sum(m.is_latest_version is False for m in models),
        "discounted_old_versions": sum(m.is_discounted_old_version for m in models),
        "prior_mean_0_5": models[0].buyer_rating.prior_mean_0_5 if models else None,
    }


def main(interim_dir: Path = INTERIM_DIR) -> int:
    """Read phase 1 output, write phase 2 output."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    listings_path = interim_dir / "retailer_listings.json"
    review_path = interim_dir / "needs_review.csv"
    listings = TypeAdapter(list[RetailerListing]).validate_json(listings_path.read_bytes())

    result = build(listings, review_path)
    report, groups = result.report, result.listings_by_title_key

    (interim_dir / "catalog.json").write_text(result.catalog.model_dump_json(indent=1) + "\n")
    rows = write_review_csv(
        review_path,
        result.proposals,
        {key: sorted({i.listing.raw_title for i in group}) for key, group in groups.items()},
        {key: sorted({str(i.listing.product_url) for i in group}) for key, group in groups.items()},
        load_decisions(review_path),
    )
    (interim_dir / "normalize_report.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    )
    log.info(
        "%d listings -> %d models (%d fuzzy); %d rows in needs_review.csv",
        report["listings_in"],
        report["models_out"],
        report["models_fuzzy"],
        rows,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
