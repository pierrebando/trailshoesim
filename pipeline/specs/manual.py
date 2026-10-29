"""Specs entered by hand by the student, from product pages read in a normal browser.

    python -m pipeline.specs.manual --template   # (re)write data/manual/missing_specs.csv

Some brands block automated access, so their specs can only be completed by a person.
The CSV data/manual/missing_specs.csv has one row per (model, field) to fill. A row counts
only when `value`, `source_url`, `retrieved_at` and `raw_snippet` are filled; the snippet
is the exact sentence of the page that gives the value (at most 30 words), like phase 3.
Filled rows become a spec tier labelled "manual (student entry)" (see build/resolve.py).
"""

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

from pipeline.models import MAX_EXCERPT_WORDS, Plate, SourcedValue, Width

ROOT = Path(__file__).resolve().parents[2]
MANUAL_PATH = ROOT / "data" / "manual" / "missing_specs.csv"
SOURCE_NAME = "manual (student entry)"
COLUMNS = [
    "model_id", "model", "field", "value", "source_url", "retrieved_at", "raw_snippet",
    "entered_by", "notes",
]  # fmt: skip
NUMBER_FIELDS = {
    "weight_g",
    "weight_women_g",
    "stack_heel_mm",
    "stack_forefoot_mm",
    "drop_mm",
    "lug_depth_mm",
}
TEXT_FIELDS = {"midsole_foam", "outsole_rubber"}
FIELDS = NUMBER_FIELDS | TEXT_FIELDS | {"plate", "waterproof", "width_options"}
# The fields that drive most scores (cushioning, protection, grip, stability, lightness).
TEMPLATE_FIELDS = [
    "stack_heel_mm",
    "stack_forefoot_mm",
    "drop_mm",
    "lug_depth_mm",
    "weight_g",
    "midsole_foam",
    "outsole_rubber",
]
TEMPLATE_MODELS = 40


class ManualEntryError(ValueError):
    """A filled row of the CSV is invalid; the message lists every problem."""


def parse_value(field: str, raw: str) -> object:
    """The typed value of one cell ("281", "yes", "standard;wide", "rock_plate"...)."""
    raw = raw.strip()
    if field in NUMBER_FIELDS:
        return float(raw.replace(",", "."))
    if field == "waterproof":
        if raw.lower() not in {"yes", "no"}:
            raise ValueError("waterproof must be yes or no")
        return raw.lower() == "yes"
    if field == "plate":
        return Plate(raw).value  # none, rock_plate, carbon, other
    if field == "width_options":
        return [Width(w.strip()).value for w in raw.split(";") if w.strip()]
    return raw


def _row_problems(row: dict, known_models: set[str]) -> list[str]:
    problems = []
    if row["model_id"] not in known_models:
        problems.append(f"unknown model_id {row['model_id']!r}")
    if row["field"] not in FIELDS:
        problems.append(f"unknown field {row['field']!r}")
    if not re.match(r"^https?://", row["source_url"] or ""):
        problems.append("source_url must be the page the value was read on")
    try:
        dt.date.fromisoformat(row["retrieved_at"] or "")
    except ValueError:
        problems.append("retrieved_at must be a date YYYY-MM-DD")
    snippet = (row["raw_snippet"] or "").strip()
    if not snippet:
        problems.append("raw_snippet must quote the page (the sentence that gives the value)")
    elif len(snippet.split()) > MAX_EXCERPT_WORDS:
        problems.append(f"raw_snippet has more than {MAX_EXCERPT_WORDS} words")
    if row["field"] in NUMBER_FIELDS and snippet:
        try:
            number = f"{float(row['value'].strip().replace(',', '.')):g}"  # "10.0" -> "10"
        except ValueError:
            number = None  # reported by parse_value
        if number and number not in snippet.replace(",", "."):
            problems.append(f"the value {row['value']} does not appear in raw_snippet")
    return problems


def load_manual_specs(
    known_models: set[str], path: Path = MANUAL_PATH
) -> dict[str, dict[str, SourcedValue]]:
    """Filled rows as {model_id: {field: SourcedValue}}; raises if a filled row is invalid."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as file:
        rows = [row for row in csv.DictReader(file) if (row.get("value") or "").strip()]
    entries: dict[str, dict[str, SourcedValue]] = {}
    errors = []
    for number, row in enumerate(rows, start=2):
        problems = _row_problems(row, known_models)
        if not problems:
            try:
                value = parse_value(row["field"], row["value"])
            except ValueError as error:
                problems.append(str(error))
        if problems:
            errors.append(
                f"row {number} ({row['model_id']}, {row['field']}): {'; '.join(problems)}"
            )
            continue
        who = (row.get("entered_by") or "").strip()
        entries.setdefault(row["model_id"], {})[row["field"]] = SourcedValue[object](
            value=value,
            source_name=SOURCE_NAME,
            source_url=row["source_url"].strip(),
            retrieved_at=dt.date.fromisoformat(row["retrieved_at"]),
            raw_snippet=row["raw_snippet"].strip(),
            note=f"entered by {who}" if who else "entered by hand",
        )
    if errors:
        raise ManualEntryError(f"{len(errors)} invalid row(s) in {path}:\n" + "\n".join(errors))
    return entries


def write_template(shoes: list[dict], path: Path = MANUAL_PATH) -> int:
    """Rows to fill for the models where a person can help most; keeps rows already filled."""
    filled = []
    if path.exists():
        with path.open(encoding="utf-8") as file:
            filled = [r for r in csv.DictReader(file) if (r.get("value") or "").strip()]
    done = {(r["model_id"], r["field"]) for r in filled}

    def missing(shoe: dict) -> list[str]:
        return [f for f in TEMPLATE_FIELDS if shoe["specs"][f]["value"] is None]

    # Models people are most likely to look at: reviewed and rated ones first.
    ranked = sorted(
        (s for s in shoes if len(missing(s)) >= 3),
        key=lambda s: (-len(s["expert_reviews"]), -s["confidence"]["buyer_review_count"], s["id"]),
    )[:TEMPLATE_MODELS]
    rows = list(filled)
    for shoe in ranked:
        name = " ".join(x for x in (shoe["brand"], shoe["model"], shoe["version"]) if x)
        for field in missing(shoe):
            if (shoe["id"], field) not in done:
                rows.append({"model_id": shoe["id"], "model": name, "field": field})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows({c: r.get(c, "") for c in COLUMNS} for r in rows)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    """Write the template, or check the filled rows."""
    parser = argparse.ArgumentParser(description="Manual spec entries (student).")
    parser.add_argument("--template", action="store_true", help="write the CSV of rows to fill")
    args = parser.parse_args(argv)
    shoes = json.loads((ROOT / "data" / "processed" / "shoes.json").read_text(encoding="utf-8"))[
        "shoes"
    ]
    if args.template:
        print(f"wrote {write_template(shoes)} rows to {MANUAL_PATH}")
        return 0
    try:
        entries = load_manual_specs({s["id"] for s in shoes})
    except ManualEntryError as error:
        print(error)
        return 1
    print(f"{sum(len(v) for v in entries.values())} valid entries for {len(entries)} models")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
