"""Manual spec entries (data/manual/missing_specs.csv): validation and tier order."""

import csv
from pathlib import Path

import pytest

from pipeline.build.resolve import resolve_specs
from pipeline.models import MatchConfidence, SourcedFloat
from pipeline.specs.manual import COLUMNS, ManualEntryError, load_manual_specs, parse_value
from tests.test_build import _lab_review, _model_specs, known

PAGE = "https://example.org/fictional-shoe"
MODELS = {"fictional-shoe"}


def write(path: Path, rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows({c: r.get(c, "") for c in COLUMNS} for r in rows)
    return path


def row(field: str, value: str, snippet: str, **extra: str) -> dict:
    return {
        "model_id": "fictional-shoe", "field": field, "value": value, "source_url": PAGE,
        "retrieved_at": "2026-10-29", "raw_snippet": snippet, "entered_by": "student", **extra,
    }  # fmt: skip


def test_filled_rows_become_sourced_values_and_empty_rows_are_ignored(tmp_path: Path) -> None:
    path = write(tmp_path / "m.csv", [
        row("stack_heel_mm", "33", "Stack height: 33 mm heel / 27 mm forefoot"),
        row("plate", "rock_plate", "Rock plate in the forefoot"),
        row("width_options", "standard;wide", "Available in standard and wide"),
        {"model_id": "fictional-shoe", "field": "drop_mm"},  # not filled yet
    ])  # fmt: skip
    entries = load_manual_specs(MODELS, path)["fictional-shoe"]
    assert set(entries) == {"stack_heel_mm", "plate", "width_options"}
    assert entries["stack_heel_mm"].value == 33.0
    assert entries["stack_heel_mm"].source_name == "manual (student entry)"
    assert entries["width_options"].value == ["standard", "wide"]


def test_invalid_rows_are_all_reported(tmp_path: Path) -> None:
    path = write(tmp_path / "m.csv", [
        row("stack_heel_mm", "35", "Stack height: 33 mm"),  # value not in the quote
        row("lug_depth_mm", "5", "Lugs of 5 mm", source_url=""),  # no source
        row("colour", "red", "Red"),  # not a spec field
        row("waterproof", "maybe", "Water resistant"),  # not yes/no
        row("drop_mm", "6", " ".join(["word"] * 31) + " 6"),  # quote too long
    ])  # fmt: skip
    with pytest.raises(ManualEntryError) as error:
        load_manual_specs(MODELS, path)
    message = str(error.value)
    assert "5 invalid row(s)" in message
    assert "does not appear in raw_snippet" in message and "source_url" in message


def test_values_are_parsed_by_field() -> None:
    assert parse_value("weight_g", "281,5") == 281.5
    assert parse_value("waterproof", "Yes") is True
    with pytest.raises(ValueError):
        parse_value("plate", "titanium")


def test_manual_comes_after_manufacturer_and_before_lab() -> None:
    manual = {"lug_depth_mm": known(SourcedFloat, 5.0, "manual (student entry)")}
    lab = [_lab_review(4.5, MatchConfidence.EXACT)]
    specs = _model_specs(
        manufacturer={}, retailer={"lug_depth_mm": known(SourcedFloat, 4.0, "shop")}
    )
    resolved = resolve_specs(specs, lab, manual)
    assert (resolved.lug_depth_mm.value, resolved.sources["lug_depth_mm"]) == (5.0, "manual")
    with_brand = _model_specs(
        manufacturer={"lug_depth_mm": known(SourcedFloat, 6.0, "brand")}, retailer={}
    )
    assert resolve_specs(with_brand, lab, manual).lug_depth_mm.value == 6.0
