"""scoring.yaml must be internally consistent and agree with the data model."""

import json
import math
import re
from pathlib import Path

import pytest

from pipeline.models import Criterion, Specs, TerrainScores
from pipeline.utils.config import load_scoring_config

CONFIG = load_scoring_config()


def _sums_to_one(values: list[float]) -> bool:
    return math.isclose(sum(values), 1.0, abs_tol=1e-9)


def _check_input(name: str, spec: dict) -> None:
    assert name in Specs.model_fields, f"unknown spec field {name!r}"
    anchors = spec.get("anchors")
    if anchors:
        xs = [x for x, _ in anchors]
        assert xs == sorted(xs) and len(set(xs)) == len(xs), f"{name}: anchors x not increasing"
        assert all(0 <= y <= 10 for _, y in anchors), f"{name}: anchor y outside 0-10"
    if "lookup" in spec:
        table, attribute = spec["lookup"].split(".")
        classes = CONFIG["lookups"][table].get("classes", CONFIG["lookups"][table])
        assert all(attribute in values for values in classes.values()), spec["lookup"]
    if "fallback" in spec:
        _check_input(spec["fallback"]["field"], spec["fallback"])


ROOT = Path(__file__).resolve().parents[1]


def test_config_has_a_version() -> None:
    assert CONFIG["version"]


def test_spec_data_and_config_carry_the_same_scoring_version() -> None:
    # docs/scoring-spec.md says "Must match `version` in scoring.yaml"; the web app reads
    # data/processed/scoring_config.json, which must come from the same version.
    spec = (ROOT / "docs" / "scoring-spec.md").read_text(encoding="utf-8")
    assert re.search(r"Version \*\*([0-9.]+)\*\*", spec).group(1) == CONFIG["version"]
    processed = ROOT / "data" / "processed"
    if (processed / "shoes.json").exists():
        shoes = json.loads((processed / "shoes.json").read_text(encoding="utf-8"))
        web_config = json.loads((processed / "scoring_config.json").read_text(encoding="utf-8"))
        assert shoes["scoring_config_version"] == web_config["version"] == CONFIG["version"]


def test_every_criterion_is_configured() -> None:
    assert set(CONFIG["criteria"]) == {c.value for c in Criterion}
    assert set(CONFIG["profile"]["base_weights"]) == {c.value for c in Criterion}


@pytest.mark.parametrize("criterion", [c.value for c in Criterion])
def test_criterion_weights_are_consistent(criterion: str) -> None:
    config = CONFIG["criteria"][criterion]
    assert _sums_to_one(list(config["blend"].values()))
    assert _sums_to_one([spec["weight"] for spec in config["spec_inputs"].values()])
    for name, spec in config["spec_inputs"].items():
        _check_input(name, spec)


def test_every_terrain_is_configured_and_weights_sum_to_one() -> None:
    scores = CONFIG["terrain"]["scores"]
    assert set(scores) == set(TerrainScores.model_fields)
    for inputs in scores.values():
        assert _sums_to_one([spec["weight"] for spec in inputs.values()])
        for name, spec in inputs.items():
            _check_input(name, spec)


def test_lookup_rules_point_to_existing_classes() -> None:
    for table in ("foam_classes", "rubber_classes"):
        classes = CONFIG["lookups"][table]["classes"]
        for rule in CONFIG["lookups"][table]["rules"]:
            assert rule["class"] in classes


def test_load_mix_sums_to_one_and_base_weights_are_positive() -> None:
    assert _sums_to_one(list(CONFIG["profile"]["load_mix"].values()))
    for low, high in CONFIG["profile"]["base_weights"].values():
        assert low > 0 and high > 0


def test_confidence_fields_exist_in_specs() -> None:
    for name in CONFIG["confidence"]["spec_completeness_weights"]:
        assert name in Specs.model_fields
