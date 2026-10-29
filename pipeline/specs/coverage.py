"""Write docs/data-coverage.md: how complete the manufacturer specs are."""

from collections import Counter
from pathlib import Path

from pipeline.models import InterimSpecs, RetailerTags

# Manufacturer fields that also exist in the retailer fallback.
SHARED_FIELDS = [
    "weight_g",
    "weight_women_g",
    "drop_mm",
    "lug_depth_mm",
    "midsole_foam",
    "outsole_rubber",
    "plate",
    "waterproof",
]
RETAILER_ONLY_FIELDS = ["sole_height_unlabelled_mm", "drop_range", "weight_range"]


def _retailer_section(records: list) -> list[str]:
    """Coverage of the retailer fallback, alone and combined with manufacturer data."""
    with_fallback = [r for r in records if r.retailer_fallback is not None]
    if not with_fallback:
        return []
    total = len(records)

    def pct(count: int) -> str:
        return f"{count} ({100 * count / total:.0f} %)"

    lines = [
        "",
        "## Retailer fallback (phase 3b, separate from manufacturer data)",
        "",
        "Values shown on Tradeinn/Glisshop product pages (`retailer_fallback`). Phase 6 uses",
        "manufacturer data first, then lab measurements, then these, with lower confidence.",
        "",
        "| Field | Manufacturer | Retailer fallback | Either source |",
        "|---|---|---|---|",
    ]
    for field in SHARED_FIELDS:
        maker = sum(getattr(r, field).value is not None for r in records)
        shop = sum(getattr(r.retailer_fallback, field).value is not None for r in with_fallback)
        either = sum(
            getattr(r, field).value is not None
            or (r.retailer_fallback and getattr(r.retailer_fallback, field).value is not None)
            for r in records
        )
        lines.append(f"| `{field}` | {pct(maker)} | {pct(shop)} | {pct(either)} |")
    lines += ["", "| Retailer-only field | Filled |", "|---|---|"]
    for field in RETAILER_ONLY_FIELDS:
        shop = sum(getattr(r.retailer_fallback, field).value is not None for r in with_fallback)
        lines.append(f"| `{field}` | {pct(shop)} |")
    for tag in RetailerTags.model_fields:
        shop = sum(getattr(r.retailer_fallback.tags, tag).value is not None for r in with_fallback)
        lines.append(f"| `tags.{tag}` (shop classification) | {pct(shop)} |")
    return lines


def write_coverage(specs: InterimSpecs, fields: list[str], path: Path) -> None:
    """Coverage per field, per brand, and the 20 models with the most missing fields."""
    records = list(specs.models.values())
    total = len(records) or 1
    with_page = [r for r in records if r.manufacturer_url]

    lines = [
        "# Data coverage",
        "",
        "Manufacturer specs (phase 3) first, then expert reviews (phase 4) and the final "
        "coverage of `data/processed/shoes.json` (phase 6) at the end.",
        "",
        "## Manufacturer specs (phase 3)",
        "",
        f"Generated {specs.generated_at:%Y-%m-%d} from `data/interim/specs.json` "
        "(`python -m pipeline.specs`).",
        "",
        f"- Models: **{len(records)}**",
        f"- Official product page found: **{len(with_page)}** "
        f"({100 * len(with_page) / total:.0f} %)",
        "- Percentages are over ALL models; the last column is over models with a page found.",
        "",
        "## Fields",
        "",
        "| Field | Filled | % of all models | % of models with a page |",
        "|---|---|---|---|",
    ]
    for field in fields:
        filled = sum(getattr(r, field).value is not None for r in records)
        filled_page = sum(getattr(r, field).value is not None for r in with_page)
        share_page = 100 * filled_page / len(with_page) if with_page else 0
        lines.append(
            f"| `{field}` | {filled} | {100 * filled / total:.0f} % | {share_page:.0f} % |"
        )

    lines += _retailer_section(records)
    lines += ["", "## Brands", "", "| Brand | Models | Page found | Why not |", "|---|---|---|---|"]
    brands = Counter(r.brand for r in records)
    for brand, count in brands.most_common():
        brand_records = [r for r in records if r.brand == brand]
        found = sum(r.manufacturer_url is not None for r in brand_records)
        reasons = Counter(
            r.manufacturer_url_missing_reason for r in brand_records if r.manufacturer_url is None
        )
        why = "; ".join(f"{reason} ({n})" for reason, n in reasons.most_common(2))
        lines.append(f"| {brand} | {count} | {found} | {why} |")

    def missing(record) -> int:
        return sum(getattr(record, field).value is None for field in fields)

    worst = sorted(records, key=lambda r: (-missing(r), r.model_id))[:20]
    lines += [
        "",
        "## The 20 models with the most missing fields",
        "",
        f"| Model id | Missing fields (of {len(fields)}) | Reason |",
        "|---|---|---|",
    ]
    for record in worst:
        reason = record.manufacturer_url_missing_reason or "fields not stated on the page"
        lines.append(f"| `{record.model_id}` | {missing(record)} | {reason} |")

    # Blocked brands all tie at "everything missing"; this table shows thin pages instead.
    thin = sorted(with_page, key=lambda r: (-missing(r), r.model_id))[:20]
    lines += [
        "",
        "## Among models whose page was found: the thinnest pages",
        "",
        f"| Model id | Missing fields (of {len(fields)}) | Page |",
        "|---|---|---|",
    ]
    for record in thin:
        lines.append(f"| `{record.model_id}` | {missing(record)} | {record.manufacturer_url} |")
    # Keep the blocks written by later phases: "reviews" (phase 4) and "build" (phase 6).
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    for name in ("reviews", "build"):
        start_mark, end_mark = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
        start, end = previous.find(start_mark), previous.find(end_mark)
        if start >= 0 and end > start:
            lines += ["", previous[start : end + len(end_mark)]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
