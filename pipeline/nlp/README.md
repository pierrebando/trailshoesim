# pipeline/nlp/ (phase 5)

The small offline AI step: two multilingual Hugging Face models (CPU, no API key) read
the review conclusions and give each model a 0-10 score per scoring criterion, with the
sentence that shows it. A sentence-embedding model finds which criterion a sentence talks
about; a zero-shot NLI model says in which direction. Method and thresholds for non-specialists:
`docs/methodology-nlp.md`; settings: `pipeline/config/aspects.yaml`.

| File | Role |
|---|---|
| `sentences.py` | Stage 1: split EN/FR text and pros/cons into sentences (rules). |
| `aspects.py` | Stages 2-3: which criterion a sentence mentions (embeddings), direction (NLI), score; per-review aggregation. |
| `__main__.py` | `python -m pipeline.nlp`: all reviews -> `data/interim/expert_aspects.json` (source-weighted per model). |
| `make_labeling_sheet.py` | Blind sample of 30 models -> `data/interim/gold_labels.csv` to label. |
| `evaluate.py` | Coverage, accuracy, Spearman, confusion matrix vs the labels -> `docs/evaluation.md`. |

Both model ids and revisions are recorded in `expert_aspects.json` for reproducibility.
