"""Compare the phase 5 scores with the labels of data/interim/gold_labels.csv.

    python -m pipeline.nlp.evaluate --tag baseline

For each criterion:

* coverage: of the (model, criterion) pairs the labeller says are mentioned, how many the
  pipeline also scores (recall); and how many pipeline scores are on pairs the labeller
  says are NOT mentioned (false mentions);
* accuracy on low / medium / high, on the pairs both consider mentioned;
* Spearman rank correlation between the 0-10 score and the label (low < medium < high);
* a confusion matrix (labels in rows, pipeline in columns, "not mentioned" included).

The 30 models are split in two halves (alternate rows of the stratified sheet): changes to
the method are chosen on the DEV half only, so the TEST half gives an honest number.
The tables are written into docs/evaluation.md between markers named after `--tag`, so
the hand-written comments around them are kept and several runs can be compared.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

from pipeline.models import Criterion, InterimAspects
from pipeline.nlp.aspects import load_config, score_class

ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = ROOT / "data" / "interim" / "gold_labels.csv"
ASPECTS_PATH = ROOT / "data" / "interim" / "expert_aspects.json"
REPORT_PATH = ROOT / "docs" / "evaluation.md"
CLASSES = ["low", "medium", "high"]
ALL_CLASSES = [*CLASSES, "not mentioned"]
ORDER = {"low": 0, "medium": 1, "high": 2}


def ranks(values: list[float]) -> list[float]:
    """Ranks starting at 1; tied values share their average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        for position in range(start, end + 1):
            result[order[position]] = (start + end) / 2 + 1
        start = end + 1
    return result


def spearman(x: list[float], y: list[float]) -> float | None:
    """Spearman correlation = Pearson correlation of the ranks (None if undefined)."""
    if len(x) < 3:
        return None
    rx, ry = ranks(x), ranks(y)
    mean_x, mean_y = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry, strict=True))
    var_x = sum((a - mean_x) ** 2 for a in rx)
    var_y = sum((b - mean_y) ** 2 for b in ry)
    if var_x == 0 or var_y == 0:
        return None
    return cov / (var_x * var_y) ** 0.5


def load_pairs(gold_path: Path, aspects_path: Path) -> list[dict]:
    """One record per (labelled model, criterion): label, pipeline score and class, half."""
    config = load_config()
    aspects = InterimAspects.model_validate_json(aspects_path.read_bytes()).models
    rows = list(csv.DictReader(gold_path.open(encoding="utf-8")))
    pairs = []
    for index, row in enumerate(rows):
        model = aspects.get(row["model_id"])
        for criterion in Criterion:
            label = row[criterion.value].strip().lower()
            if label not in ALL_CLASSES:
                raise ValueError(f"{row['model_id']} {criterion.value}: unknown label {label!r}")
            result = model.criteria.get(criterion) if model else None
            score = result.score_0_10 if result else None
            pairs.append({
                "model_id": row["model_id"],
                "criterion": criterion.value,
                "half": "dev" if index % 2 == 0 else "test",
                "label": label,
                "score": score,
                "predicted": score_class(score, config),
            })  # fmt: skip
    return pairs


def metrics(pairs: list[dict]) -> dict:
    """Coverage, accuracy, Spearman and confusion matrix of a list of pairs."""
    mentioned = [p for p in pairs if p["label"] != "not mentioned"]
    found = [p for p in mentioned if p["score"] is not None]
    scored = [p for p in pairs if p["score"] is not None]
    false_mentions = [p for p in scored if p["label"] == "not mentioned"]
    confusion = {g: dict.fromkeys(ALL_CLASSES, 0) for g in ALL_CLASSES}
    for p in pairs:
        confusion[p["label"]][p["predicted"]] += 1
    return {
        "n_mentioned": len(mentioned),
        "n_found": len(found),
        "n_scored": len(scored),
        "n_false": len(false_mentions),
        "accuracy": sum(p["predicted"] == p["label"] for p in found) / len(found)
        if found
        else None,
        "spearman": spearman([p["score"] for p in found], [ORDER[p["label"]] for p in found]),
        "confusion": confusion,
    }


def majority(pairs: list[dict]) -> str:
    """Accuracy of the trivial rule "always the most frequent label" (on mentioned pairs)."""
    labels = [p["label"] for p in pairs if p["label"] != "not mentioned"]
    if not labels:
        return "n/a"
    top = max(CLASSES, key=labels.count)
    return f"accuracy {labels.count(top) / len(labels):.2f} (always `{top}`)"


def _number(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _ratio(part: int, whole: int) -> str:
    return f"{part}/{whole} ({part / whole:.0%})" if whole else "0/0"


def summary_table(pairs: list[dict]) -> list[str]:
    """Markdown table: one line per criterion plus the totals."""
    lines = [
        "| Criterion | Coverage (found / mentioned) | False mentions "
        "| Accuracy (3 classes) | Spearman |",
        "|---|---|---|---|---|",
    ]
    for criterion in [*(c.value for c in Criterion), "ALL"]:
        subset = pairs if criterion == "ALL" else [p for p in pairs if p["criterion"] == criterion]
        m = metrics(subset)
        name = f"**{criterion}**" if criterion == "ALL" else criterion
        lines.append(
            f"| {name} | {_ratio(m['n_found'], m['n_mentioned'])} "
            f"| {_ratio(m['n_false'], m['n_scored'])} "
            f"| {_number(m['accuracy'])} ({m['n_found']}) | {_number(m['spearman'])} |"
        )
    return lines


def confusion_table(pairs: list[dict]) -> list[str]:
    """Markdown confusion matrix, all criteria together."""
    confusion = metrics(pairs)["confusion"]
    lines = [
        "| label \\ pipeline | " + " | ".join(ALL_CLASSES) + " |",
        "|---" * (len(ALL_CLASSES) + 1) + "|",
    ]
    for gold in ALL_CLASSES:
        lines.append(
            f"| {gold} | " + " | ".join(str(confusion[gold][p]) for p in ALL_CLASSES) + " |"
        )
    return lines


def report_block(pairs: list[dict], tag: str, aspects: InterimAspects) -> str:
    """The generated block for one evaluation run."""
    lines = [
        f"Run `{tag}`: aspects.yaml version {aspects.aspects_config_version}, "
        f"direction method `{aspects.direction_method}`.",
        "",
    ]
    for half, title in (("all", "All 30 models"), ("dev", "DEV half"), ("test", "TEST half")):
        subset = pairs if half == "all" else [p for p in pairs if p["half"] == half]
        lines += [f"**{title}**", "", *summary_table(subset), ""]
        lines += [
            f"Reference: always answering the most frequent label gives {majority(subset)}.",
            "",
        ]
    lines += ["**Confusion matrix (all models, all criteria)**", "", *confusion_table(pairs)]
    return "\n".join(lines)


def write_block(path: Path, tag: str, block: str) -> None:
    """Replace (or append) the block between the markers of `tag` in the report."""
    start, end = f"<!-- metrics:{tag}:start -->", f"<!-- metrics:{tag}:end -->"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Phase 5 evaluation\n"
    new = f"{start}\n{block}\n{end}"
    pattern = re.compile(re.escape(start) + ".*?" + re.escape(end), re.DOTALL)
    text = (
        pattern.sub(lambda _: new, text) if pattern.search(text) else text.rstrip() + f"\n\n{new}\n"
    )
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Evaluate expert_aspects.json against the labels and update docs/evaluation.md."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default="current", help="name of this run in the report")
    parser.add_argument("--aspects", type=Path, default=ASPECTS_PATH)
    parser.add_argument("--no-write", action="store_true", help="print only")
    args = parser.parse_args(argv)

    pairs = load_pairs(GOLD_PATH, args.aspects)
    aspects = InterimAspects.model_validate_json(args.aspects.read_bytes())
    block = report_block(pairs, args.tag, aspects)
    print(block)
    if not args.no_write:
        write_block(REPORT_PATH, args.tag, block)
        print(f"\nupdated {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
