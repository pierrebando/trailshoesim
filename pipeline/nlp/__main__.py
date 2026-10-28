"""Phase 5: aspect scores (0-10) per model and criterion from the review conclusions.

    python -m pipeline.nlp

Reads  data/interim/expert_reviews.json (which reviews belong to which model) and
       data/raw/reviews/conclusions.json (full conclusions, local cache from phase 4).
Writes data/interim/expert_aspects.json.

Pipeline: sentences.py (stage 1) -> aspects.py match (stage 2, embedding model) and
direction (stage 3, NLI model) -> per-review aggregation -> per-model aggregation
weighted by source reliability (scoring.yaml expert_reviews.source_weights).
"""

import datetime as dt
import json
import logging
import sys
from pathlib import Path

from pipeline.models import Criterion, InterimAspects, InterimReviews
from pipeline.nlp.aspects import (
    AspectMatcher,
    SentenceTransformerEmbedder,
    TransformersNLI,
    aggregate,
    load_config,
)
from pipeline.nlp.sentences import review_sentences
from pipeline.reviews.common import excerpt_of
from pipeline.utils.config import load_scoring_config

ROOT = Path(__file__).resolve().parents[2]
REVIEWS_PATH = ROOT / "data" / "interim" / "expert_reviews.json"
CONCLUSIONS_PATH = ROOT / "data" / "raw" / "reviews" / "conclusions.json"
ASPECTS_OUT = ROOT / "data" / "interim" / "expert_aspects.json"
log = logging.getLogger("pipeline.nlp")


def review_aspects(matcher: AspectMatcher, url: str, source: str, text: dict) -> dict:
    """ReviewAspects fields for one review."""
    config = matcher.config
    pros, cons = (
        (text.get("pros") or [], text.get("cons") or []) if config.use_pros_cons else ([], [])
    )
    sentences = review_sentences(text.get("conclusion"), pros, cons)
    found = aggregate(matcher.match(sentences), config)
    aspects = {
        criterion: {
            "score_0_10": result["score_0_10"],
            "evidence_excerpt": excerpt_of(result["evidence"]),
            "source": source,
            "review_url": url,
            "n_sentences": result["n_sentences"],
            "n_reviews": 1,
            "_relevance": result["relevance"],  # used to pick the model-level evidence
        }
        for criterion, result in found.items()
    }
    return {
        "source": source,
        "review_url": url,
        "n_sentences_read": len(sentences),
        "aspects": aspects,
    }


def combine(reviews: list[dict], weights: dict[str, float]) -> dict[str, dict | None]:
    """Per criterion: source-weighted mean of the review scores; evidence of the clearest one."""
    combined: dict[str, dict | None] = {}
    for criterion in Criterion:
        found = [r["aspects"][criterion.value] for r in reviews if criterion.value in r["aspects"]]
        if not found:
            combined[criterion.value] = None
            continue
        w = [weights.get(a["source"], 1.0) for a in found]
        best = max(found, key=lambda a: a["_relevance"])
        combined[criterion.value] = {
            **{k: v for k, v in best.items() if k != "_relevance"},
            "score_0_10": round(
                sum(x * a["score_0_10"] for x, a in zip(w, found, strict=True)) / sum(w), 2
            ),
            "n_sentences": sum(a["n_sentences"] for a in found),
            "n_reviews": len(found),
        }
    return combined


def main(argv: list[str] | None = None) -> int:
    """Score every review of expert_reviews.json and write expert_aspects.json."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if not CONCLUSIONS_PATH.exists():
        log.error(
            "missing %s: run `python -m pipeline.reviews --source all` first", CONCLUSIONS_PATH
        )
        return 1
    config = load_config()
    reviews = InterimReviews.model_validate_json(REVIEWS_PATH.read_bytes())
    texts = json.loads(CONCLUSIONS_PATH.read_text(encoding="utf-8"))
    weights = load_scoring_config()["expert_reviews"]["source_weights"]
    embedder = SentenceTransformerEmbedder(config.model_name, config.model_revision)
    nli = None
    if config.direction_method == "nli":
        nli = TransformersNLI(config.nli_model_name, config.nli_model_revision)
    matcher = AspectMatcher(embedder, config, nli)

    models = {}
    for model_id, model_reviews in reviews.models.items():
        per_review = [
            review_aspects(matcher, str(r.url), r.source, texts[str(r.url)])
            for r in model_reviews
            if str(r.url) in texts
        ]
        combined = combine(per_review, weights)
        for review in per_review:  # drop the helper field before validation
            for aspect in review["aspects"].values():
                aspect.pop("_relevance")
        models[model_id] = {"criteria": combined, "reviews": per_review}

    output = InterimAspects(
        generated_at=dt.datetime.now(dt.UTC).replace(microsecond=0),
        nlp_model=config.model_name,
        nlp_model_revision=config.model_revision,
        aspects_config_version=config.version,
        direction_method=config.direction_method,
        direction_model=config.nli_model_name if nli else None,
        direction_model_revision=config.nli_model_revision if nli else None,
        models=models,
    )
    ASPECTS_OUT.write_text(output.model_dump_json(indent=1) + "\n", encoding="utf-8")
    mentioned = sum(a is not None for m in output.models.values() for a in m.criteria.values())
    log.info(
        "%d models, %d (model, criterion) scores; wrote %s", len(models), mentioned, ASPECTS_OUT
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
