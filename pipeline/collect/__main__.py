"""Command line entry point for phase 1.

    python -m pipeline.collect --site tradeinn|glisshop|lepape|irun|all [--refresh] [--limit N]

Writes data/interim/retailer_listings.json (validated RetailerListing records) and
data/interim/collect_report.json (counts and failures per site).
"""

import argparse
import datetime as dt
import json
import logging
import sys
from collections.abc import Callable
from pathlib import Path

from pydantic import TypeAdapter

from pipeline.collect import glisshop, tradeinn
from pipeline.collect.common import CollectResult
from pipeline.models import RetailerListing
from pipeline.utils.http import PoliteClient

INTERIM_DIR = Path(__file__).resolve().parents[2] / "data" / "interim"
LISTINGS_PATH = INTERIM_DIR / "retailer_listings.json"
REPORT_PATH = INTERIM_DIR / "collect_report.json"

COLLECTORS: dict[str, Callable[..., CollectResult]] = {
    "tradeinn": tradeinn.collect,
    "glisshop": glisshop.collect,
}

# Sites we must not collect, with the reason (details in docs/sources.md).
BLOCKED_SITES = {
    "lepape": "Cloudflare bot challenge on every page (HTTP 403): automated access refused.",
    "irun": "Terms of sale forbid extracting or reusing any part of the site content.",
}

listings_adapter = TypeAdapter(list[RetailerListing])
log = logging.getLogger("pipeline.collect")


def _load_existing() -> list[RetailerListing]:
    if not LISTINGS_PATH.exists():
        return []
    return listings_adapter.validate_json(LISTINGS_PATH.read_bytes())


def _summary(result: CollectResult, client: PoliteClient) -> dict:
    listings = result.listings
    return {
        "products": len(listings),
        "with_price": sum(item.price_eur is not None for item in listings),
        "with_rating": sum(item.rating is not None for item in listings),
        "with_review_count": sum(item.review_count is not None for item in listings),
        "with_gender": sum(item.gender is not None for item in listings),
        "with_brand": sum(item.brand is not None for item in listings),
        "parsing_failures": len(result.failures),
        "failures": result.failures,
        "excluded_not_trail": len(result.excluded_not_trail),
        "category_pages": result.category_pages,
        "possibly_truncated_category_pages": result.truncated_pages,
        "brands_seen": sorted(result.brands_seen),
        "network_requests": client.network_requests,
        "cache_hits": client.cache_hits,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the requested collectors and write the interim files. Returns an exit code."""
    parser = argparse.ArgumentParser(description="Phase 1: collect retailer listings.")
    parser.add_argument("--site", required=True, choices=[*COLLECTORS, *BLOCKED_SITES, "all"])
    parser.add_argument("--refresh", action="store_true", help="ignore the cache in data/raw/")
    parser.add_argument("--limit", type=int, help="max product pages per site (quick tests)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    requested = [*COLLECTORS, *BLOCKED_SITES] if args.site == "all" else [args.site]
    for site in requested:
        if site in BLOCKED_SITES:
            log.warning("%s skipped: %s See docs/sources.md.", site, BLOCKED_SITES[site])
    to_run = [site for site in requested if site in COLLECTORS]
    if not to_run:
        return 1

    # Keep the records of sites not collected in this run, replace the others.
    listings = [item for item in _load_existing() if item.retailer.value not in to_run]
    report = json.loads(REPORT_PATH.read_text()) if REPORT_PATH.exists() else {}
    for site in to_run:
        client = PoliteClient(site, refresh=args.refresh)
        result = COLLECTORS[site](client, limit=args.limit)
        listings.extend(result.listings)
        report[site] = {"collected_on": dt.date.today().isoformat(), **_summary(result, client)}

    listings.sort(key=lambda item: (item.retailer.value, str(item.product_url)))
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    LISTINGS_PATH.write_bytes(listings_adapter.dump_json(listings, indent=1) + b"\n")
    REPORT_PATH.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    log.info("wrote %d listings to %s", len(listings), LISTINGS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
