# pipeline/collect/ (phase 1)

Collects the list of trail running shoes on sale at the retailers, with price, buyer
rating, review count, brand, title, gender, breadcrumb, image URL and product URL.

| Site | Status | Module |
|---|---|---|
| Tradeinn (Runnerinn store) | collected | `tradeinn.py` |
| Glisshop | collected | `glisshop.py` |
| Le Pape | **stopped**: Cloudflare bot challenge | none |
| i-Run | **stopped**: terms forbid extraction | none |

Why and how: `docs/sources.md`.

```bash
python -m pipeline.collect --site all             # every allowed site
python -m pipeline.collect --site tradeinn --limit 20   # quick test
python -m pipeline.collect --site tradeinn --refresh    # ignore the cache
```

- All HTTP goes through `pipeline/utils/http.py` (robots.txt check, 1 request every
  1.1 s, project User-Agent, gzip cache in `data/raw/<site>/`). Re-running reads the
  cache, so it is fast and sends no request for pages already downloaded.
- Output: `data/interim/retailer_listings.json` (list of `RetailerListing`, see
  `pipeline/models.py`) and `data/interim/collect_report.json` (counts and failures).
- Parsers are pure functions of the HTML, tested offline in `tests/test_tradeinn.py` and
  `tests/test_glisshop.py`. `common.py` holds what collectors share.
