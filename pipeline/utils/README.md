# pipeline/utils/

Small helpers shared by several phases.

- `config.py`: loads `pipeline/config/scoring.yaml`.
- `http.py`: `PoliteClient`, the only way collectors may fetch pages (robots.txt check,
  1 request every 1.1 s per site, project User-Agent, gzip cache in `data/raw/<site>/`,
  stop on bot challenges).
- `robots.py`: robots.txt parser that understands `*` and `$` wildcards.
