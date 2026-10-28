# Phase 5 methodology: from review text to criterion scores

This page explains, for a reader who is not an NLP specialist, how the pipeline turns the
conclusions of expert reviews into a 0-10 score per scoring criterion (cushioning,
protection, grip, stability, responsiveness, lightness, durability, fit width). Every
number quoted here lives in `pipeline/config/aspects.yaml`, and the code is in
`pipeline/nlp/`.

## The question we answer

For each shoe model and each criterion: *what do the reviewers say?* For example "the
reviews say the grip is excellent" → grip high, with the sentence that shows it.
We do **not** try to rebuild the whole review or to give a general opinion. When the
reviews do not talk about a criterion, the answer is "not mentioned" (null), and phase 6
then relies on the specs or lowers the confidence, as for any missing data.

## The input

The conclusion section (plus the pros/cons lists when the site has them) of the 118
reviews collected in phase 4, for 81 models: RunRepeat and Believe in the Run (English)
and Esprit Trail (French). The full texts stay on the project owner's computer
(`data/raw/reviews/conclusions.json`, gitignored); only ≤30-word excerpts are committed.

## The three stages

### 1. Split into sentences (`sentences.py`)

A review conclusion is split at `.`, `!`, `?` or `…` followed by a capital letter or a
digit. Common abbreviations ("vs.", "env.", "approx.") do not end a sentence, reviewer
tags such as "SAM :" are removed, and fragments shorter than 3 words are dropped. Each
pros/cons item ("Heavy", "Stable ride") counts as a sentence of its own because it is
short and to the point. This is simple rules, not AI: rules are enough here and are easy
to check.

### 2. Which criterion does the sentence talk about? (`aspects.py`, matching)

We use a **sentence-embedding model**: a neural network that turns a sentence into a list
of 768 numbers (a *vector*) such that sentences with similar meanings get similar vectors,
even if they use different words or different languages. "Elle accroche bien sur le
mouillé" and "great grip on wet rock" end up close together.

How close two vectors are is measured by **cosine similarity**: about 1 for the same
meaning, about 0 for unrelated sentences.

For each criterion we wrote a few short **descriptors** in English and French, split into
two poles: *high* ("excellent grip on wet rocks and mud") and *low* ("slippery on wet rock,
poor traction"). A sentence's **relevance** to a criterion is its best similarity to any
descriptor of that criterion.

A sentence **mentions** a criterion when three conditions hold:

| Condition | Threshold | Why |
|---|---|---|
| relevance ≥ `mention_min_similarity` | 0.55 | Below this, the sentence is about something else. |
| relevance ≥ best relevance of the sentence − `mention_max_gap_to_best` | 0.05 | A sentence can mention two criteria ("light and grippy"), but not all eight just because it is about running shoes. |
| relevance ≥ background similarity + `background_margin` | 0.05 | Reviews also talk about price, colour, the test period... We wrote 12 such **background** phrases; a sentence closer to them than to the criteria is ignored. |

### 3. In which direction? (`aspects.py`, polarity)

**Since version 0.3.0 (current): a zero-shot NLI model.** NLI ("natural language
inference") models are trained on pairs *premise / hypothesis* and answer: does the
premise imply the hypothesis (*entailment*), contradict it (*contradiction*), or neither
(*neutral*)? For each mentioned criterion we ask about two hypotheses, e.g. for lightness
"The shoe is light." and "The shoe is heavy.":

`d = ((P(entail HIGH) − P(contradict HIGH)) − (P(entail LOW) − P(contradict LOW))) / 2`

d lies between −1 (clearly low) and +1 (clearly high); `score = 5 + 5 × d`. A sentence
that only names the topic ("The outsole is Vibram Megagrip") is neutral to both
hypotheses and scores about 5. The model is
`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (multilingual, so French
sentences are tested against the English hypotheses; pinned revision, 558 MB, CPU).

**Version 0.2.0 (baseline, still available with `direction.method: embedding`):**
`d = similarity to the closest HIGH descriptor − similarity to the closest LOW
descriptor`, score = `5 + 5 × clip(d / 0.15, −1, 1)` (exactly 5 when |d| < 0.02). It was
replaced because the evaluation showed it was hardly better than chance on real reviews:
a sentence vector mostly encodes the *topic*, so "lacks cushioning" and "very cushioned"
are both close to the cushioning descriptors (see `docs/evaluation.md`).

For fit width, "high" means roomy/wide and "low" means narrow/snug.

## Aggregation

* **Within one review**: the scores of all sentences that mention the criterion are
  averaged, each weighted by `relevance − 0.55` (at least 0.01), so a sentence that is
  clearly about the criterion counts more than one that is barely above the threshold.
  The evidence kept is the most relevant sentence, cut to 30 words.
* **Across reviews of the same model**: the review scores are averaged with the source
  weights in `scoring.yaml` (`expert_reviews.source_weights`: RunRepeat 1.2, others 1.0;
  RunRepeat measures in a lab and its texts are the most systematic). The evidence kept is
  that of the most relevant review, with its link.

Output: `data/interim/expert_aspects.json` (per model: the eight criteria, each a score
with evidence and source, or null; plus the per-review detail).

## Choice of the model

Constraints: free, runs **offline on a laptop CPU**, understands **English and French**.
Three Hugging Face models were compared on a small hand-written EN/FR set of 15 sentences
(one criterion and one direction each):

| Model | Size | Right criterion | Right direction |
|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | 118 M | 11/15 | 12/15 |
| `intfloat/multilingual-e5-small` | 118 M | 11/15 | 14/15 |
| **`paraphrase-multilingual-mpnet-base-v2`** | 278 M | **12/15** | **15/15** |

We kept `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (pinned revision in
`aspects.yaml`), about 4 ms per sentence on CPU. 15 sentences is a tiny test; it only
ruled out clear losers.

The NLI model was first left out (slower, and the embedding direction was right on the
hand-written check set). The evaluation on real reviews reversed that decision: the
embedding model is kept for *which criterion* (it finds 91% of the mentions), and the NLI
model now decides *which direction*. It is called only on the (sentence, criterion) pairs
already detected, two hypotheses each, so the full run stays a few minutes on a laptop.

## Calibration of the thresholds

Thresholds were set on `tests/fixtures/nlp/sentences.yaml`: 48 hand-written sentences,
32 about a criterion (2 high + 2 low per criterion, EN and FR) and 16 about something else
(price, colour, history of the model...).

| Setting | On-topic found | Off-topic sentences wrongly matched |
|---|---|---|
| first try: 0.45 / gap 0.08 / no background | 30/32 | 16/16 |
| **current: 0.55 / gap 0.05 / background margin 0.05** | **29/32** | **0/16** |

With the current setting, all 29 found mentions have the right direction (with both the
embedding and the NLI direction), and 7 extra (second) criteria are attached to on-topic
sentences. The 3 misses are a sentence mixing
two ideas (firm + rocks), a short French sentence about responsiveness, and a torn upper
(durability).

**Caveat:** this is optimistic. The same person wrote the check set, the descriptors and
the background list, and the sentences are cleaner than real reviews. The honest measure
is the labelled sample below: there the same direction rule that was perfect on the check
set gets only 55% of the classes right.

## Known failure modes (seen on the real reviews)

* Off-topic sentences slightly above the threshold: "Ideal for forefoot strikers" →
  stability, "Excellent versatility" → durability, sentences about the heel collar →
  stability. With the NLI direction they mostly score ~5 (neutral), which pulls the
  criterion towards "medium" instead of flipping it.
* Short "concern" phrases: the NLI model finds "Major durability concerns" neutral to "The
  shoe wears out quickly." (score 5 instead of low).
* Until 0.3.0, lockdown sentences (heel slip) counted as stability; the stability
  descriptors now describe the platform only, as in `docs/scoring-spec.md`.
* Comparisons ("less stable than the previous version") and negations ("not as heavy as
  it looks") are hard for embeddings: the vector captures the topic better than the logic.
* Irony, and conclusions that are mostly about other shoes.

## Evaluation protocol (labelled sample)

`python -m pipeline.nlp.make_labeling_sheet` draws 30 models with a fixed random seed,
stratified by number of reviewing sources (16 with one, 12 with two, 2 with three) and
spread across brands (18 brands). It writes:

* `data/interim/gold_labels.csv`: one row per model, links and short excerpts, and one
  empty column per criterion;
* `data/raw/reviews/labeling_texts.md` (local only): the full texts to read.

The sheet is **blind**: it does not show the pipeline's scores. A labeller reads the
reviews and writes `low`, `medium`, `high` or `not mentioned` for each criterion, judging
what the reviewers say (not their own knowledge of the shoe); when the reviewers disagree,
the label is `medium`.

**Who labelled (column `labelled_by`).** The project owner asked the AI assistant
(Claude) to fill the sheet. It read the same review texts as the pipeline (local cache,
and the cached page for the one review whose conclusion the parser missed) without
looking at the pipeline's scores. These labels are **not independent human labels**: the
labeller also designed the pipeline, and an LLM has its own biases. The project owner
checked the 5 rows with the most reviewer disagreements and kept all their labels; the
other 25 are unchecked. Changing a label and re-running `python -m pipeline.nlp.evaluate`
updates every table.

`pipeline/nlp/evaluate.py` (after labelling) compares, per criterion:

* **coverage**: how many criteria the human says are mentioned are also found by the model
  (and how many the model finds that the human says are not mentioned);
* **accuracy** on the three classes low / medium / high (model score ≤ 4 = low, ≥ 6 =
  high, in between = medium) where both say "mentioned";
* **Spearman correlation** between the model score and the human class (does the order
  agree?);
* a **confusion matrix**.

The 30 models are split into a DEV half and a TEST half (alternate rows). Improvements are
chosen by looking at the DEV half only; the TEST half is the honest estimate. Results and
before/after numbers: `docs/evaluation.md`.
