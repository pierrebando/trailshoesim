# pipeline/reviews/ (phase 4)

Specialist reviews of the catalogue models. Sources and access checks: `docs/sources.md`.

| Module | Source | Discovery | What is read |
|---|---|---|---|
| `runrepeat.py` | RunRepeat (en) | trail catalogue pages | score /100 + sub-scores, verdict, pros/cons, **lab measurements** |
| `believe_in_the_run.py` | Believe in the Run (en) | sitemap (`/shoe-reviews/`) | grades A-F, "Final thoughts", likes/dislikes |
| `esprit_trail.py` | Esprit Trail (fr) | post sitemaps (`/test-`) | "le verdict" |
| `common.py` | – | – | strict model/version matching, sections, excerpts |
| `__main__.py` | – | – | the phase 4 pipeline |

```bash
python -m pipeline.reviews --source all          # every source
python -m pipeline.reviews --source runrepeat    # one source (others kept)
```

Outputs: `data/interim/expert_reviews.json` (committed: metadata, ratings on the source's
scale, lab values, <= 30-word excerpt, link), `data/interim/reviews_needs_review.csv`
(ambiguous matches: write `accept` or `reject` in `decision`, then re-run), and
`data/raw/reviews/conclusions.json` (full conclusions, gitignored, phase 5 only).
