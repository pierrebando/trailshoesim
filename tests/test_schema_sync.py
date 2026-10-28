"""The committed JSON Schemas must match the pydantic models they are generated from."""

import pytest

from pipeline.build.export_schema import SCHEMA_DIR, SCHEMAS, render_schema


@pytest.mark.parametrize("filename", sorted(SCHEMAS))
def test_committed_schema_is_up_to_date(filename: str) -> None:
    committed = (SCHEMA_DIR / filename).read_text(encoding="utf-8")
    assert committed == render_schema(SCHEMAS[filename]), (
        f"schema/{filename} is stale: run `python -m pipeline.build.export_schema`"
    )
