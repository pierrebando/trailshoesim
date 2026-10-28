"""Make the blind labelling sheet for the phase 5 evaluation.

    python -m pipeline.nlp.make_labeling_sheet

Picks ~30 models that have at least one review, stratified by number of reviewing
sources (1, 2, 3) and spread across brands (fixed random seed, so the sample is
reproducible), and writes:

* data/interim/gold_labels.csv (committed): one row per model, with the review links and
  our <=30-word excerpts, and one EMPTY column per criterion to fill with
  low / medium / high / not mentioned;
* data/raw/reviews/labeling_texts.md (gitignored, local only): the full conclusions and
  pros/cons to read while labelling (third-party text, never committed).

The sheet is blind: it does not show the model's scores, so they cannot bias the labels.
"""

import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from pipeline.models import Criterion, InterimCatalog, InterimReviews

ROOT = Path(__file__).resolve().parents[2]
REVIEWS_PATH = ROOT / "data" / "interim" / "expert_reviews.json"
CATALOG_PATH = ROOT / "data" / "interim" / "catalog.json"
CONCLUSIONS_PATH = ROOT / "data" / "raw" / "reviews" / "conclusions.json"
SHEET_PATH = ROOT / "data" / "interim" / "gold_labels.csv"
TEXTS_PATH = ROOT / "data" / "raw" / "reviews" / "labeling_texts.md"
SEED = 20261028
# Models to draw per number of reviewing sources (more weight on multi-source models,
# where aggregation across reviews is also tested).
QUOTA = {1: 16, 2: 12, 3: 2}
LABELS = "low / medium / high / not mentioned"


def pick_models(reviews: InterimReviews, catalog: InterimCatalog) -> list[str]:
    """Stratified sample: per number of sources, round-robin over brands."""
    brand_of = {m.id: m.brand for m in catalog.models}
    rng = random.Random(SEED)
    picked: list[str] = []
    for n_sources, quota in QUOTA.items():
        by_brand: dict[str, list[str]] = defaultdict(list)
        for model_id, found in sorted(reviews.models.items()):
            if len({r.source for r in found}) == n_sources:
                by_brand[brand_of[model_id]].append(model_id)
        for ids in by_brand.values():
            rng.shuffle(ids)
        brands = sorted(by_brand)
        rng.shuffle(brands)
        chosen: list[str] = []
        while len(chosen) < quota and any(by_brand.values()):
            for brand in brands:  # one model per brand per round: spread across brands
                if by_brand[brand] and len(chosen) < quota:
                    chosen.append(by_brand[brand].pop())
        picked += chosen
    return picked


def main(argv: list[str] | None = None) -> int:
    """Write the sheet and the local reading file."""
    reviews = InterimReviews.model_validate_json(REVIEWS_PATH.read_bytes())
    catalog = InterimCatalog.model_validate_json(CATALOG_PATH.read_bytes())
    texts = json.loads(CONCLUSIONS_PATH.read_text(encoding="utf-8"))
    models = {m.id: m for m in catalog.models}
    picked = pick_models(reviews, catalog)
    if SHEET_PATH.exists():
        print(f"{SHEET_PATH} already exists: not overwritten (labels may be in it).")
        return 1

    criteria = [c.value for c in Criterion]
    with SHEET_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        header = ["model_id", "brand", "model", "sources", "review_urls", "excerpts"]
        writer.writerow([*header, *criteria, "labelled_by", "notes"])
        for model_id in picked:
            found = reviews.models[model_id]
            model = models[model_id]
            name = f"{model.model} {model.version or ''}".strip()
            writer.writerow([
                model_id, model.brand, name,
                " ".join(sorted({r.source for r in found})),
                " ".join(str(r.url) for r in found),
                " || ".join(r.conclusion_excerpt or "" for r in found),
                *[""] * len(criteria), "", "",
            ])  # fmt: skip

    lines = [
        "# Labelling texts (LOCAL ONLY: third-party text, never commit this file)",
        "",
        f"Fill `data/interim/gold_labels.csv`: for each model and criterion write {LABELS}.",
        "Judge what the REVIEWERS say about the shoe, not what you know about it.",
        "- high / low: the reviews say the shoe is clearly high / low on the criterion",
        "  (fit_width: high = roomy/wide, low = narrow/snug).",
        "- medium: they talk about it and say it is average, or they disagree.",
        "- not mentioned: they do not talk about it.",
        "",
    ]
    for number, model_id in enumerate(picked, 1):
        model = models[model_id]
        lines += [
            f"## {number}. {model_id} ({model.brand} {model.model} {model.version or ''})",
            "",
        ]
        for review in reviews.models[model_id]:
            text = texts.get(str(review.url), {})
            lines += [f"### {review.source} — {review.url}", ""]
            lines += [text.get("conclusion") or "(no conclusion found)", ""]
            if text.get("pros"):
                lines += ["**Pros:** " + " | ".join(text["pros"]), ""]
            if text.get("cons"):
                lines += ["**Cons:** " + " | ".join(text["cons"]), ""]
    TEXTS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {SHEET_PATH} ({len(picked)} models) and {TEXTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
