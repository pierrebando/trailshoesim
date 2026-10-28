# pipeline/normalize/ (phase 2)

Turns `data/interim/retailer_listings.json` into one record per canonical model in
`data/interim/catalog.json`.

| Module | Role |
|---|---|
| `brands.py` | Brand alias table (`pipeline/config/brands.yaml`). |
| `titles.py` | Title parser: brand, model, version, gender, variants (`pipeline/config/titles.yaml`). |
| `matching.py` | Exact key match, then conservative fuzzy proposals (rapidfuzz). |
| `versions.py` | Version ordering ("9" < "9+" < "10"). |
| `ratings.py` | Bayesian buyer rating (docs/scoring-spec.md §4). |
| `apply_review.py` | Reads and writes `needs_review.csv` (keep / split / rename decisions). |
| `__main__.py` | The phase 2 pipeline. |

Key format: `brand|model|version`, e.g. `hoka|speedgoat|6`. Gender is not part of the
key (it goes to `gender_variants`); waterproof, wide, mid... are `variants` of the same
model.

```bash
python -m pipeline.normalize                 # build catalog.json + needs_review.csv
python -m pipeline.normalize.apply_review    # same, after you filled in decisions
```
