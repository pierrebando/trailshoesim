# pipeline/build/ (phase 6)

Merges the interim files into one record per model, computes the scores of
`docs/scoring-spec.md` (§2 criteria, §3 terrain, §8 confidence; §4 buyer rating comes from
phase 2), validates everything and writes `data/processed/`.

| File | Role |
|---|---|
| `evaluator.py` | Generic sub-score of spec §0.3-0.4: `interp`, lookups, coverage, re-normalisation. |
| `resolve.py` | One value per spec field: manufacturer > lab measurement > retailer, with reasons when missing. |
| `scores.py` | Criterion blend (§2.5) with provenance, terrain scores, confidence level and reasons. |
| `assemble.py` | Builds one `Shoe` from the catalogue, specs, reviews and aspects. |
| `__main__.py` | `python -m pipeline.build`: writes `shoes.json`, `scoring_config.json`, `meta.json`; validates against `schema/`. |
| `report.py` | `data/processed/build_report.md` and `docs/img/criteria_distribution.png`. |
| `export_schema.py` | Regenerates `schema/*.schema.json` from `pipeline/models.py`. |
