# pipeline/specs/ (phase 3)

Manufacturer specs for every model of `data/interim/catalog.json`.

| Module | Role |
|---|---|
| `locate.py` | Reads the brand's sitemap and matches a model to a product URL (name + version in the slug). |
| `pagetext.py` | Page -> plain text from the product title onwards, cells separated by " | ". |
| `extract.py` | Label-based extraction ("Poids", "Drop", "Outsole"...); every value keeps a verbatim snippet, and `verify` rejects values not found in the page text. |
| `retailer.py` | Phase 3b: SEPARATE fallback from retailer product pages (exact values only, agreement rules, snippets re-checked in the cached pages). |
| `coverage.py` | Writes `docs/data-coverage.md` (manufacturer, retailer fallback, combined). |
| `__main__.py` | The phase 3 pipeline. |

Which sites may be read, and why the others are not: `pipeline/config/manufacturers.yaml`
and `docs/sources.md`. Pages are cached in `data/raw/specs/<brand>/`.

```bash
python -m pipeline.specs                     # all brands
python -m pipeline.specs --brand Saucony     # one brand (others kept from specs.json)
python -m pipeline.specs --refresh           # ignore the cache
python -m pipeline.specs --retailer-only     # rebuild only the retailer fallback (offline)
```

No LLM is used: the extraction rules are deterministic, so the same page always gives the
same values and each value can be traced to its snippet.
