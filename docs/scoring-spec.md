# Scoring specification

Version **0.3.1**. Must match `version` in `pipeline/config/scoring.yaml`.

Changes in 0.3.1: RunRepeat's lab weight and drop become spec sources (§2.2).

Changes in 0.3.0 (phase 7 review): in the final score (§6.1), a weighted term with an
unknown value counts as a neutral `final.missing_term_value` (5) instead of being dropped.
Before, a max-cushion shoe with unknown responsiveness ranked first for a runner who asked
for a dynamic shoe: its unknown weak point simply did not count.

Changes in 0.2.1: minimum spec coverage 0.6 → 0.45, and a criterion may list
`required_inputs` like terrain does (protection requires the forefoot stack).

Changes in 0.2.0 (after the phase 6 review of real data): minimum spec coverage 0.4 →
0.6 (§2.3); expert-only scores shrink towards a neutral 5 when few reviews exist (§2.5);
platform widths may come from lab measurements (§2.2); foam rules for compounds whose
type is stated in a collected review (§2.1).

This document says exactly how Trail Shoe Finder scores, ranks, explains and compares
shoes. Later phases only implement it. Every number lives in
`pipeline/config/scoring.yaml` and is quoted below by its YAML path, e.g.
`criteria.grip.blend`. To change a number, edit the YAML, not the code or this document.

> **These are heuristics, not scientific laws.** The formulas encode reasonable
> rules of thumb from the running world (more stack means more cushioning, deeper lugs
> are better in mud, heavier runners and longer distances benefit from more cushioning...).
> They are meant to be transparent and tunable. They are not validated biomechanics.

---

## 0. General principles

### 0.1 Where each part is computed

| Part | Depends on the runner? | Computed | Stored in |
|---|---|---|---|
| Criterion scores (§2) | no | offline, Python (phase 6) | `shoes.json` → `criteria_scores` |
| Terrain scores (§3) | no | offline | `terrain_scores` |
| Bayesian buyer rating (§4) | no | offline | `buyer_rating` |
| Confidence (§8) | no | offline | `confidence` |
| Hard filters (§1), weights (§5), final score and explanation (§6), similarity (§7) | yes | browser, JavaScript (phase 7) | not stored |

The build exports `scoring.yaml` to `data/processed/scoring_config.json` so the browser
uses the same constants as the pipeline.

### 0.2 Missing data: never guess

When an input is unknown we **drop it and re-normalise** the remaining weights. We never
replace it with an average or a typical value. The share of weight that was actually
available (the *coverage*) is recorded. Low coverage lowers confidence and can remove a
shoe from the ranking (§6.3).

### 0.3 Helper functions

**Piecewise-linear interpolation.** `interp(x, anchors)`, where
`anchors = [[x1, y1], ..., [xn, yn]]` and `x1 < x2 < ... < xn`:

```
interp(x) = y1                                          if x <= x1
          = yn                                          if x >= xn
          = yi + (x - xi) * (y(i+1) - yi) / (x(i+1) - xi)  if xi <= x <= x(i+1)
```

It is continuous, easy to read, and each anchor can be tuned on its own.

**Clamp.** `clamp(t, 0, 1) = min(1, max(0, t))`.

**Smoothstep** (a smooth ramp from 0 to 1, with zero slope at both ends):
`smoothstep(t) = 3t² − 2t³` with `t = clamp(t, 0, 1)`.

**Rounding.** Scores are computed in full precision and only rounded when written
(`common.output_decimals`) or displayed.

### 0.4 Generic sub-score from inputs

Criterion spec sub-scores (§2) and terrain scores (§3) use the same evaluator. A
sub-score has a list of inputs. Each input has a `weight` and one way of turning a spec
value into a 0-10 number:

| Kind | YAML | Value → score |
|---|---|---|
| numeric | `anchors` | `interp(value, anchors)` |
| text spec matched to a class | `lookup: <table>.<attr>` | rules of `lookups.<table>`, then the class attribute (§2.1) |
| plate type | `lookup: plate_classes.<attr>` | direct table lookup |
| categorical | `table: {...}` | direct mapping |
| count | `transform: count` + `anchors` | `interp(len(value), anchors)` |
| fallback | `fallback: {field, anchors}` | if the main field is null, use this field with these anchors |

An input is **missing** if its spec value is null, or if a text value matches no
lookup rule. Then, with `P` the inputs that are present:

```
coverage  = Σ_{i∈P} w_i  /  Σ_{all i} w_i
sub_score = Σ_{i∈P} w_i · f_i(value_i)  /  Σ_{i∈P} w_i
```

The sub-score is **null** if `coverage < min_coverage` or if a required input is missing.
For criteria, `min_coverage` is `common.min_spec_input_coverage` and the required inputs
are `criteria.<c>.required_inputs` (none unless listed). For terrain, it is
`terrain.min_input_coverage` and the required inputs are `terrain.required_inputs`.
Input names are recorded in `inputs_used` / `inputs_missing` (e.g. `specs.lug_depth_mm`).

---

## 1. Hard filters (blockers)

Hard filters run **before** scoring. A shoe that fails one is not shown in the ranking.

| Filter | Default | A shoe passes if... |
|---|---|---|
| Max price | none | its lowest `retail[].price_eur` ≤ max price |
| Excluded brands | none | its `brand` (case-insensitive) is not in the list |
| Waterproof | any | `yes`: `specs.waterproof.value == true`; `no`: `== false`; `any`: always |
| Min / max drop | none | `min ≤ specs.drop_mm.value ≤ max` |
| Width | any | the requested width is in `specs.width_options.value` |
| Gender | any | the runner's gender, or `unisex`, is in `gender_variants` |

**Unknown values.** If a filter is set (not "any") and the shoe's value is null, the shoe
**fails**. We cannot promise it matches. The UI shows how many shoes were hidden this way
("3 shoes hidden because their drop is unknown").

The runner's *foot width* (profile) is different from the *width filter*. The profile
value only changes weights (§5.6). The filter is a strict requirement.

---

## 2. Criterion scores (0-10, offline)

There are eight criteria: `cushioning, protection, grip, stability, responsiveness,
lightness, durability, fit_width`. Each score blends a **spec sub-score** (from
manufacturer data) with an **expert sub-score** (from review aspects).

### 2.1 Lookup tables (`lookups`)

Foam and rubber names are free text ("Vibram Megagrip with Litebase", "supercritical
EVA"). They are lower-cased and checked against `lookups.foam_classes.rules` /
`lookups.rubber_classes.rules` in order. The **first** rule with a matching substring
gives the class, so specific names are listed before generic ones (e.g. "supercritical"
before "eva"). Each class has 0-10 attributes:

- foam: `cushioning`, `responsiveness`, `durability`
- rubber: `grip`, `durability`
- plate (`lookups.plate_classes`): `protection`, `responsiveness`

If no rule matches, the input is **missing**. An unknown compound is not assumed to be
average. A brand compound name (e.g. "EExpure", "DNA Flash") is added to a rule only when
a collected source states its type; the evidence is quoted next to the rule in the YAML. These tables are the most subjective part of the system. They are starting
values to review against expert reviews in phase 5.

### 2.2 Spec inputs per criterion (`criteria.<name>.spec_inputs`)

| Criterion | Inputs (weight) | Idea |
|---|---|---|
| cushioning | heel stack (0.45), forefoot stack (0.30), foam class (0.25) | more foam, softer foam → more cushioning |
| protection | plate (0.55), forefoot stack (0.45, **required**) | rock plate and thick forefoot block sharp rocks |
| grip | rubber class (0.45), lug depth (0.45), lug spacing (0.10) | sticky rubber and deep lugs grip better off-road |
| stability | heel stack, inverted (0.60), forefoot platform width (0.20), heel platform width (0.20) | low and wide = stable |
| responsiveness | foam class (0.70), plate (0.30) | PEBA / supercritical foams and carbon plates return energy |
| lightness | weight (1.0) | lighter = higher score |
| durability | rubber class (0.60), foam class (0.40) | hard rubber and EVA/eTPU last longer than sticky rubber and PEBA |
| fit_width | number of width options (1.0) | more options = easier fit; mostly from expert reviews |

Notes:

- **Weight.** `weight_g` is for the men's reference size (usually US 9). If only a
  women's weight is published, it is stored in `weight_women_g` and used with its own
  anchors (`fallback`). This way we never convert women's to men's weights with a guessed factor.
- **Plate `none`.** Use `none` only when the source says there is no plate, or lists the
  full midsole construction. If the page is silent, store null with a reason.
- **Drop.** If the page gives both stacks but no drop, `drop_mm` may be derived as
  `heel − forefoot` with `source_name: "derived from stack heights"` and the stack URL.
  This is a calculation, not a guess.
- **Platform widths** are rarely published by manufacturers. Since 0.2.0 they come from a
  review source's lab measurement when there is one (RunRepeat "midsole width", heel and
  forefoot); otherwise they are null and stability falls back on stack height.
- **Source priority.** Each spec field takes the manufacturer value, else a lab
  measurement (stack heights, lug depth, platform widths, weight, drop), else the
  retailer's value. **Exception: the drop** takes stated values first (manufacturer, then
  retailer) and the lab measurement only when nobody states one, because a measured drop
  can differ a lot from the designed drop that runners filter on.

### 2.3 Spec sub-score

`S_c` = generic evaluator (§0.4) applied to `criteria.<c>.spec_inputs`. It is null if
coverage < `common.min_spec_input_coverage`.

### 2.4 Expert sub-score

Let `R_c` be the expert reviews whose `aspects` contain criterion `c`, and `n_c = |R_c|`:

```
E_c = mean over r ∈ R_c of r.aspects[c].score_0_10      (null if n_c = 0)
```

Each review counts once, whatever its length, so one very long test cannot dominate.

### 2.5 Blend

With `(b_spec, b_exp) = criteria.<c>.blend` and `N = expert_reviews.full_weight_review_count`:

```
w_s = b_spec                       if S_c is not null, else 0
w_e = b_exp · min(1, n_c / N)      if E_c is not null, else 0
score_c = (w_s · S_c + w_e · E_c) / (w_s + w_e)        null if w_s + w_e = 0
```

The expert weight grows with the number of reviews, so one review only moves the score
a little.

**No spec sub-score** (`S_c` null, `E_c` known). The formula above would give the reviews
100 % of the score, even for one review. Instead, with `t = min(1, n_c / N)` and
`p = expert_reviews.prior_score_without_specs` (5, neutral):

```
score_c = t · E_c + (1 − t) · p
```

One review moves the score a third of the way from 5 (N = 3); three reviews give `E_c`.
The prior is recorded in the provenance as `neutral_prior` with weight `1 − t`. It is
not a guessed value for a missing input: without any review the score stays null. Blend weights differ by criterion. Lightness is almost pure spec (0.9 / 0.1)
because weight is objective. Durability and fit are mostly expert (0.3 / 0.7, 0.2 / 0.8)
because specs say little about them.

### 2.6 Why buyer ratings are not blended into criteria

Retailers give one overall star rating per shoe, not a rating per criterion. Spreading it
over cushioning or grip would make up information we don't have. Instead, the Bayesian
buyer rating (§4) enters the final score as a separate term with a fixed share
(`final.buyer_share`, §6).

### 2.7 Worked example (fictional shoe)

Heel stack 33 mm, forefoot stack 27 mm, foam "supercritical EVA", two expert reviews
rating cushioning 8 and 7.

- heel: `interp(33)` between [30, 5] and [35, 7] → 5 + 3/5·2 = **6.2**
- forefoot: `interp(27)` between [24, 5] and [29, 7] → **6.2**
- foam: matches "supercritical" → class `supercritical_or_gas_infused` → cushioning **7.5**
- `S = 0.45·6.2 + 0.30·6.2 + 0.25·7.5 = 6.525`
- `E = 7.5`, `n = 2`, `w_s = 0.6`, `w_e = 0.4 · 2/3 = 0.267`
- `score = (0.6·6.525 + 0.267·7.5) / 0.867 ≈ ` **6.83**

---

## 3. Terrain scores (0-10, offline)

There are five terrain types: `road_to_trail, groomed_mixed, technical_rocky, muddy_soft,
wet_roots`. Each uses the generic evaluator (§0.4) with the inputs in
`terrain.scores.<terrain>`. **Lug depth is required**: it is the main driver, so a terrain
score is null without it. Terrain scores use specs only. Review aspects are about the
eight criteria, not about terrains.

Lug depth is the main signal. Each terrain has a peaked curve around its ideal lug depth,
in line with the usual rule of thumb:

| Lug depth | Best suited to | Curve shape in the YAML |
|---|---|---|
| < 3 mm | road-to-trail | peak at 2.5 mm, falls steeply after 4 mm |
| 3-4 mm | groomed / mixed | peak at 3.5 mm |
| 4-5 mm | technical / rocky | peak at 4.5 mm, falls slowly |
| ≥ 5 mm | muddy / soft | keeps rising up to 6 mm |
| 4-5 mm | wet roots / rocks | peak at 5 mm, but rubber matters most |

Other inputs and their weights:

| Terrain | lug depth | rubber grip | lug spacing | plate (protection) | heel stack |
|---|---|---|---|---|---|
| road_to_trail | 0.55 | 0.15 | 0.15 (tight best) | – | 0.15 (higher = better) |
| groomed_mixed | 0.50 | 0.25 | 0.10 (medium best) | 0.05 | 0.10 (moderate best) |
| technical_rocky | 0.35 | 0.25 | 0.05 | 0.20 | 0.15 (lower = better) |
| muddy_soft | 0.55 | 0.15 | 0.30 (wide best: sheds mud) | – | – |
| wet_roots | 0.30 | 0.55 (sticky rubber) | 0.05 | – | 0.10 (lower = better) |

---

## 4. Buyer rating: Bayesian average (offline)

**Problem.** A raw average rewards small samples: a 5.0 from 3 reviews would beat a 4.6
from 200 reviews.

**Fix.** Treat every shoe as if it already had `C` "virtual" reviews at the catalogue
average `m`, then add its real reviews:

```
N        = Σ_i n_i                     (review counts over all retailers)
raw      = Σ_i n_i · r_i / N           (null if N = 0)
bayesian = (C · m + Σ_i n_i · r_i) / (C + N)     (null if N = 0)
```

- `C = buyer_rating.prior_strength` (20).
- `m` = review-weighted mean rating over the whole catalogue, if the catalogue has at
  least `buyer_rating.min_reviews_for_catalogue_prior` reviews. Otherwise
  `buyer_rating.fallback_prior_mean` (4.3).
- Ratings are on a 0-5 scale (normalised in phase 2).

**Example** with `m = 4.3`, `C = 20`:
- 5.0 × 3 reviews → (86 + 15) / 23 = **4.39**
- 4.6 × 200 reviews → (86 + 920) / 220 = **4.57**, which now ranks higher.

For the final score, the Bayesian mean is turned into 0-10 with
`interp(bayesian, buyer_rating.score_anchors)`. These anchors spread the useful 4.0-5.0
range, where almost all shoes sit.

Known limitation: if two retailers show the same reviews (shared review platforms), they
are counted twice. We cannot detect this reliably, so we accept it and mention it in the
phase reports.

---

## 5. Runner profile → weights (browser)

Each **term** `k` of the final score gets a weight `W_k ≥ 0`. The terms are the 8 criteria,
2 derived scores (§5.3), the terrain composite (§5.4) and the drop fit (§5.5). Weights
are built in layers, and every layer is a continuous function of the inputs.

### 5.1 Load index

```
t_w   = clamp((weight_kg − low) / (high − low), 0, 1)       profile.runner_weight_kg
w_n   = smoothstep(t_w)
d_n   = clamp(ln(distance_km / low) / ln(high / low), 0, 1)  profile.distance_km
load  = a · w_n + b · d_n                                    profile.load_mix (a + b = 1)
```

Distance uses a log scale, because going from 10 to 20 km changes needs about as much as
going from 50 to 100 km. `load` is between 0 (light runner, short runs) and 1 (heavy
runner, ultra distances).

### 5.2 Base weights

For each criterion `c`, with `[lo, hi] = profile.base_weights.c`:

```
base_c = lo + (hi − lo) · load
```

With more load, cushioning, stability, protection and durability gain weight, and
lightness and responsiveness lose some.

### 5.3 Preference sliders

Each slider gives `s ∈ [−1, +1]`: −1 = fully the left pole, 0 = no preference, +1 =
fully the right pole. A UI slider from 0 to 100 maps to `s = (v − 50) / 50`. With
`g = profile.preference_axes.strength`, for each axis:

```
pref_k += g · max(−s, 0) · left_k  +  g · max(s, 0) · right_k
```

| Axis | Left pole | Right pole |
|---|---|---|
| cushioning_vs_ground_feel | cushioning 1.0 | ground_feel 1.0 |
| stability_vs_agility | stability 1.0 | agility 1.0 |
| dynamic_vs_comfortable | responsiveness 0.7, lightness 0.3 | cushioning 0.6, fit_width 0.4 |

Two poles are not criteria, so we derive them (`profile.derived_scores`):

```
ground_feel = 10 − cushioning
agility     = weighted mean of {lightness: 0.6, ground_feel: 0.4} over known values
```

They exist only as terms of the final score. Their weight is 0 unless a slider points to them.

### 5.4 Terrain

The runner selects one or more terrains. Each selected terrain gets an equal share
(shares sum to 1). If none is selected, all five get 0.2.

- **Terrain composite term**: `x_terrain = Σ share_t · terrain_t / Σ share_t` over
  terrains with a known score, with weight `W_terrain = profile.terrain.composite_weight`.
- **Criterion boosts**: `terrain_c = Σ_t share_t · profile.terrain.criterion_boosts.t.c`.
  For example, technical terrain adds weight to protection, stability and grip.

### 5.5 Foot strike (small and smooth)

With `(target, σ, w) = profile.foot_strike.<strike>`:

```
x_drop_fit = 10 · exp(−½ · ((drop_mm − target) / σ)²)      (null if drop unknown)
W_drop_fit = w
strike_c   = profile.foot_strike.<strike>.criterion_boosts.c
```

Heel strikers get a target drop of 9 mm and extra cushioning weight. Forefoot strikers
get a target of 4 mm. Midfoot strikers get a weak preference around 6 mm. `unknown` has
weight 0, so it is neutral. The bell curve is smooth: a 6 mm drop for a heel striker
scores `10 · exp(−½ · (3/4)²) ≈ 7.5`, not 0. At most this term weighs about 5 % of the
total, because the evidence linking foot strike and drop is weak.

### 5.6 Foot width

`width_fit_width = profile.foot_width_boosts.<foot_width>` is added to the `fit_width`
weight. Runners with narrow or wide feet care more about fit.

### 5.7 Total weights

```
W_c           = base_c + pref_c + terrain_c + strike_c + width_c   (for the 8 criteria)
W_ground_feel = pref_ground_feel
W_agility     = pref_agility
W_terrain     = profile.terrain.composite_weight
W_drop_fit    = profile.foot_strike.<strike>.weight
```

Each component is kept separately so the explanation can say *why* a weight is high.

### 5.8 Worked example

Profile: 80 kg, 42 km, technical terrain only, heel striker, cushioning slider at
`s = −0.5` (half towards cushioning), other sliders neutral, standard feet.

- `t_w = 25/45 = 0.556`, `w_n = 0.583`; `d_n = ln(8.4)/ln(20) = 0.710`; `load = 0.647`.

| Term | base | + slider | + terrain | + strike | W | share |
|---|---|---|---|---|---|---|
| cushioning | 1.647 | 0.75 | – | 0.3 | 2.697 | 18.8 % |
| terrain composite | – | – | – | – | 2.000 | 14.0 % |
| protection | 1.124 | – | 0.8 | – | 1.924 | 13.4 % |
| stability | 1.253 | – | 0.5 | – | 1.753 | 12.2 % |
| grip | 1.200 | – | 0.3 | – | 1.500 | 10.5 % |
| durability | 1.024 | – | – | – | 1.024 | 7.1 % |
| fit_width | 0.994 | – | – | – | 0.994 | 6.9 % |
| lightness | 0.918 | – | – | – | 0.918 | 6.4 % |
| responsiveness | 0.912 | – | – | – | 0.912 | 6.4 % |
| drop fit | – | – | – | – | 0.600 | 4.2 % |
| **total** | | | | | **14.322** | 100 % |

---

## 6. Final score and explanation (browser)

### 6.1 Formula

Let `x_k` be the 0-10 score of term `k`, `P` the terms with `W_k > 0`, `A ⊆ P` those
with a known `x_k`, and `m = final.missing_term_value` (5, neutral). With
`x̃_k = x_k` if known, else `m`:

```
fit       = Σ_{k∈P} W_k · x̃_k / Σ_{k∈P} W_k                      (0-10; null if A is empty)
coverage  = Σ_{k∈A} W_k / Σ_{k∈P} W_k
B         = interp(buyer_rating.bayesian_mean_0_5, buyer_rating.score_anchors)   (null if no reviews)
λ         = final.buyer_share if B is known, else 0
score     = 10 · ((1 − λ) · fit + λ · B)                          (0-100)
```

### 6.2 Normalisation to 0-100

The score is **absolute**: 100 would mean 10/10 on every weighted term. We do **not**
rescale so that the best shoe gets 100, because then a weak catalogue would look
excellent and scores would change whenever a shoe is added. The UI shows the score
rounded to an integer next to the rank.

### 6.3 Not enough data

If `coverage < final.min_ranking_coverage`, the shoe is not ranked. It appears in a
separate "Not enough data to rank" list with what is missing. This stops a shoe with
almost no data from winning on its few known strengths.

### 6.4 Ordering and ties

Sort by `score` (descending). On ties (same rounded score), the higher confidence level
comes first, then higher coverage, then lower price.

### 6.5 Explanation

**Breakdown (all terms).** For each `k ∈ P`:

```
share_k  = W_k / Σ_{k∈P} W_k
points_k = 10 · (1 − λ) · share_k · x̃_k          and   points_buyer = 10 · λ · B
```

Unknown terms are shown as "unknown, counted as 5". Why neutral rather than dropped: a
dropped term re-normalises the others, so a shoe whose weak point is unknown ranks as if
it had none. Why not 0: a missing measurement is not evidence of a weakness.

The points add up exactly to the score, so the UI can show a stacked bar and a table
(term, weight %, score /10, points).

**Advantage over the alternatives.** A strength only matters if other shoes don't have it:

```
μ_k = mean of x_k over the shoes that passed the hard filters (known values only)
      or 5 if fewer than explanation.min_candidates_for_mean shoes have a value
a_k = share_k · (x_k − μ_k)
```

Reasons and drawbacks only use terms whose value is known (`k ∈ A`).

- **Top reasons**: terms with `a_k > 0` and `x_k ≥ explanation.reason_min_score`, sorted
  by `a_k`, at most `explanation.max_reasons` (3).
- **Top drawbacks**: terms with `a_k < 0` and `x_k ≤ explanation.drawback_max_score`,
  most negative first, at most `explanation.max_drawbacks` (2).
- **Missing-data drawbacks**: any term not in `A` whose weight share would be ≥
  `explanation.missing_data_min_weight_share` → "No reliable data on durability".

**Sentence template** (filled in the browser):

> **Grip — 8.4/10 (excellent).** Weighted 10 % for you because you selected technical
> terrain. *"Outstanding bite on wet rock"* — Source, 2025 (link).

- The label word comes from `explanation.score_labels`: the first band whose threshold
  is ≤ the score.
- "Because..." names the largest weight component from §5.7: load, slider, terrain,
  foot strike or foot width.
- The quote is the `evidence_excerpt` of the expert aspect with the highest score (for a
  reason) or the lowest score (for a drawback), when one exists.
- The buyer term reads: "Buyers rate it 4.6/5 over 212 reviews (adjusted 4.57)."

---

## 7. "I like this model": similarity (browser)

The runner picks a reference shoe `r`. Every shoe `s ≠ r` that passes the **same hard
filters** is compared with it.

**Feature vector** (`similarity.feature_weights`):

- the 8 criterion scores and 5 terrain scores, divided by 10;
- `drop_mm`, `stack_heel_mm` and `lug_depth_mm`, robust min-max scaled over the whole
  catalogue: `clamp((v − P5) / (P95 − P5), 0, 1)` with the percentiles from
  `similarity.numeric_normalisation`. Percentiles ignore extreme shoes;
- `waterproof` as 1 / 0.

Weight is not a separate feature: it is already covered by `lightness`, which handles the
men's/women's reference sizes.

**Distance** over the features `F` known for both shoes:

```
shared   = Σ_{f∈F} w_f / Σ_{all f} w_f          (if < similarity.min_shared_weight_share → "not comparable")
d        = sqrt( Σ_{f∈F} w_f · (r_f − s_f)² / Σ_{f∈F} w_f )      ∈ [0, 1]
similarity = 100 · (1 − d)
```

Show the top `similarity.max_results` results. Other versions of the same brand + model
are labelled "other version". Each result gets an explanation: the 3 features with the
smallest weighted difference ("very close on drop and grip") and the 2 with the largest,
with direction ("lighter", "more cushioned").

---

## 8. Confidence (offline)

```
spec_completeness   = Σ_f c_f · known_f / Σ_f c_f        c = confidence.spec_completeness_weights
expert_review_count = number of expert reviews
buyer_review_count  = Σ retail[].review_count
price_age_days      = build date − most recent retail[].price_date
```

`known_f` is 1 if `specs.f.value` is not null. For `weight_g`, it is 1 if either
`weight_g` or `weight_women_g` is known. Platform widths are left out of completeness
because almost no manufacturer publishes them; counting them would lower every shoe
equally.

**Level** (`confidence.levels`). **high** if all of the following are true:
completeness ≥ 0.8, price age ≤ 14 days, **and all** evidence conditions
(≥ 2 expert reviews and ≥ 20 buyer reviews). Otherwise **medium** if completeness ≥ 0.6,
price age ≤ 30 days, **and any** evidence condition (≥ 1 expert review or ≥ 10 buyer
reviews). Otherwise **low**. A shoe with no price date is low.

`confidence.reasons` lists, in plain English, the conditions that stopped the next level
up, e.g. "Only 1 expert review (high needs 2)". The browser can recompute the price age
on the day of viewing from `price_date` and show "prices checked on <date>".

---

## 9. Index of constants

| YAML path | Used in |
|---|---|
| `version` | header, `shoes.json` → `scoring_config_version` |
| `common.min_spec_input_coverage`, `common.output_decimals` | §0.3, §0.4, §2.3 |
| `criteria.<c>.required_inputs` | §0.4, §2.3 |
| `lookups.foam_classes`, `lookups.rubber_classes`, `lookups.plate_classes` | §2.1, §3 |
| `expert_reviews.full_weight_review_count`, `expert_reviews.prior_score_without_specs` | §2.5 |
| `criteria.<c>.blend`, `criteria.<c>.spec_inputs` | §2.2-2.5 |
| `terrain.required_inputs`, `terrain.min_input_coverage`, `terrain.scores` | §3 |
| `buyer_rating.*` | §4, §6.1 |
| `profile.runner_weight_kg`, `profile.distance_km`, `profile.load_mix` | §5.1 |
| `profile.base_weights` | §5.2 |
| `profile.derived_scores`, `profile.preference_axes` | §5.3 |
| `profile.terrain.*` | §5.4 |
| `profile.foot_strike` | §5.5 |
| `profile.foot_width_boosts` | §5.6 |
| `final.buyer_share`, `final.min_ranking_coverage`, `final.missing_term_value` | §6.1, §6.3 |
| `explanation.*` | §6.5 |
| `similarity.*` | §7 |
| `confidence.*` | §8 |
