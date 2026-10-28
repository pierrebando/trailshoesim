"""Phase 6: build the final database read by the web app.

    python -m pipeline.build [--build-date YYYY-MM-DD] [--no-report]

Reads  data/interim/catalog.json, specs.json, expert_reviews.json, expert_aspects.json
       and pipeline/config/scoring.yaml.
Writes data/processed/shoes.json          (all shoes, valid against schema/catalog.schema.json)
       data/processed/scoring_config.json (scoring.yaml as JSON, for the browser)
       data/processed/meta.json           (build date, versions, counts, price dates)
       data/processed/build_report.md + docs/img/*.png (unless --no-report)

The output is validated twice: by the pydantic models while it is built, then the
written JSON against the JSON Schemas in schema/. Any violation stops the build.
"""

import argparse
import datetime as dt
import json
import logging
import sys
import tomllib
from pathlib import Path

import jsonschema

from pipeline.build.assemble import build_shoe
from pipeline.models import (
    BuildMeta,
    Catalog,
    ConfidenceLevel,
    InterimAspects,
    InterimCatalog,
    InterimReviews,
    InterimSpecs,
)
from pipeline.nlp.aspects import load_config as load_aspects_config
from pipeline.utils.config import load_scoring_config

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
SCHEMA_DIR = ROOT / "schema"
SCHEMA_VERSION = "1.0.0"
log = logging.getLogger("pipeline.build")


class BuildError(RuntimeError):
    """The build produced data that breaks the schema: nothing is written."""


def rounded(data: object, decimals: int) -> object:
    """Round every float of a JSON-like structure (spec §0.3: round only when written)."""
    if isinstance(data, float):
        return round(data, decimals)
    if isinstance(data, list):
        return [rounded(item, decimals) for item in data]
    if isinstance(data, dict):
        return {key: rounded(value, decimals) for key, value in data.items()}
    return data


def validate(data: object, schema_file: str) -> None:
    """Check `data` against a schema of schema/; raise BuildError listing every violation."""
    schema = json.loads((SCHEMA_DIR / schema_file).read_text(encoding="utf-8"))
    errors = sorted(
        jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path)
    )
    if errors:
        lines = [f"  {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors[:20]]
        raise BuildError(f"{len(errors)} violation(s) of {schema_file}:\n" + "\n".join(lines))


def build(build_date: dt.date) -> tuple[dict, dict, dict[str, str]]:
    """Build every shoe; return (catalogue JSON, meta JSON, dropped model -> reason)."""
    config = load_scoring_config()
    catalog = InterimCatalog.model_validate_json((INTERIM / "catalog.json").read_bytes())
    specs = InterimSpecs.model_validate_json((INTERIM / "specs.json").read_bytes()).models
    reviews = InterimReviews.model_validate_json((INTERIM / "expert_reviews.json").read_bytes())
    aspects = InterimAspects.model_validate_json((INTERIM / "expert_aspects.json").read_bytes())

    shoes, dropped = [], {}
    for model in catalog.models:
        if not model.gender_variants:
            # Shoe.gender_variants needs at least one value and we never guess one.
            dropped[model.id] = "no gender shown by any retailer listing"
            continue
        shoes.append(
            build_shoe(
                model,
                specs[model.id],
                reviews.models.get(model.id, []),
                aspects,
                build_date,
                config,
            )
        )
    generated_at = dt.datetime.now(dt.UTC).replace(microsecond=0)
    result = Catalog(
        schema_version=SCHEMA_VERSION,
        generated_at=generated_at,
        scoring_config_version=config["version"],
        shoes=shoes,
    )
    data = rounded(result.model_dump(mode="json"), config["common"]["output_decimals"])
    validate(data, "catalog.schema.json")
    for shoe in data["shoes"]:
        validate(shoe, "shoe.schema.json")

    price_dates = [o.price_date for s in shoes for o in s.retail]
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    meta = BuildMeta(
        build_date=build_date,
        generated_at=generated_at,
        pipeline_version=pyproject["project"]["version"],
        scoring_config_version=config["version"],
        aspects_config_version=load_aspects_config().version,
        shoe_count=len(shoes),
        brand_count=len({s.brand for s in shoes}),
        offer_count=sum(len(s.retail) for s in shoes),
        expert_review_count=sum(len(s.expert_reviews) for s in shoes),
        models_dropped=dropped,
        confidence_counts={
            level: sum(s.confidence.level == level for s in shoes) for level in ConfidenceLevel
        },
        price_date_min=min(price_dates),
        price_date_max=max(price_dates),
        retailers=sorted({o.retailer for s in shoes for o in s.retail}),
        review_sources=sorted({r.source for s in shoes for r in s.expert_reviews}),
    )
    meta_data = meta.model_dump(mode="json")
    validate(meta_data, "meta.schema.json")
    return data, meta_data, dropped


def write_json(path: Path, data: object) -> None:
    """Write JSON with a stable layout (readable diffs in git)."""
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Build, validate and write data/processed/."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Build data/processed/shoes.json.")
    parser.add_argument(
        "--build-date",
        type=dt.date.fromisoformat,
        default=dt.date.today(),
        help="date used for price ages (default: today)",
    )
    parser.add_argument("--no-report", action="store_true", help="skip build_report.md and plots")
    args = parser.parse_args(argv)
    try:
        data, meta, dropped = build(args.build_date)
    except BuildError as error:
        log.error("build stopped, nothing written:\n%s", error)
        return 1
    PROCESSED.mkdir(parents=True, exist_ok=True)
    write_json(PROCESSED / "shoes.json", data)
    write_json(PROCESSED / "scoring_config.json", load_scoring_config())
    write_json(PROCESSED / "meta.json", meta)
    log.info("%d shoes written, %d models dropped: %s", len(data["shoes"]), len(dropped), dropped)
    if not args.no_report:
        from pipeline.build.report import write_report  # matplotlib only when needed

        write_report(data, meta)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
