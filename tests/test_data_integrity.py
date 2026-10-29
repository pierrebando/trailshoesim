"""Integrity of the committed data and of the repository content (not of the code).

These tests read data/processed/ and the files tracked by git. They fail when the data
the web app ships breaks a project rule: schema, duplicates, prices, ratings,
provenance, excerpt length, raw HTML or full third-party text in the repository.
"""

import csv
import json
import re
import subprocess
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SHOES_PATH = ROOT / "data" / "processed" / "shoes.json"
MAX_WORDS = 30
# A trail shoe sold below 20 EUR or above 400 EUR in France would be a parsing error.
PRICE_RANGE = (20, 400)

pytestmark = pytest.mark.skipif(not SHOES_PATH.exists(), reason="data/processed not built")


@pytest.fixture(scope="module")
def catalog() -> dict:
    return json.loads(SHOES_PATH.read_text(encoding="utf-8"))


def tracked_files() -> list[str]:
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip("not a git checkout")
    return result.stdout.split()


def test_shoes_json_matches_the_schemas(catalog: dict) -> None:
    def schema(name: str) -> dict:
        return json.loads((ROOT / "schema" / name).read_text(encoding="utf-8"))

    jsonschema.validate(catalog, schema("catalog.schema.json"))
    shoe_schema = jsonschema.Draft202012Validator(schema("shoe.schema.json"))
    for shoe in catalog["shoes"]:
        shoe_schema.validate(shoe)


def test_no_duplicated_ids_or_models(catalog: dict) -> None:
    ids = [s["id"] for s in catalog["shoes"]]
    assert len(ids) == len(set(ids))
    keys = [
        (s["brand"].lower(), s["model"].lower(), (s["version"] or "").lower())
        for s in catalog["shoes"]
    ]
    duplicates = {k for k in keys if keys.count(k) > 1}
    assert not duplicates, duplicates


def test_prices_and_ratings_are_plausible(catalog: dict) -> None:
    low, high = PRICE_RANGE
    for shoe in catalog["shoes"]:
        for offer in shoe["retail"]:
            assert low <= offer["price_eur"] <= high, (shoe["id"], offer["price_eur"])
            if offer["rating"] is not None:
                assert 0 <= offer["rating"] <= 5 and offer["review_count"] > 0
        mean = shoe["buyer_rating"]["bayesian_mean_0_5"]
        assert mean is None or 0 <= mean <= 5


def test_every_known_spec_has_a_source_url_and_date(catalog: dict) -> None:
    for shoe in catalog["shoes"]:
        for field, spec in shoe["specs"].items():
            if field == "sources" or spec["value"] is None:
                continue
            assert spec["source_url"] and spec["retrieved_at"], (shoe["id"], field)
            assert field in shoe["specs"]["sources"], (shoe["id"], field)


def test_expert_excerpts_are_short_and_linked(catalog: dict) -> None:
    for shoe in catalog["shoes"]:
        for review in shoe["expert_reviews"]:
            assert review["url"].startswith("https://"), shoe["id"]
            texts = [review["conclusion_excerpt"] or ""]
            texts += [a["evidence_excerpt"] for a in review["aspects"].values()]
            for text in texts:
                assert len(text.split()) <= MAX_WORDS, (shoe["id"], text[:60])


def test_repository_has_no_raw_html_outside_fictional_fixtures() -> None:
    for path in tracked_files():
        if not re.search(r"\.html?$", path):
            continue
        if path == "web/index.html":
            continue  # the app's own page
        assert path.startswith("tests/fixtures/"), path
        text = (ROOT / path).read_text(encoding="utf-8").lower()
        assert "fictional" in text, f"{path}: fixtures must be hand-written and say so"
    assert [p for p in tracked_files() if p.startswith("data/raw/")] == ["data/raw/README.md"]


# Committed fields allowed to be longer than 30 words: our own text, or lists of short
# items joined with " || " (each item is checked separately).
OWN_TEXT_FIELDS = {"missing_reason", "notes", "reason", "match_note", "note"}
JOINED_FIELDS = {"raw_titles", "excerpts", "retailer_urls", "review_urls"}


def _strings(value: object, key: str = ""):
    if isinstance(value, str):
        yield key, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v, key)


def test_no_full_third_party_text_in_committed_data() -> None:
    too_long = []
    for path in tracked_files():
        if not path.startswith("data/") or not path.endswith((".json", ".csv")):
            continue
        full = ROOT / path
        if path.endswith(".json"):
            items = _strings(json.loads(full.read_text(encoding="utf-8")))
        else:
            with full.open(encoding="utf-8") as file:
                items = [(k, v) for row in csv.DictReader(file) for k, v in row.items() if v]
        for key, text in items:
            if key in OWN_TEXT_FIELDS or text.startswith("http"):
                continue
            parts = text.split(" || ") if key in JOINED_FIELDS else [text]
            too_long += [(path, key, p[:50]) for p in parts if len(p.split()) > MAX_WORDS]
    assert not too_long, too_long[:5]


def test_no_long_quotes_in_markdown() -> None:
    long_quotes = []
    for path in tracked_files():
        if not path.endswith(".md"):
            continue
        text = (ROOT / path).read_text(encoding="utf-8")
        quotes = re.findall(r"[\"“]([^\"”\n]{100,})[\"”]", text) + re.findall(
            r"^> (.+)$", text, re.M
        )
        long_quotes += [(path, q[:50]) for q in quotes if len(q.split()) > MAX_WORDS]
    assert not long_quotes, long_quotes
