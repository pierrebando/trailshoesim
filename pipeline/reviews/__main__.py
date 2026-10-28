"""Phase 4: specialist reviews for every model of data/interim/catalog.json.

    python -m pipeline.reviews --source runrepeat|believe_in_the_run|esprit_trail|all [--refresh]

Writes:
* data/interim/expert_reviews.json (committed): per model, the reviews with metadata,
  ratings on the source's scale, the source's lab values, a <=30-word excerpt, the link;
* data/interim/reviews_needs_review.csv (committed): ambiguous matches, for a human;
* data/raw/reviews/conclusions.json (gitignored, NEVER committed): full conclusions and
  pros/cons, read by phase 5 only;
* the "Expert reviews" block of docs/data-coverage.md.
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

from pipeline.models import CollectedReview, InterimCatalog, InterimReviews, MatchConfidence
from pipeline.reviews import believe_in_the_run, esprit_trail, runrepeat
from pipeline.reviews.common import (
    Match,
    candidate_urls,
    catalogue_modifiers,
    classify,
    excerpt_of,
    reviews_numbered_versions,
)
from pipeline.utils.http import AccessBlockedError, PoliteClient

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "data" / "interim" / "catalog.json"
REVIEWS_PATH = ROOT / "data" / "interim" / "expert_reviews.json"
REVIEW_CSV = ROOT / "data" / "interim" / "reviews_needs_review.csv"
CONCLUSIONS_PATH = ROOT / "data" / "raw" / "reviews" / "conclusions.json"
COVERAGE_PATH = ROOT / "docs" / "data-coverage.md"
SOURCES = {module.SOURCE: module for module in (runrepeat, believe_in_the_run, esprit_trail)}
CSV_COLUMNS = ["review_id", "source", "model_id", "url", "title", "reason", "decision", "notes"]
COVERAGE_START, COVERAGE_END = "<!-- reviews:start -->", "<!-- reviews:end -->"
log = logging.getLogger("pipeline.reviews")


def review_id(source: str, model_id: str, url: str) -> str:
    """Stable id of a (source, model, url) proposal, so decisions survive re-runs."""
    return hashlib.sha1(f"{source}|{model_id}|{url}".encode()).hexdigest()[:10]


def load_csv() -> list[dict]:
    """Rows of reviews_needs_review.csv (none if the file does not exist yet)."""
    if not REVIEW_CSV.exists():
        return []
    with REVIEW_CSV.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def decisions_of(rows: list[dict]) -> dict[str, str]:
    """{review_id: 'accept' | 'reject'} from the CSV. Anything else is an error."""
    decisions = {}
    for row in rows:
        decision = (row.get("decision") or "").strip().lower()
        if decision and decision not in ("accept", "reject"):
            raise ValueError(
                f"{row['review_id']}: decision must be accept or reject, not {decision!r}"
            )
        if decision:
            decisions[row["review_id"]] = decision
    return decisions


def collect_source(module, catalog: InterimCatalog, refresh: bool, decisions: dict[str, str]):
    """(reviews per model, ambiguous rows, conclusions) for one source."""
    client = PoliteClient(f"reviews/{module.SOURCE}", refresh=refresh)
    urls = module.discover(client)
    log.info("%s: %d review URLs", module.SOURCE, len(urls))
    reviews: dict[str, list[CollectedReview]] = {}
    ambiguous: list[dict] = []
    conclusions: dict[str, dict] = {}
    modifiers = catalogue_modifiers(catalog.models)
    numbered_lines = {m.key.rsplit("|", 1)[0] for m in catalog.models if m.version}
    for model in catalog.models:
        # A catalogue model without version (the retailer left it out) could be any
        # version; if the source reviews numbered versions, we cannot tell which one.
        version_unknown = (
            model.version is None
            and model.key.rsplit("|", 1)[0] not in numbered_lines
            and reviews_numbered_versions(model, urls, modifiers)
        )
        for url in candidate_urls(model, urls, modifiers):
            try:
                page = client.get(url)
            except AccessBlockedError:
                raise
            except Exception as error:  # recorded; the other pages continue
                log.warning("%s: %s", url, error)
                continue
            if page.status != 200:
                continue
            parsed = module.parse(page.text)
            match = classify(model, url, parsed.title, modifiers)
            if version_unknown and match.confidence is not None:
                match = Match(
                    url,
                    None,
                    "catalogue model has no version; the source reviews numbered versions",
                )
            rid = review_id(module.SOURCE, model.id, url)
            confidence = match.confidence
            if confidence is None:
                ambiguous.append(
                    {"review_id": rid, "source": module.SOURCE, "model_id": model.id, "url": url,
                     "title": parsed.title, "reason": match.note}
                )  # fmt: skip
                if decisions.get(rid) != "accept":
                    continue
                confidence = MatchConfidence.MANUAL
            lab_values = {
                key: {**value, "source_url": url, "retrieved_at": page.retrieved_at}
                for key, value in parsed.lab_values.items()
            }
            reviews.setdefault(model.id, []).append(
                CollectedReview(
                    source=module.SOURCE,
                    url=url,
                    title=parsed.title,
                    language=module.LANGUAGE,
                    date=dt.date.fromisoformat(parsed.date) if parsed.date else None,
                    retrieved_at=page.retrieved_at,
                    review_match_confidence=confidence,
                    match_note=match.note,
                    ratings=parsed.ratings,
                    lab_values=lab_values,
                    conclusion_excerpt=excerpt_of(parsed.conclusion),
                    conclusion_heading=parsed.conclusion_heading,
                )
            )
            conclusions[url] = {
                "source": module.SOURCE,
                "heading": parsed.conclusion_heading,
                "conclusion": parsed.conclusion,
                "pros": parsed.pros,
                "cons": parsed.cons,
            }
    return reviews, ambiguous, conclusions


def write_csv(rows: list[dict], decisions: dict[str, str], notes: dict[str, str]) -> None:
    """Rewrite reviews_needs_review.csv, carrying over the decisions and notes already made."""
    rows = sorted(rows, key=lambda r: (r["source"], r["model_id"], r["url"]))
    with REVIEW_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "decision": decisions.get(row["review_id"], ""),
                    "notes": notes.get(row["review_id"], row.get("notes", "")),
                }
            )


def coverage_block(data: InterimReviews, catalog: InterimCatalog) -> str:
    """Markdown: tests per model (0-4) and per source."""
    sources = data.sources
    per_model = {m.id: {r.source for r in data.models.get(m.id, [])} for m in catalog.models}
    distribution = Counter(len(found) for found in per_model.values())
    lines = [
        COVERAGE_START,
        "",
        "## Expert reviews (phase 4)",
        "",
        f"Generated {data.generated_at:%Y-%m-%d} from `data/interim/expert_reviews.json` "
        "(`python -m pipeline.reviews --source all`). Doctors of Running is not collected "
        "(robots.txt bans AI crawlers), so at most 3 sources per model.",
        "",
        "| Sources with a review | 0 | 1 | 2 | 3 | 4 |",
        "|---|---|---|---|---|---|",
        "| Models | " + " | ".join(str(distribution.get(n, 0)) for n in range(5)) + " |",
        "",
        "| Source | Models reviewed | of which exact | variant | manual |",
        "|---|---|---|---|---|",
    ]
    for source in sources:
        found = [r for reviews in data.models.values() for r in reviews if r.source == source]
        models = len(
            {
                mid
                for mid, reviews in data.models.items()
                if any(r.source == source for r in reviews)
            }
        )
        kinds = Counter(r.review_match_confidence.value for r in found)
        lines.append(
            f"| {source} | {models} | {kinds.get('exact', 0)} | {kinds.get('variant', 0)} "
            f"| {kinds.get('manual', 0)} |"
        )
    lab = sum(bool(r.lab_values) for reviews in data.models.values() for r in reviews)
    lines += ["", f"Reviews with lab measurements: {lab}.", "", COVERAGE_END]
    return "\n".join(lines)


def write_coverage_block(block: str) -> None:
    """Insert or replace the reviews block of docs/data-coverage.md."""
    text = COVERAGE_PATH.read_text(encoding="utf-8") if COVERAGE_PATH.exists() else ""
    pattern = re.compile(re.escape(COVERAGE_START) + ".*?" + re.escape(COVERAGE_END), re.S)
    text = (
        pattern.sub(block, text) if pattern.search(text) else text.rstrip() + "\n\n" + block + "\n"
    )
    COVERAGE_PATH.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Collect the requested sources and write the phase 4 outputs."""
    parser = argparse.ArgumentParser(description="Phase 4: specialist reviews.")
    parser.add_argument("--source", required=True, choices=[*SOURCES, "all"])
    parser.add_argument("--refresh", action="store_true", help="ignore the cache in data/raw/")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    catalog = InterimCatalog.model_validate_json(CATALOG_PATH.read_bytes())
    to_run = list(SOURCES) if args.source == "all" else [args.source]
    existing = (
        InterimReviews.model_validate_json(REVIEWS_PATH.read_bytes())
        if REVIEWS_PATH.exists()
        else None
    )
    models: dict[str, list[CollectedReview]] = {}
    if existing:  # keep the reviews of the sources not collected in this run
        for model_id, reviews in existing.models.items():
            kept = [r for r in reviews if r.source not in to_run]
            if kept:
                models[model_id] = kept
    old_rows = load_csv()
    decisions = decisions_of(old_rows)
    rows = [row for row in old_rows if row["source"] not in to_run]
    conclusions = json.loads(CONCLUSIONS_PATH.read_text()) if CONCLUSIONS_PATH.exists() else {}
    conclusions = {url: c for url, c in conclusions.items() if c.get("source") not in to_run}

    for source in to_run:
        reviews, ambiguous, texts = collect_source(
            SOURCES[source], catalog, args.refresh, decisions
        )
        for model_id, found in reviews.items():
            models.setdefault(model_id, []).extend(found)
        rows += ambiguous
        conclusions.update(texts)
        log.info("%s: %d models reviewed, %d ambiguous", source, len(reviews), len(ambiguous))

    sources = sorted({r.source for reviews in models.values() for r in reviews} | set(to_run))
    data = InterimReviews(
        generated_at=dt.datetime.now(dt.UTC).replace(microsecond=0),
        sources=sources,
        models={
            mid: sorted(found, key=lambda r: (r.source, str(r.url)))
            for mid, found in sorted(models.items())
        },
    )
    REVIEWS_PATH.write_text(data.model_dump_json(indent=1) + "\n", encoding="utf-8")
    write_csv(rows, decisions, {row["review_id"]: row.get("notes", "") for row in old_rows})
    CONCLUSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONCLUSIONS_PATH.write_text(
        json.dumps(conclusions, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    write_coverage_block(coverage_block(data, catalog))
    log.info("wrote %s (%d models with reviews)", REVIEWS_PATH, len(data.models))
    return 0


if __name__ == "__main__":
    sys.exit(main())
