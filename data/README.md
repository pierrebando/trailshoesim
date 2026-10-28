# data/

| Folder | Committed? | Content |
|---|---|---|
| `raw/` | No (gitignored) | Cache of every HTTP response, exactly as downloaded. Lets us re-run without re-scraping. |
| `interim/` | Yes | Cleaned per-source records (JSON). No raw HTML, no full article text. |
| `processed/` | Yes | Final output read by the web app: `catalog.json` (+ the scoring config as JSON). |
