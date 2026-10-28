"""Phase 4: review parsers (hand-written fixtures), strict matching, excerpts, decisions."""

from pathlib import Path

import pytest

from pipeline.models import MAX_EXCERPT_WORDS, CanonicalModel, MatchConfidence
from pipeline.reviews import believe_in_the_run, esprit_trail, runrepeat
from pipeline.reviews.__main__ import decisions_of, review_id
from pipeline.reviews.common import candidate_urls, classify, excerpt_of, text_tokens

FIXTURES = Path(__file__).parent / "fixtures" / "reviews"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def model(key: str, brand: str) -> CanonicalModel:
    _, name, version = key.split("|")
    return CanonicalModel.model_validate(
        {
            "id": key.replace("|", "-").replace(" ", "-").strip("-"),
            "key": key,
            "brand": brand,
            "model": name.title(),
            "version": version or None,
            "category": "trail",
            "gender_variants": ["men"],
            "variants": {},
            "match_confidence": "exact",
            "is_latest_version": None,
            "is_discounted_old_version": False,
            "newer_version_id": None,
            "retailers": ["tradeinn"],
            "offers": [
                {
                    "retailer": "tradeinn",
                    "url": "https://example.com/p",
                    "retailer_product_id": None,
                    "raw_title": name,
                    "title_key": key,
                    "gender": "men",
                    "variant": {},
                    "price_eur": 100,
                    "in_stock": True,
                    "rating": None,
                    "review_count": None,
                    "retrieved_at": "2026-10-28",
                }
            ],
            "buyer_rating": {
                "review_count_total": 0,
                "raw_mean_0_5": None,
                "bayesian_mean_0_5": None,
                "prior_mean_0_5": 4.3,
                "prior_strength": 20,
            },
            "review_flags": [],
        }
    )


# --- parsers -----------------------------------------------------------------


def test_runrepeat_parser() -> None:
    review = runrepeat.parse(read("runrepeat.html"))
    assert review.title == "Example Ridge 2 review"
    assert review.date == "2026-05-02"
    assert [(r["label"], r["value"], r["scale"]) for r in review.ratings] == [
        ("Our verdict", "86", "0-100"),
        ("Technical", "91", "0-100"),
        ("Mud", "77", "0-100"),
    ]
    assert review.conclusion.startswith("The Example Ridge 2 is a confident shoe")
    assert review.pros == ["Sticky outsole", "Protective"] and review.cons == ["Heavy"]
    lab = review.lab_values
    assert (lab["stack_heel_mm"]["value"], lab["stack_forefoot_mm"]["value"]) == (32.5, 25.1)
    assert lab["lug_depth_mm"]["value"] == 4.6
    assert lab["weight_g"]["value"] == 295.0  # grams printed by the page, not converted
    assert lab["lug_depth_mm"]["raw_snippet"] == "Lug depth | 4.6 mm | 3.5 mm"
    assert "not manufacturer" in lab["lug_depth_mm"]["source_name"]
    assert "stack_heel_mm" in lab and "Heel height" not in str(lab)  # brand specs ignored


def test_believe_in_the_run_parser() -> None:
    review = believe_in_the_run.parse(read("believe_in_the_run.html"))
    assert review.date == "2026-03-14"
    assert [(r["label"], r["value"]) for r in review.ratings] == [
        ("Design", "B+"),
        ("Value", "A"),
        ("Performance", "B"),
    ]
    assert review.conclusion_heading == "Final thoughts on the EXAMPLE RIDGE 2"
    assert "Comment form" not in review.conclusion  # stops at the comment heading (an h3)
    assert "half size up" not in review.conclusion  # readers' comments are not the review
    assert review.pros == ["The outsole bites into wet rock."]
    assert review.cons == ["It runs warm."]
    assert review.lab_values == {}


def test_esprit_trail_parser() -> None:
    review = esprit_trail.parse(read("esprit_trail.html"))
    assert review.date == "2025-09-01"
    assert review.conclusion_heading.endswith("le verdict")
    assert review.conclusion.startswith("Cette Ridge 2.0 est une vraie réussite.")
    assert review.ratings == []


# --- strict matching -----------------------------------------------------------

SPEEDGOAT_6 = model("hoka|speedgoat|6", "HOKA")
URLS = [
    "https://x.com/shoe-reviews/hoka-speedgoat-5-review/",
    "https://x.com/shoe-reviews/hoka-speedgoat-6-review/",
    "https://x.com/shoe-reviews/hoka-speedgoat-6-gtx-review/",
    "https://x.com/shoe-reviews/hoka-speedgoat-6-vs-salomon-genesis/",
    "https://x.com/shoe-reviews/hoka-speedgoat-review/",
]


def test_speedgoat_5_is_never_attached_to_speedgoat_6() -> None:
    found = candidate_urls(SPEEDGOAT_6, URLS)
    assert URLS[0] not in found and URLS[4] not in found
    assert set(found) == {URLS[1], URLS[2], URLS[3]}


def test_classify_exact_variant_and_ambiguous() -> None:
    exact = classify(SPEEDGOAT_6, URLS[1], "Hoka Speedgoat 6 Review: Still the Goat")
    assert exact.confidence is MatchConfidence.EXACT
    variant = classify(SPEEDGOAT_6, URLS[2], "Hoka Speedgoat 6 GTX Review")
    assert variant.confidence is MatchConfidence.VARIANT
    comparison = classify(SPEEDGOAT_6, URLS[3], "Speedgoat 6 vs Genesis")
    assert comparison.confidence is None and "comparison" in comparison.note
    wrong_title = classify(SPEEDGOAT_6, URLS[1], "Hoka Speedgoat 5 Review")
    assert wrong_title.confidence is None and "title does not confirm" in wrong_title.note


def test_model_without_version_does_not_take_a_numbered_review() -> None:
    tomir = model("nnormal|tomir|", "NNormal")
    urls = ["https://x.com/test-nnormal-tomir-2-0-avis/", "https://x.com/test-nnormal-tomir-avis/"]
    assert candidate_urls(tomir, urls) == ["https://x.com/test-nnormal-tomir-avis/"]


def test_a_longer_model_name_is_another_shoe() -> None:
    prodigio = model("la sportiva|prodigio|", "La Sportiva")
    urls = [
        "https://x.com/shoe-reviews/la-sportiva-prodigio-review/",
        "https://x.com/shoe-reviews/la-sportiva-prodigio-pro-review/",
        "https://x.com/shoe-reviews/la-sportiva-prodigio-max-review/",
    ]
    assert candidate_urls(prodigio, urls) == [urls[0]]
    peregrine = model("saucony|peregrine|13", "Saucony")
    assert candidate_urls(peregrine, ["https://x.com/saucony-peregrine-13-st-review/"]) == []
    free_text = ["https://x.com/test-saucony-peregrine-13-legerete-et-rapidite/"]
    assert candidate_urls(peregrine, free_text) == free_text  # free text after the name is fine
    glide = model("salomon|ultra glide|4", "Salomon")
    assert (
        classify(
            glide,
            "https://x.com/salomon-ultra-glide-4-review/",
            "Salomon Ultra Glide 4: Something for Everyone",
        ).confidence
        is MatchConfidence.EXACT
    )
    genesis = model("salomon|genesis|2", "Salomon")
    assert candidate_urls(genesis, ["https://x.com/salomon-s-lab-genesis-2-review/"]) == []
    assert candidate_urls(genesis, ["https://x.com/salomon-genesis-2-gtx-review/"])  # variant


def test_numbered_versions_are_detected() -> None:
    from pipeline.reviews.common import reviews_numbered_versions

    rebel = model("new balance|rebel|", "New Balance")
    assert reviews_numbered_versions(rebel, ["https://x.com/new-balance-rebel-v3-review/"])
    assert not reviews_numbered_versions(rebel, ["https://x.com/new-balance-rebel-review/"])


def test_catalogue_modifiers_include_family_extensions() -> None:
    from pipeline.reviews.common import catalogue_modifiers

    family = [model("x|kjerag|", "X"), model("x|kjerag brut|", "X")]
    assert "brut" in catalogue_modifiers(family)


def test_optional_leading_words_and_glued_versions() -> None:
    trabuco = model("asics|gel trabuco|14", "Asics")
    assert candidate_urls(trabuco, ["https://runrepeat.com/asics-trabuco-14"])
    ride = model("saucony|ride tr|3", "Saucony")
    assert candidate_urls(ride, ["https://x.com/saucony-ride-tr3-review/"])
    assert text_tokens("Altra Lone Peak 9-plus GTX") == ["altra", "lone", "peak", "9+", "gtx"]


# --- excerpts and decisions ----------------------------------------------------


def test_excerpt_keeps_whole_sentences_within_30_words() -> None:
    text = "First sentence is short. " + " ".join(["word"] * 40) + "."
    assert excerpt_of(text) == "First sentence is short."
    long_first = " ".join(["mot"] * 50) + "."
    excerpt = excerpt_of(long_first)
    assert excerpt.endswith("…") and len(excerpt.split()) <= MAX_EXCERPT_WORDS
    assert excerpt_of("SAM : The shoe is great.") == "The shoe is great."
    assert excerpt_of(None) is None


def test_decisions_and_stable_ids() -> None:
    rows = [{"review_id": "a", "decision": "Accept"}, {"review_id": "b", "decision": ""}]
    assert decisions_of(rows) == {"a": "accept"}
    with pytest.raises(ValueError, match="accept or reject"):
        decisions_of([{"review_id": "c", "decision": "maybe"}])
    assert review_id("s", "m", "u") == review_id("s", "m", "u") != review_id("s", "m", "v")
