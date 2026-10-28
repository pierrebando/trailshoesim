# Phase 5 evaluation

How well do the phase 5 aspect scores agree with a careful reading of the reviews?
Method in `docs/methodology-nlp.md`; code in `pipeline/nlp/evaluate.py`. The tables
between the `metrics` markers are generated (`python -m pipeline.nlp.evaluate --tag NAME`);
the text around them is written by hand.

## The labelled sample, and its main limit

* 30 models (240 model × criterion pairs) drawn by `make_labeling_sheet.py`: stratified by
  number of reviewing sources (16 / 12 / 2), 18 brands, fixed seed.
* Labels: `low`, `medium`, `high` or `not mentioned` per criterion, from what the
  reviewers say. 191 pairs are mentioned (111 high, 54 medium, 26 low); 49 are not.
* **The labels were made by the AI assistant (Claude), at the project owner's request**,
  from the same review texts the pipeline reads, without looking at the pipeline's
  scores (`labelled_by` column). They are not independent human labels: the labeller
  also designed the pipeline. Disagreeing reviewers were labelled `medium`, which is a
  judgement call. **Checked:** the project owner re-read the 5 rows with the most
  disagreements (Altra Mont Blanc Speed, Mizuno Neo Accera, Brooks Catamount 4, Salomon
  Ultra Glide 4, Brooks Cascadia 20) against the reviews and kept every label, including
  the "disagreement = medium" rule (`labelled_by` = `...; checked:owner`). The other
  25 rows are unchecked.
* Small sample: about 90 mentioned pairs per half, so an accuracy difference of ±0.05
  between two runs is within noise (one standard error is about 0.05).

## How to read the tables

* **Coverage**: of the pairs the labels call mentioned, how many get a pipeline score.
  **False mentions**: pipeline scores on pairs the labels call not mentioned.
* **Accuracy**: on pairs both call mentioned, share of identical classes (pipeline score
  ≤ 4 = low, ≥ 6 = high, in between = medium). **Reference**: the accuracy of always
  answering the most frequent label; a useful method must beat it.
* **Spearman**: rank correlation between the 0-10 score and the label order
  (low < medium < high); 1 = same order, 0 = no relation.
* **DEV / TEST**: alternate rows of the sheet. Changes were chosen by looking at DEV only;
  TEST was looked at only to report.

## Before: embedding direction (aspects.yaml 0.2.0)

<!-- metrics:baseline:start -->
Run `baseline`: aspects.yaml version 0.2.0, direction method `embedding`.

**All 30 models**

| Criterion | Coverage (found / mentioned) | False mentions | Accuracy (3 classes) | Spearman |
|---|---|---|---|---|
| cushioning | 25/26 (96%) | 2/27 (7%) | 0.52 (25) | 0.25 |
| protection | 19/21 (90%) | 4/23 (17%) | 0.63 (19) | 0.21 |
| grip | 21/26 (81%) | 1/22 (5%) | 0.71 (21) | 0.41 |
| stability | 25/26 (96%) | 0/25 (0%) | 0.52 (25) | 0.43 |
| responsiveness | 19/23 (83%) | 3/22 (14%) | 0.21 (19) | 0.04 |
| lightness | 24/25 (96%) | 3/27 (11%) | 0.50 (24) | 0.62 |
| durability | 18/21 (86%) | 5/23 (22%) | 0.61 (18) | 0.37 |
| fit_width | 22/23 (96%) | 4/26 (15%) | 0.68 (22) | 0.61 |
| **ALL** | 173/191 (91%) | 22/195 (11%) | 0.55 (173) | 0.35 |

Reference: always answering the most frequent label gives accuracy 0.58 (always `high`).

**DEV half**

| Criterion | Coverage (found / mentioned) | False mentions | Accuracy (3 classes) | Spearman |
|---|---|---|---|---|
| cushioning | 12/13 (92%) | 1/13 (8%) | 0.42 (12) | 0.13 |
| protection | 8/10 (80%) | 3/11 (27%) | 0.62 (8) | 0.39 |
| grip | 10/14 (71%) | 0/10 (0%) | 0.70 (10) | 0.75 |
| stability | 13/14 (93%) | 0/13 (0%) | 0.31 (13) | -0.07 |
| responsiveness | 11/13 (85%) | 0/11 (0%) | 0.27 (11) | 0.25 |
| lightness | 12/13 (92%) | 1/13 (8%) | 0.58 (12) | 0.80 |
| durability | 9/10 (90%) | 3/12 (25%) | 0.44 (9) | 0.15 |
| fit_width | 11/12 (92%) | 1/12 (8%) | 0.73 (11) | 0.82 |
| **ALL** | 86/99 (87%) | 9/95 (9%) | 0.50 (86) | 0.34 |

Reference: always answering the most frequent label gives accuracy 0.57 (always `high`).

**TEST half**

| Criterion | Coverage (found / mentioned) | False mentions | Accuracy (3 classes) | Spearman |
|---|---|---|---|---|
| cushioning | 13/13 (100%) | 1/14 (7%) | 0.62 (13) | 0.35 |
| protection | 11/11 (100%) | 1/12 (8%) | 0.64 (11) | 0.10 |
| grip | 11/12 (92%) | 1/12 (8%) | 0.73 (11) | -0.10 |
| stability | 12/12 (100%) | 0/12 (0%) | 0.75 (12) | 0.73 |
| responsiveness | 8/10 (80%) | 3/11 (27%) | 0.12 (8) | -0.15 |
| lightness | 12/12 (100%) | 2/14 (14%) | 0.42 (12) | 0.46 |
| durability | 9/11 (82%) | 2/11 (18%) | 0.78 (9) | 0.66 |
| fit_width | 11/11 (100%) | 3/14 (21%) | 0.64 (11) | 0.35 |
| **ALL** | 87/92 (95%) | 13/100 (13%) | 0.60 (87) | 0.37 |

Reference: always answering the most frequent label gives accuracy 0.60 (always `high`).

**Confusion matrix (all models, all criteria)**

| label \ pipeline | low | medium | high | not mentioned |
|---|---|---|---|---|
| low | 8 | 7 | 11 | 0 |
| medium | 11 | 14 | 26 | 3 |
| high | 10 | 13 | 73 | 15 |
| not mentioned | 6 | 2 | 14 | 27 |
<!-- metrics:baseline:end -->

**Comment.** Detection works: 91% of the mentioned criteria are found, with 11% false
mentions. The **direction does not**: overall accuracy 0.55 is *below* the 0.58 of always
answering "high", and Spearman is 0.35. Responsiveness is the worst (accuracy 0.21,
Spearman 0.04): many reviews talk about "energy return" in sentences that are about
foam in general. The confusion matrix shows the problem: 11 of the 26 `low` pairs come
out `high`. The hand-written check set (31/32 directions right) had hidden this: its
sentences are short and one-topic, real review sentences are not.

## What was tried (DEV half only)

| Change | DEV coverage | DEV accuracy | DEV Spearman | Kept? |
|---|---|---|---|---|
| baseline (0.2.0) | 86/99 | 0.50 | 0.34 | – |
| polarity_scale 0.05 or 0.08 (instead of 0.15) | 86/99 | 0.49 | 0.34 | no: no effect |
| neutral_band 0 or 0.05 (instead of 0.02) | 86/99 | 0.50 | 0.33-0.34 | no: no effect |
| ignore pros/cons lists | 38/99 | 0.50 | 0.19 | no: pros/cons carry most of the signal |
| **NLI direction**, d from entailment − contradiction of both hypotheses | 86/99 | 0.52 | 0.38 | **yes** |
| NLI, entailment only | 86/99 | 0.38 | 0.23 | no |
| NLI, "high" hypothesis only | 86/99 | 0.37 | 0.25 | no |
| NLI + sentence weight × NLI confidence | 86/99 | 0.53 | 0.37 | no: no clear gain, more complex |
| NLI + ignore neutral sentences (\|d\| < 0.2) | 86/99 | 0.51 | 0.35 | no |
| **NLI + stability descriptors = platform only** (no lockdown phrases) | 84/99 | 0.57 | 0.43 | **yes** |
| + durability hypothesis "poor durability" | 84/99 | 0.57 | 0.42 | no: no effect |

The threshold changes did nothing because the problem is the *signal*, not its scale: the
embedding of "lacks cushioning" is close to the embedding of "very cushioned". The NLI
model is trained for exactly this distinction. The stability change follows the scoring
spec (stability = platform: stack and width): heel-slip sentences were counted as
stability and pulled stable shoes (MTL Adapt Matryx, Dynafit Ultra 100 3) down.

## After: NLI direction (aspects.yaml 0.3.0)

<!-- metrics:after:start -->
Run `after`: aspects.yaml version 0.3.0, direction method `nli`.

**All 30 models**

| Criterion | Coverage (found / mentioned) | False mentions | Accuracy (3 classes) | Spearman |
|---|---|---|---|---|
| cushioning | 25/26 (96%) | 2/27 (7%) | 0.52 (25) | 0.55 |
| protection | 19/21 (90%) | 4/23 (17%) | 0.63 (19) | 0.66 |
| grip | 21/26 (81%) | 1/22 (5%) | 0.86 (21) | 0.28 |
| stability | 22/26 (85%) | 0/22 (0%) | 0.55 (22) | 0.34 |
| responsiveness | 19/23 (83%) | 3/22 (14%) | 0.37 (19) | 0.30 |
| lightness | 24/25 (96%) | 3/27 (11%) | 0.62 (24) | 0.60 |
| durability | 18/21 (86%) | 5/23 (22%) | 0.56 (18) | 0.28 |
| fit_width | 22/23 (96%) | 4/26 (15%) | 0.64 (22) | 0.82 |
| **ALL** | 170/191 (89%) | 22/192 (11%) | 0.59 (170) | 0.49 |

Reference: always answering the most frequent label gives accuracy 0.58 (always `high`).

**DEV half**

| Criterion | Coverage (found / mentioned) | False mentions | Accuracy (3 classes) | Spearman |
|---|---|---|---|---|
| cushioning | 12/13 (92%) | 1/13 (8%) | 0.50 (12) | 0.74 |
| protection | 8/10 (80%) | 3/11 (27%) | 0.75 (8) | 0.85 |
| grip | 10/14 (71%) | 0/10 (0%) | 0.90 (10) | 0.62 |
| stability | 11/14 (79%) | 0/11 (0%) | 0.55 (11) | 0.00 |
| responsiveness | 11/13 (85%) | 0/11 (0%) | 0.45 (11) | 0.34 |
| lightness | 12/13 (92%) | 1/13 (8%) | 0.67 (12) | 0.59 |
| durability | 9/10 (90%) | 3/12 (25%) | 0.33 (9) | 0.17 |
| fit_width | 11/12 (92%) | 1/12 (8%) | 0.45 (11) | 0.69 |
| **ALL** | 84/99 (85%) | 9/93 (10%) | 0.57 (84) | 0.43 |

Reference: always answering the most frequent label gives accuracy 0.57 (always `high`).

**TEST half**

| Criterion | Coverage (found / mentioned) | False mentions | Accuracy (3 classes) | Spearman |
|---|---|---|---|---|
| cushioning | 13/13 (100%) | 1/14 (7%) | 0.54 (13) | 0.36 |
| protection | 11/11 (100%) | 1/12 (8%) | 0.55 (11) | 0.50 |
| grip | 11/12 (92%) | 1/12 (8%) | 0.82 (11) | -0.10 |
| stability | 11/12 (92%) | 0/11 (0%) | 0.55 (11) | 0.68 |
| responsiveness | 8/10 (80%) | 3/11 (27%) | 0.25 (8) | 0.30 |
| lightness | 12/12 (100%) | 2/14 (14%) | 0.58 (12) | 0.72 |
| durability | 9/11 (82%) | 2/11 (18%) | 0.78 (9) | 0.52 |
| fit_width | 11/11 (100%) | 3/14 (21%) | 0.82 (11) | 0.86 |
| **ALL** | 86/92 (93%) | 13/99 (13%) | 0.62 (86) | 0.57 |

Reference: always answering the most frequent label gives accuracy 0.60 (always `high`).

**Confusion matrix (all models, all criteria)**

| label \ pipeline | low | medium | high | not mentioned |
|---|---|---|---|---|
| low | 10 | 12 | 3 | 1 |
| medium | 10 | 23 | 18 | 3 |
| high | 3 | 23 | 68 | 17 |
| not mentioned | 3 | 6 | 13 | 27 |
<!-- metrics:after:end -->

**Comment.**

| | Before (0.2.0) | After (0.3.0) | Reference "always high" |
|---|---|---|---|
| Coverage, all | 173/191 (91%) | 170/191 (89%) | – |
| Accuracy, DEV | 0.50 | 0.57 | 0.57 |
| Accuracy, TEST | 0.60 | 0.62 | 0.60 |
| Spearman, DEV | 0.34 | 0.43 | 0 (constant) |
| Spearman, TEST | 0.37 | **0.57** | 0 (constant) |
| Opposite-direction errors (low↔high), all | 21 | **6** | – |

* The clearest gain is in the **wrong-way errors**: a `low` shoe scored `high`, or the
  reverse, fell from 21 to 6. Those are the errors that would mislead a runner. On the
  TEST half (never used to choose), Spearman went from 0.37 to 0.57.
* **Accuracy only matches the "always high" reference** (0.57-0.62 vs 0.57-0.60). Most
  remaining errors are `high` labels scored `medium` (23 pairs): neutral or off-topic
  sentences score ~5 and dilute a clear sentence. The 0-10 score orders shoes much
  better than the three classes suggest, which is what phase 6 uses.
* **Strong**: fit_width (Spearman 0.82), protection (0.66), lightness (0.60), cushioning
  (0.55), grip (accuracy 0.86; low Spearman only because almost every grip label is
  `high`).
* **Weak**: responsiveness (accuracy 0.37, Spearman 0.30). Reviewers rarely say "not
  responsive"; they write "lacks pop", "modest energy return", "far from supple or
  energetic". Durability (Spearman 0.28): durability sentences are rare (18 pairs) and
  short concern phrases ("Major durability concerns") read as neutral to the NLI model.
  Stability is unstable between halves (DEV 0.00, TEST 0.68 on 11 pairs each).
* Coverage fell by 3 pairs: the narrower stability descriptors no longer catch "foot
  secure on technical terrain" sentences that the labeller counted as stability.
* One labelled model has no text at all in the pipeline: the Esprit Trail review of the
  Scott Kinabalu 3 puts its conclusion under "le carnet de notes", which the phase 4
  parser does not recognise (1 of 117 reviews). Its 6 mentioned criteria count as missed.

## Recommendations for phase 6

* Use the expert sub-score with its confidence: weight it by the number of sentences and
  reviews (`n_sentences`, `n_reviews`), and lower it for responsiveness and durability.
* Keep the evidence excerpt next to every expert-based reason in the UI, so a wrong
  score can be spotted.
* Possible next steps (not done): fix the Esprit Trail "carnet de notes" heading; add
  responsiveness hypotheses phrased like reviewers ("The shoe lacks pop."); check more
  label rows.
