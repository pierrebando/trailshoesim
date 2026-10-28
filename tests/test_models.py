"""The pydantic models accept a valid record and enforce the project's data rules."""

import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from pipeline.models import MAX_EXCERPT_WORDS, AspectAssessment, Shoe, SourcedFloat

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "fictional_shoe.json"
SHOE_SCHEMA = ROOT / "schema" / "shoe.schema.json"


@pytest.fixture
def shoe_data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fictional_shoe_is_valid(shoe_data: dict) -> None:
    shoe = Shoe.model_validate(shoe_data)
    assert shoe.specs.plate.value == "rock_plate"


def test_serialised_shoe_matches_json_schema(shoe_data: dict) -> None:
    # Round-trip through the model so we check what the pipeline will actually write.
    written = json.loads(Shoe.model_validate(shoe_data).model_dump_json())
    schema = json.loads(SHOE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(written)


def test_missing_value_requires_a_reason() -> None:
    with pytest.raises(ValidationError, match="missing_reason"):
        SourcedFloat(value=None)


def test_known_value_requires_provenance() -> None:
    with pytest.raises(ValidationError, match="source_name"):
        SourcedFloat(value=4.0, source_name="example.com")


def test_long_excerpt_is_rejected() -> None:
    too_long = " ".join(["word"] * (MAX_EXCERPT_WORDS + 1))
    with pytest.raises(ValidationError, match="excerpt has"):
        AspectAssessment(score_0_10=5, evidence_excerpt=too_long, mention_count=1)


def test_unknown_field_is_rejected(shoe_data: dict) -> None:
    shoe_data["colour"] = "red"
    with pytest.raises(ValidationError, match="colour"):
        Shoe.model_validate(shoe_data)


def test_rating_without_reviews_is_rejected(shoe_data: dict) -> None:
    shoe_data["retail"][1]["rating"] = 4.0  # this offer has review_count 0
    with pytest.raises(ValidationError, match="review_count"):
        Shoe.model_validate(shoe_data)
