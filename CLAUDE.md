# CLAUDE.md — Trail Shoe Finder

Guidance for anyone (human or AI assistant) working in this repository.
This is a school project: a teacher will read the code, so clarity beats cleverness.

## Project summary

"Trail Shoe Finder" is a static web app (hosted on GitHub Pages, no backend) that
recommends trail running shoes from a runner profile.

- **Profile**: weight, typical distance, terrain types, foot strike (heel / midfoot /
  forefoot / unknown), preference sliders (cushioning vs ground feel, stability vs agility,
  dynamic vs comfortable), foot width, gender.
- **Hard filters (blockers)**: max price, excluded brands, waterproof yes/no/any,
  min/max drop, width, gender.
- **Ranking**: a weighted score that is always **explained** (top reasons, drawbacks,
  per-criterion breakdown). Also: a model page, a comparator, an "I like this model" mode
  (find similar shoes) and confidence indicators.
- **Data** is built **offline** by a Python pipeline and shipped as a JSON file.
- Language: UI in English, pipeline documentation in English.

## Repository structure

```
CLAUDE.md               this file
README.md               short project presentation and quickstart
pyproject.toml          Python project, dependencies, ruff + pytest config
pipeline/               offline Python pipeline (package)
  models.py             pydantic models of the final shoe record (source of truth)
  config/scoring.yaml   every numeric constant of the scoring system
  collect/              phase 1: retailer listings
  normalize/            phase 2: cleaning + matching models across retailers
  specs/                phase 3: manufacturer specs (sitemap locate + quoted extraction)
  reviews/              phase 4: expert review excerpts + links
  nlp/                  phase 5: offline Hugging Face step (sentence -> criterion, polarity)
  build/                phase 6: scoring, confidence, export (+ schema export)
  utils/                shared helpers
data/
  raw/                  HTTP cache, gitignored (only its README is tracked)
  interim/              committed intermediate JSON per source/phase
  processed/            committed final JSON read by the web app
schema/                 JSON Schemas, generated from pipeline/models.py
docs/                   scoring-spec.md and phase reports
web/                    static web app (phase 7)
tests/                  pytest suite
```

## Decisions

1. Static site on GitHub Pages; no backend, no database, no runtime API calls.
2. All data is produced offline by the Python pipeline and committed as JSON in `data/processed/`
   (`shoes.json`, `scoring_config.json`, `meta.json`; see `data/processed/README.md`).
3. Data sources:
   1. Three French retailers — **Le Pape, iRun, Tradeinn** — define which shoes exist in the
      catalogue (currently on sale) and provide price, buyer rating, review count, URL.
      **Phase 1 outcome:** Le Pape blocks bots (Cloudflare challenge) and i-Run's terms
      forbid extraction; both are skipped until the project owner obtains permission.
      **Glisshop** replaces them (the only one of ten other French retailers that is
      open and whose terms allow it). Collected: **Tradeinn + Glisshop**. Details in
      `docs/sources.md`.
   2. **Manufacturer product pages** provide technical specs.
   3. **Specialist review sources**: RunRepeat, Believe in the Run and Esprit Trail
      (French). Doctors of Running was dropped: its robots.txt bans AI crawlers. Only
      short excerpts (<= 30 words, our selection) + links are committed; full conclusions
      stay in `data/raw/reviews/conclusions.json` (gitignored) for phase 5.
   4. A small **offline AI step** (Hugging Face models) maps review sentences to criteria and polarity.
4. UI in English; documentation in English.
5. The pydantic models in `pipeline/models.py` are the single source of truth for the data
   format; `schema/*.schema.json` is generated from them and checked by a test.
6. Every scoring constant lives in `pipeline/config/scoring.yaml`; `docs/scoring-spec.md`
   explains them. The build exports the YAML to JSON so the browser uses the same numbers.
7. Shoe-only scores (criteria, terrain, buyer rating, confidence) are computed offline.
   Everything that depends on the runner profile (filters, weights, final score,
   explanation, similarity) is computed in the browser.
8. Scoring rules are **heuristics** chosen by the project, not scientific laws.
9. Prices are in EUR; buyer ratings are normalised to a 0-5 scale.
10. Missing data is never guessed: scores are re-normalised over available inputs and the
    confidence level is lowered.
11. Python 3.11, pydantic v2, ruff, pytest.
12. A model is identified by the key `brand|model|version` (e.g. `hoka|speedgoat|6`).
    Gender is NOT in the key (`gender_variants`); waterproof / wide / mid / BOA / refurbished
    are `variants` of the same model. Vocabulary lives in `pipeline/config/brands.yaml` and
    `pipeline/config/titles.yaml`.
13. When a retailer gives a model name without colour (Glisshop), phase 2 builds the key
    from it rather than from the marketing title (`RetailerListing.model_name`).
14. Manufacturer specs (phase 3) quote the page: every known value has a `raw_snippet`
    (max 30 words, verbatim) and is rejected if the snippet or value is not in the page
    text. Conversions are labelled with `derivation`. Lab measurements from review sites
    go to the separate `lab_fallback` slot (phase 4/6), never into the manufacturer fields.
    Specs shown by the retailers (Tradeinn/Glisshop) go to the separate `retailer_fallback`
    slot (phase 3b): exact numbers only (filter buckets such as "5-8 mm" stay text ranges),
    weight from men's standard-version listings, null when listings disagree, every
    snippet re-checked in the cached page. Source priority for phase 6: manufacturer >
    lab measurements > retailer (with lower confidence). Shop classifications (fit width,
    terrain, runner build...) are `retailer_fallback.tags`, hints only.
    A robots.txt that bans AI crawlers (ClaudeBot...) or scripted clients is respected.
15. Reviews are matched STRICTLY: model words then exact version in the URL slug, confirmed
    by the page title ("Speedgoat 5" never attaches to "Speedgoat 6"). Comparisons and
    unconfirmed titles go to `data/interim/reviews_needs_review.csv` (decision accept/reject).
    Lab values published by a source (RunRepeat) are stored as that source's measurements.
16. Fuzzy matching is conservative (same brand and version, `fuzz.ratio` >= 92); anything
    uncertain goes to `data/interim/needs_review.csv` for a human decision.
17. Phase 5 uses two pinned multilingual Hugging Face models, offline on CPU. A
    sentence-embedding model (`paraphrase-multilingual-mpnet-base-v2`) decides WHICH
    criterion a sentence mentions (similarity to short EN/FR descriptors, minus
    "background" topics); a zero-shot NLI model (`mDeBERTa-v3-base-xnli-multilingual`)
    decides the DIRECTION (entailment of "The shoe is light." vs "The shoe is heavy.").
    The embedding-only direction (aspects.yaml 0.2.0) was dropped after the evaluation.
    Every threshold is in `pipeline/config/aspects.yaml`, explained in
    `docs/methodology-nlp.md`, and measured on a labelled sample
    (`data/interim/gold_labels.csv`, `docs/evaluation.md`; labels made by the AI
    assistant at the owner's request, 5 rows checked by the owner, column `labelled_by`).
18. Phase 6 implements `docs/scoring-spec.md` §2-4 and §8 literally, constants from
    `scoring.yaml`. Each spec field comes from manufacturer > lab measurement (RunRepeat:
    stacks, lug depth, platform widths) > retailer; `Specs.sources` says which. Scoring
    0.2.x (owner's decisions after the phase 6 review): min spec coverage 0.45,
    protection requires the forefoot stack, expert-only scores shrink towards a neutral 5
    with few reviews, evidenced foam rules only. Every criterion and
    terrain score has a `provenance` list (input, source kind, value, weight; weights sum
    to 1). Buyer ratings are never a criterion input (spec §2.6). The expert sub-score is
    the plain mean over reviews (spec §2.4), not the source-weighted mean of phase 5.
    Output is validated against `schema/*.schema.json`; any violation stops the build.
    Models without a gender are dropped (listed in `meta.json`), never given a default. Not mentioned = null.

## Rules

- **Never invent data.** If a value is not found, store `null` and a reason
  (`missing_reason`). Every non-trivial value keeps its provenance: source name, URL,
  retrieval date.
- **Polite scraping.**
  - Check `robots.txt` and the site's terms before collecting; record the result in `docs/sources.md`.
  - Max 1 request per second per site.
  - Send an explicit User-Agent identifying the project and a contact. The contact comes
    from the `TSF_CONTACT` environment variable, so no personal address is in the code.
  - Cache every response in `data/raw/`; never download the same page twice.
  - If a site forbids automated access, **STOP and report** instead of working around it.
    A bot challenge (e.g. Cloudflare "Just a moment...") counts as forbidding it.
  - All of this is enforced in `pipeline/utils/http.py` (`PoliteClient`); collectors must
    never call `requests` directly.
- **Never commit full third-party article text or raw HTML.** Only short excerpts
  (max ~30 words) with a link. Parser test fixtures are hand-written HTML that imitates
  a site's structure with fictional products, never saved copies of real pages.
- **Code style.** Python 3.11, type hints, docstrings, small modules, pydantic models for
  data, pytest tests. Comments explain WHY, not WHAT. Prefer clarity over cleverness,
  because a teacher will read it.
- **Each phase ends with a short report**: what was produced, counts, known problems, what
  the project owner should verify. Reports go in `docs/reports/phase-N.md`.
- **No secrets in the repo** (no API keys, tokens, cookies, `.env` files).

## Commands

Setup (once). Requires Python 3.11+ (macOS: installer from python.org).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export TSF_CONTACT="your-email@example.org"   # contact sent in the User-Agent (phase 1+)
```

Because this folder lives in iCloud Drive, you may prefer `python3.11 -m venv .venv.nosync`
followed by `ln -s .venv.nosync .venv` so iCloud does not sync the virtual environment.

| Phase | What | Command |
|---|---|---|
| 0 | Lint | `ruff check .` |
| 0 | Format | `ruff format .` |
| 0 | Tests | `pytest` |
| 0 | Regenerate JSON Schemas | `python -m pipeline.build.export_schema` |
| 1 | Collect retailer listings (all allowed sites) | `python -m pipeline.collect --site all` |
| 1 | One site / quick test | `python -m pipeline.collect --site tradeinn --limit 20` |
| 1 | Ignore the cache and re-download | `python -m pipeline.collect --site tradeinn --refresh` |
| 2 | Normalise + match models | `python -m pipeline.normalize` |
| 2 | Re-run after filling `needs_review.csv` | `python -m pipeline.normalize.apply_review` |
| 3 | Manufacturer specs (all brands) | `python -m pipeline.specs` |
| 3 | One brand / ignore the cache | `python -m pipeline.specs --brand Saucony --refresh` |
| 3b | Rebuild only the retailer fallback (no network) | `python -m pipeline.specs --retailer-only` |
| 4 | Expert reviews (all sources) | `python -m pipeline.reviews --source all` |
| 4 | One source / ignore the cache | `python -m pipeline.reviews --source runrepeat --refresh` |
| 5 | Install the NLP extra (once, ~1 GB with PyTorch) | `pip install -e ".[nlp]"` |
| 5 | NLP aspects (downloads 2 models once, ~0.9 GB, then offline) | `python -m pipeline.nlp` |
| 5 | Make the blind labelling sheet (never overwrites) | `python -m pipeline.nlp.make_labeling_sheet` |
| 5 | Evaluate against the labels, update `docs/evaluation.md` | `python -m pipeline.nlp.evaluate --tag current` |
| 6 | Build shoes.json, meta.json, build report | `python -m pipeline.build` |
| all | Rebuild everything from the cache (phases 1-6) | see below |
| 7 | Web app (local preview) | _to be added_ |

Rebuild everything, from the HTTP cache in `data/raw/` (only pages that are not cached
are downloaded, politely) and the decisions in the `*needs_review.csv` files:

```bash
python -m pipeline.collect --site all && python -m pipeline.normalize && python -m pipeline.specs && python -m pipeline.reviews --source all && python -m pipeline.nlp && python -m pipeline.build
```

## Phase status

- [x] Phase 0 — repository structure, tooling, data model, scoring specification
- [x] Phase 1 — collect (Tradeinn + Glisshop; Le Pape and i-Run stopped, see `docs/sources.md`)
- [x] Phase 2 — normalize (160 models from 924 Tradeinn listings)
- [x] Phase 3 — specs (9 of 25 brand sites allowed; see `docs/data-coverage.md`)
- [x] Phase 3b — retailer specs fallback (separate slot)
- [x] Phase 4 — reviews (RunRepeat, Believe in the Run, Esprit Trail)
- [x] Phase 5 — nlp (embeddings + NLI; evaluated on 30 AI-labelled models, see `docs/evaluation.md`)
- [ ] Phase 6 — build (shoes.json built and validated; waiting for the owner's review of the build report)
- [ ] Phase 7 — web
