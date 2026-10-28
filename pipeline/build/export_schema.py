"""Generate the JSON Schemas in `schema/` from the pydantic models.

The schemas are generated rather than hand-written so they can never drift from the
code: `tests/test_schema_sync.py` fails if a model changes without regenerating.

Run from the repository root:

    python -m pipeline.build.export_schema
"""

import json
from pathlib import Path

from pydantic import BaseModel

from pipeline.models import BuildMeta, Catalog, RetailerListing, Shoe

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"
SCHEMAS: dict[str, type[BaseModel]] = {
    "shoe.schema.json": Shoe,
    "catalog.schema.json": Catalog,
    "retailer_listing.schema.json": RetailerListing,
    "meta.schema.json": BuildMeta,
}


def render_schema(model: type[BaseModel]) -> str:
    """Return the JSON Schema of `model` as pretty-printed JSON text."""
    # "serialization" mode describes the JSON we write, which is what the web app reads.
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **model.model_json_schema(mode="serialization"),
    }
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    """Write every schema file listed in SCHEMAS."""
    for filename, model in SCHEMAS.items():
        (SCHEMA_DIR / filename).write_text(render_schema(model), encoding="utf-8")
        print(f"wrote schema/{filename}")


if __name__ == "__main__":
    main()
