"""The generic sub-score evaluator of docs/scoring-spec.md, sections 0.3 and 0.4.

A sub-score is a weighted mean of inputs, each turning one spec value into 0-10:

* `anchors`: piecewise-linear interpolation (`interp`);
* `lookup: <table>.<attr>`: a foam / rubber name matched to a class, or a plate type;
* `table`: a direct mapping of a categorical value;
* `transform: count` + `anchors`: the number of items of a list;
* `fallback: {field, anchors}`: used only when the main field is null.

Missing inputs are dropped and the remaining weights re-normalised; the share of weight
that was known is the coverage. Nothing here ever replaces a missing value.
"""

from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

Anchors = list[list[float]]


def interp(x: float, anchors: Anchors) -> float:
    """Piecewise-linear interpolation, held constant outside the anchors (spec §0.3)."""
    xs = [a[0] for a in anchors]
    if any(b <= a for a, b in pairwise(xs)):
        raise ValueError(f"anchors must have strictly increasing x: {anchors}")
    if x <= anchors[0][0]:
        return float(anchors[0][1])
    if x >= anchors[-1][0]:
        return float(anchors[-1][1])
    for (x1, y1), (x2, y2) in pairwise(anchors):
        if x1 <= x <= x2:
            return y1 + (x - x1) * (y2 - y1) / (x2 - x1)
    raise AssertionError("unreachable: x is inside the anchors")


def lookup_class(text: str, rules: list[dict]) -> str | None:
    """Class of a free-text foam / rubber name: the FIRST rule with a matching substring."""
    lowered = text.lower()
    for rule in rules:
        if any(word in lowered for word in rule["match"]):
            return rule["class"]
    return None  # unknown compound: the input is missing, not "average"


@dataclass
class InputResult:
    """One input of a sub-score, as evaluated."""

    name: str  # e.g. "specs.lug_depth_mm" (the field actually used, fallback included)
    weight: float  # weight from the YAML
    value: Any = None  # the spec value read (None = missing)
    score: float | None = None  # 0-10, None when missing
    label: str = ""  # readable value, e.g. "Vibram Megagrip (premium_sticky)"


@dataclass
class SubScore:
    """Result of the evaluator: score (or None), coverage and every input."""

    score: float | None
    coverage: float
    inputs: list[InputResult] = field(default_factory=list)

    @property
    def used(self) -> list[InputResult]:
        """Inputs with a known value."""
        return [i for i in self.inputs if i.score is not None]

    @property
    def missing(self) -> list[InputResult]:
        """Inputs without a known value."""
        return [i for i in self.inputs if i.score is None]


def evaluate_input(name: str, spec: dict, values: dict[str, Any], lookups: dict) -> InputResult:
    """Turn the spec value `values[name]` into 0-10 with the rule `spec` (one YAML input)."""
    result = InputResult(name=f"specs.{name}", weight=float(spec["weight"]))
    value = values.get(name)
    anchors = spec.get("anchors")
    if value is None and "fallback" in spec:
        name = spec["fallback"]["field"]
        value = values.get(name)
        anchors = spec["fallback"]["anchors"]
        result.name = f"specs.{name}"
    result.value = value
    if value is None:
        return result

    if "lookup" in spec:
        table, attribute = spec["lookup"].split(".")
        if table == "plate_classes":
            klass = str(value)
            attributes = lookups["plate_classes"].get(klass)
        else:
            klass = lookup_class(str(value), lookups[table]["rules"])
            attributes = lookups[table]["classes"].get(klass) if klass else None
        if attributes is None:
            result.label = f"{value} (no matching class)"
            return result
        result.score = float(attributes[attribute])
        result.label = f"{value} ({klass})" if table != "plate_classes" else str(value)
    elif "table" in spec:
        if str(value) not in spec["table"]:
            result.label = f"{value} (not in table)"
            return result
        result.score = float(spec["table"][str(value)])
        result.label = str(value)
    elif spec.get("transform") == "count":
        result.score = interp(len(value), anchors)
        result.label = f"{len(value)} ({', '.join(map(str, value))})"
    else:
        result.score = interp(float(value), anchors)
        result.label = f"{value:g}" if isinstance(value, float) else str(value)
    return result


def evaluate(
    inputs: dict[str, dict],
    values: dict[str, Any],
    lookups: dict,
    min_coverage: float,
    required: tuple[str, ...] = (),
) -> SubScore:
    """Weighted mean of the known inputs (spec §0.4); None if coverage is too low."""
    results = [evaluate_input(name, spec, values, lookups) for name, spec in inputs.items()]
    total = sum(r.weight for r in results)
    known = [r for r in results if r.score is not None]
    known_weight = sum(r.weight for r in known)
    coverage = known_weight / total if total else 0.0
    required_missing = any(values.get(name) is None for name in required)
    if not known or coverage < min_coverage or required_missing:
        return SubScore(None, coverage, results)
    score = sum(r.weight * r.score for r in known) / known_weight
    return SubScore(score, coverage, results)
