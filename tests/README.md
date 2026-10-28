# tests/

pytest test suite. Run `pytest` from the repository root.

- `test_models.py`: the pydantic models accept a valid record and reject rule violations
  (missing value without reason, value without provenance, excerpt too long).
- `test_schema_sync.py`: the committed JSON Schemas match the pydantic models.
- `test_scoring_config.py`: `scoring.yaml` is internally consistent (weights sum to 1, anchors sorted...).
- `test_http.py`: robots.txt wildcards, cache, bot-challenge stop, User-Agent (no network).
- `test_tradeinn.py`, `test_glisshop.py`: retailer parsers.
- `test_titles.py`: title parsing on 39 real-looking French/English titles.
- `test_reviews.py`: review parsers (3 sources), strict matching, excerpts, decisions.
- `test_specs.py`: spec extraction on 4 layouts, verification, sitemap matching.
- `test_retailer_fallback.py`: phase 3b rules (exact vs buckets, versions, genders, disagreements, re-verification).
- `test_normalize.py`: matching, review decisions, versions, Bayesian ratings, end-to-end build.
- `test_build.py`: phase 6 scoring (spec worked example, re-normalisation, null when
  nothing is known, monotonicity, terrain, women's weight fallback), source priority,
  confidence levels, and an end-to-end build of the committed interim data against the schemas.
- `test_nlp.py`: sentence splitting, matching rules with fake embedding and NLI models,
  aggregation, evaluation metrics, and the real models on `fixtures/nlp/sentences.yaml`
  (48 hand-written EN/FR sentences; skipped when the models are not downloaded).
- `fixtures/fictional_shoe.json`: a clearly fictional shoe used as test data (not real data).
- `fixtures/tradeinn/*.html`, `fixtures/glisshop/*.html`, `fixtures/specs/*.html`, `fixtures/reviews/*.html`: **hand-written** HTML imitating each site's markup with
  fictional products. Not copies of real pages (we never commit third-party HTML).
