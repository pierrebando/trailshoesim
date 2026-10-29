# schema/

JSON Schemas (draft 2020-12) of the data files the web app reads:

- `shoe.schema.json`: one final shoe record.
- `catalog.schema.json`: the whole `data/processed/shoes.json` file (metadata + list of shoes).
- `meta.schema.json`: `data/processed/meta.json` (build date, versions, counts).
- `retailer_listing.schema.json`: one record of `data/interim/retailer_listings.json` (phase 1).

These files are **generated** from `pipeline/models.py`; do not edit them by hand.
Regenerate with `python -m pipeline.build.export_schema`. A test fails if they are out of date.
