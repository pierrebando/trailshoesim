# data/processed/

Final data shipped with the web app (phase 6, `python -m pipeline.build`):

- `shoes.json`: all shoes, valid against `schema/catalog.schema.json` (each shoe against
  `schema/shoe.schema.json`). Every score has its `provenance`.
- `scoring_config.json`: a JSON copy of `pipeline/config/scoring.yaml` for the browser.
- `meta.json`: build date, versions, counts, price date range (`schema/meta.schema.json`).
- `build_report.md`: generated summary (completeness, confidence, flags, sanity table).
