# Phase 5 report: AI aspect scores from expert reviews

## What was produced

* `pipeline/nlp/` (`python -m pipeline.nlp`): review conclusions + pros/cons → sentences
  (EN/FR rules) → which criterion (multilingual sentence embeddings) → which direction
  (zero-shot multilingual NLI) → 0-10 per review → per model, weighted by source
  (`scoring.yaml expert_reviews.source_weights`). Two pinned Hugging Face models, offline,
  CPU; ~8 minutes for all 81 models on a laptop.
* `data/interim/expert_aspects.json`: 81 models, 526 (model, criterion) scores, each with
  a ≤30-word evidence excerpt, source and link; null when not mentioned.
* `pipeline/config/aspects.yaml` (version 0.3.0): every threshold, descriptor and NLI
  hypothesis, with its reason.
* `docs/methodology-nlp.md` (for non-specialists) and `docs/evaluation.md` (results).
* `data/interim/gold_labels.csv`: 30 models × 8 criteria labelled; `make_labeling_sheet.py`,
  `evaluate.py`.
* Tests: `tests/test_nlp.py` (fake models, metrics, and the real models on 48 hand-written
  EN/FR sentences in `tests/fixtures/nlp/sentences.yaml`).

## Counts

| Criterion | Models scored (of 81) |
|---|---|
| cushioning | 75 |
| protection | 65 |
| grip | 58 |
| stability | 62 |
| responsiveness | 59 |
| lightness | 73 |
| durability | 62 |
| fit_width | 72 |

## Evaluation (30 labelled models; details in `docs/evaluation.md`)

| | Before (embedding direction) | After (NLI direction) |
|---|---|---|
| Criteria found / mentioned | 91% | 89% |
| Accuracy low/medium/high (TEST half) | 0.60 | 0.62 (always "high": 0.60) |
| Spearman (TEST half) | 0.37 | 0.57 |
| Opposite-direction errors | 21 | 6 |

## Known problems

* **The labels are not human labels.** At the project owner's request the AI assistant
  filled `gold_labels.csv` from the cached review texts, blind to the pipeline's scores.
  It also built the pipeline, so the evaluation is not independent. The project owner
  checked the 5 most disputed rows and kept every label; 25 rows are unchecked.
* Accuracy on the three classes is only at the level of "always high"; the gain is in the
  ordering (Spearman) and in fewer wrong-way errors.
* Responsiveness and durability are weak (Spearman ~0.3); off-topic sentences slightly
  above the threshold still dilute clear ones towards 5.
* One Esprit Trail review (Scott Kinabalu 3) has no extracted conclusion ("le carnet de
  notes" heading not recognised by the phase 4 parser).
* The full run takes ~8 min (NLI model) and needs ~0.9 GB of models in the Hugging Face cache.

## What the project owner should verify

1. Done: rows 1, 8, 18, 23 and 27 of `gold_labels.csv` checked, labels kept.
2. Look at 10 evidence excerpts in `expert_aspects.json` for shoes you know.
3. Decide whether phase 6 should down-weight the expert sub-score for responsiveness and
   durability.
