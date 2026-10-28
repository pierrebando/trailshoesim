# pipeline/

The offline Python data pipeline. It runs on a developer machine (never in the browser)
and produces `data/processed/catalog.json`, the only file the web app reads.

| Folder | Phase | Role |
|---|---|---|
| `collect/` | 1 | List trail shoes currently on sale at Le Pape, iRun and Tradeinn (price, rating, review count, URL). |
| `normalize/` | 2 | Clean retailer records and decide which listings are the same shoe model. |
| `specs/` | 3 | Read technical specs from manufacturer product pages. |
| `reviews/` | 4 | Collect expert review conclusions as short excerpts + links. |
| `nlp/` | 5 | Offline AI step (Hugging Face models): review sentence -> criterion + polarity. |
| `build/` | 6 | Compute criterion, terrain and confidence scores; export the catalogue and JSON Schemas. |
| `utils/` | – | Shared helpers (config loading; later HTTP politeness and caching). |
| `config/` | – | `scoring.yaml`: every numeric constant of the scoring system. |

`models.py` holds the pydantic models of the final shoe record. They are the single source
of truth: `schema/*.schema.json` is generated from them (see `build/export_schema.py`).
