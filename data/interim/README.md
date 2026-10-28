# data/interim/

Intermediate, committed JSON/CSV files produced by phases 1-5. Allowed content:
extracted facts with provenance and excerpts of at most ~30 words. Never raw HTML or
full article text.

| File | Phase | Content |
|---|---|---|
| `retailer_listings.json` | 1 | One record per retailer product page (`RetailerListing`). |
| `collect_report.json` | 1 | Counts, failures, possibly truncated pages per site. |
| `catalog.json` | 2 | One record per canonical model (`InterimCatalog`). |
| `needs_review.csv` | 2 | Uncertain matches; fill the `decision` column. |
| `normalize_report.json` | 2 | Phase 2 counts and the most uncertain matches. |
| `expert_reviews.json` | 4 | Reviews per model: metadata, ratings, lab values, short excerpt, link. |
| `reviews_needs_review.csv` | 4 | Ambiguous review matches; `decision` = accept / reject. |
| `expert_aspects.json` | 5 | Per model and criterion: 0-10 score from the reviews, evidence excerpt, source (or null). |
| `gold_labels.csv` | 5 | Labels (low / medium / high / not mentioned) on 30 models, to evaluate phase 5; `labelled_by` says who labelled. |
