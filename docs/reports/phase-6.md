# Phase 6 report: build of the final database

Status: **checkpoint**. The build runs and validates; the scores need the project
owner's review before phase 7. Generated details: `data/processed/build_report.md`.

## What was produced

* `pipeline/build/` (`python -m pipeline.build`): spec resolution, the scoring of
  `docs/scoring-spec.md` (§2 criteria, §3 terrain, §8 confidence; the §4 Bayesian buyer
  rating comes from phase 2), schema validation, report.
* `data/processed/shoes.json` (217 shoes, 1,194 offers, 118 expert reviews), validated
  against `schema/catalog.schema.json` and each shoe against `schema/shoe.schema.json`.
* `data/processed/scoring_config.json` (scoring.yaml for the browser) and `meta.json`
  (build date, versions, counts, price dates; `schema/meta.schema.json`).
* `data/processed/build_report.md` and `docs/img/criteria_distribution.png`.
* Data model: `Specs.sources` (tier of each known value), `provenance` on every criterion
  and terrain score, `Shoe.category` and `newer_version_id`, `BuildMeta`.
* `tests/test_build.py` (19 tests): the spec's worked example (6.83), re-normalisation,
  null when nothing is known, monotonicity (lug depth → grip, heel stack → cushioning and
  stability, forefoot stack → protection, weight → lightness, width options → fit, lug
  depth → muddy terrain), source priority, confidence levels, and an end-to-end build of
  the committed interim data against the schemas.
* CLAUDE.md: decision 18, the build command and a one-line rebuild of phases 1-6.

## Choices where the brief and the spec differed (the spec was followed)

1. **Buyer rating is not a criterion input.** The brief lists it among possible
   provenance inputs; spec §2.6 keeps it out of the criteria (it is a separate term of
   the final score, §6). No criterion `provenance` contains it; a test checks this.
2. **Expert sub-score = plain mean over reviews** (spec §2.4), not phase 5's
   source-weighted mean (RunRepeat 1.2). The difference is small; to use the weights,
   §2.4 must change first.
3. **Output file names**: `shoes.json` (brief) instead of the spec's `catalog.json`;
   the spec and READMEs were updated.
4. **Lab fallback** covers the stacks and the lug depth, as the brief says, and since
   scoring 0.2.0 the platform widths (see below). RunRepeat's weight and drop are unused.
5. **3 models dropped** (`asics-gel-nimbus-tr-28`, `joma-sierra-barefoot`,
   `joma-tundra-barefoot`): no retailer shows a gender, and the schema needs one.

## Highlights

| | |
|---|---|
| Shoes with no known spec at all | 42 (spec completeness 0%) |
| Criteria scored (of 217) | cushioning 82, protection 97, grip 127, stability 78, responsiveness 69, lightness 126, durability 113, fit width 74 |
| Terrain scored | 85 (lug depth known); wet roots 39 (needs rubber too) |
| Confidence | high 2 (adidas Agravic 4, Salomon XA Pro 3D 9), medium 41, low 174 |
| Main reason for low | spec completeness below 60% (203 shoes), no expert review (113) |
| Spec sources | stacks: 16 manufacturer + 41 lab; lug depth: 17 + 42 lab + 26 retailer; rubber: 26 + 128 retailer |

## Suspicious scores (to review)

1. **One input can make a whole spec sub-score.** `min_spec_input_coverage` is 0.4, so
   for protection the plate alone (weight 0.55) is enough: a retailer's "Plaque de
   protection: Oui" gives protection **9.0** to the barefoot Vibram FiveFingers V-Trail
   2.0. 27 rock plates come from retailers only.
2. **One review can make a whole score.** When there is no spec sub-score, the expert
   weight is re-normalised to 100% even for one review (spec §2.5 + §0.2). Example:
   Brooks Cascadia 20 responsiveness **9.1** from one review. This happens for 34
   responsiveness and 44 fit-width scores. The spec says one review "only moves the
   score a little"; that holds only when a spec sub-score exists.
3. **Stability = low stack.** Without platform widths, max-cushion shoes look unstable:
   Cascadia 20 5.3, Prodigio Max 5.1, Trabuco Max 4 4.7, while reviewers call them
   stable. Minimal shoes look stable from specs while reviews disagree (Altra Superior 7:
   spec 8.9 vs reviews 3.0).
4. **Foam and rubber lookups match little.** 104 foam names and 82 rubber names match no
   class (FloatPro, EExpure, Lightstrike, PWRTRAC, Frixion, ASICSGRIP...), some of them
   machine-translated on the retailer pages ("Ève" for EVA, "Autre Moi" for Altra EGO).
   So responsiveness has a spec sub-score for only 13 shoes.
5. **Responsiveness leans high** (mean 6.8, 23 shoes at 8-9), mostly from reviews only;
   phase 5 measured it as the weakest criterion.
6. **Phase 5 errors show through**: Merrell Trail Glove 7/8 (barefoot) get expert
   cushioning ~6.2 against a spec of ~1.2.
7. **Durability is squeezed** between 5 and 9.4 (the class values span 5-8.5): it cannot
   separate shoes much.
8. **Lightness from women's weights** is correct by construction (own anchors) but
   depends on a retailer value: Trabuco Max 4 gets 7.1 from a 225 g women's weight.
9. **Sanity table**: La Sportiva Bushido 3 and Inov-8 Mudtalon Speed 2 have almost no
   data; Altra Lone Peak 9 cushioning 3.6 looks low.

The list above describes the first build (scoring 0.1.0).

## Changes applied: scoring 0.2.0 (the project owner chose all four)

1. `common.min_spec_input_coverage` 0.4 → **0.6**: one input weighing less than 0.6 no
   longer makes a spec sub-score (protection needs plate + forefoot stack, grip rubber +
   lug depth, cushioning two of its three inputs).
2. **Expert-only scores shrink towards a neutral 5**: `score = t·E + (1−t)·5`,
   `t = min(1, n/3)`; recorded as `neutral_prior` in the provenance (spec §2.5).
3. **Platform widths from RunRepeat** ("midsole width", heel and forefoot): 45 shoes.
4. **Foam rules** only for compounds whose type a collected review states: EExpure,
   Enerzy NXT, DNA Flash (+ "adn flash"), and "ève" (machine translation of EVA). FloatPro,
   EGO, Lightstrike, Frixion, PWRTRAC, ASICSGRIP... stay unmatched: no collected source
   states what they are, and an unknown compound must not be assumed average.

### Before / after (all 217 shoes)

| Criterion | Scored before | after | With spec sub-score before | after | Mean before | after |
|---|---|---|---|---|---|---|
| cushioning | 82 | 82 | 57 | 57 | 5.60 | 5.45 |
| protection | 97 | **66** | 78 | **15** | 6.83 | 5.68 |
| grip | 127 | **76** | 118 | **39** | 7.33 | 6.53 |
| stability | 78 | 78 | 57 | 57 | 5.81 | 5.93 |
| responsiveness | 69 | 73 | 13 | 21 | 6.82 | 5.97 |
| lightness | 126 | 126 | 99 | 99 | 6.07 | 6.00 |
| durability | 113 | 105 | 83 | 72 | 7.13 | 6.76 |
| fit_width | 74 | 74 | 4 | 4 | 5.06 | 5.03 |

Scores resting 100% on a single review: 198 → **0**. Confidence levels are unchanged
(platform widths are not part of completeness, spec §8).

### Sanity table, before → after (unchanged cells show one value)

| Shoe | cush | prot | grip | stab | resp | light | dura | fit |
|---|---|---|---|---|---|---|---|---|
| brooks-cascadia-20 | 7.4 | 8.6 | 7.0 | 5.3 → **6.2** | 9.1 → **6.4** | 4.6 | 6.6 | 6.1 → **5.7** |
| saucony-peregrine-15 | 5.4 | 7.6 | 8.5 → **6.0** | 6.7 → **7.0** | 7.6 → **6.7** | 6.3 | 7.8 → **5.9** | 3.8 → **4.2** |
| la-sportiva-bushido-3 | - | 9.0 → **-** | 7.5 → **-** | - | - | 5.0 | - | - |
| la-sportiva-prodigio-max | 6.7 | 7.5 → **6.3** | 8.0 → **5.5** | 5.1 → **5.8** | 8.0 → **7.0** | 5.2 | 8.3 → **7.2** | 4.4 → **4.6** |
| merrell-mtl-adapt-matryx | 7.9 → **6.0** | 8.9 → **6.3** | 8.5 → **5.7** | 5.9 → **5.3** | 6.4 → **5.5** | 5.2 → **5.1** | 7.1 | 6.4 → **5.5** |
| asics-trabuco-max-4 | 8.3 | 9.5 → **-** | 5.4 → **5.1** | 4.7 → **5.8** | - | 7.1 | - | 5.7 → **5.2** |
| altra-lone-peak-9 | 3.6 | 7.1 | 7.1 → **-** | 7.5 → **6.9** | 5.8 → **5.3** | 4.8 | 7.6 → **5.8** | 8.0 → **6.0** |
| nnormal-kjerag | 3.2 → **4.1** | 3.0 → **-** | 6.8 | 7.9 → **7.2** | 9.2 → **8.4** | 9.6 | 6.4 → **6.2** | - |
| inov-8-mudtalon-speed-2 | - | - | - | - | - | - | - | - |
| vibram-fivefingers-v-tr-2 | - | 9.0 → **-** | 9.0 → **-** | - | - | - | 6.5 | - |
| altra-superior-7 | 2.7 | 6.4 | 6.8 → **5.9** | 6.9 → **6.3** | 5.6 → **5.2** | 8.1 → **6.0** | 7.2 → **5.8** | 4.1 → **4.7** |
| merrell-trail-glove-8 | 2.1 | 3.0 → **5.8** | 6.4 | 9.0 → **7.4** | - | 9.9 | 7.5 | 8.3 → **6.1** |

### What got better, what got worse

* **Better.** The false highs are gone: FiveFingers protection 9.0 → null, Cascadia
  responsiveness 9.1 → 6.4. Max-cushion shoes are no longer "unstable" (Cascadia 5.3 →
  6.2, Trabuco Max 4.7 → 5.8). No score rests on a single review any more.
* **Worse: coverage.** Grip is scored for 76 shoes instead of 127, protection for 66
  instead of 97: a lug depth or a rubber alone no longer counts. Most of those had only
  a retailer value.
* **Worse: everything drifts towards 5.** Shoes with one review and few specs are pulled
  to the middle: Merrell MTL Adapt Matryx, a max-cushion shoe, has cushioning 7.9 → 6.0
  and protection 8.9 → 6.3. Peregrine 15 grip 8.5 → 6.0 because its rubber (PWRTRAC)
  matches no class, so its spec grip dropped below the new minimum.
* **New oddity.** Merrell Trail Glove 8 (barefoot) protection 3.0 → 5.8: its 15 mm
  forefoot stack (clear evidence of low protection) is no longer enough alone, and the
  one review is shrunk towards 5.

## Scoring 0.2.1 (owner's decision: relax to 0.45)

`common.min_spec_input_coverage` 0.6 → **0.45**, and protection **requires** the forefoot
stack (`criteria.protection.required_inputs`), so a stack, a lug depth or a rubber alone
counts again but a plate alone never scores protection. The damping, platform widths and
foam rules of 0.2.0 are kept.

| Criterion | Scored 0.1.0 / 0.2.0 / **0.2.1** | With spec sub-score | Mean |
|---|---|---|---|
| cushioning | 82 / 82 / **82** | 57 / 57 / **57** | 5.60 / 5.45 / **5.45** |
| protection | 97 / 66 / **79** | 78 / 15 / **57** | 6.83 / 5.68 / **6.17** |
| grip | 127 / 76 / **127** | 118 / 39 / **118** | 7.33 / 6.53 / **7.24** |
| stability | 78 / 78 / **78** | 57 / 57 / **57** | 5.81 / 5.93 / **5.93** |
| responsiveness | 69 / 73 / **73** | 13 / 21 / **21** | 6.82 / 5.97 / **5.97** |
| lightness | 126 / 126 / **126** | 99 / 99 / **99** | 6.07 / 6.00 / **6.00** |
| durability | 113 / 105 / **105** | 83 / 72 / **72** | 7.13 / 6.76 / **6.76** |
| fit_width | 74 / 74 / **74** | 4 / 4 / **4** | 5.06 / 5.03 / **5.03** |

| Shoe | cush | prot | grip | stab | resp | light | dura | fit |
|---|---|---|---|---|---|---|---|---|
| brooks-cascadia-20 | 7.4 | 8.6 | 7.0 | 5.3 → 6.2 → **6.2** | 9.1 → 6.4 → **6.4** | 4.6 | 6.6 | 6.1 → 5.7 → **5.7** |
| saucony-peregrine-15 | 5.4 | 7.6 | 8.5 → 6.0 → **8.5** | 6.7 → 7.0 → **7.0** | 7.6 → 6.7 → **6.7** | 6.3 | 7.8 → 5.9 → **5.9** | 3.8 → 4.2 → **4.2** |
| la-sportiva-bushido-3 | - | 9.0 → - → **-** | 7.5 → - → **7.5** | - | - | 5.0 | - | - |
| la-sportiva-prodigio-max | 6.7 | 7.5 → 6.3 → **7.5** | 8.0 → 5.5 → **8.0** | 5.1 → 5.8 → **5.8** | 8.0 → 7.0 → **7.0** | 5.2 | 8.3 → 7.2 → **7.2** | 4.4 → 4.6 → **4.6** |
| merrell-mtl-adapt-matryx | 7.9 → 6.0 → **6.0** | 8.9 → 6.3 → **6.3** | 8.5 → 5.7 → **8.5** | 5.9 → 5.3 → **5.3** | 6.4 → 5.5 → **5.5** | 5.2 → 5.1 → **5.1** | 7.1 | 6.4 → 5.5 → **5.5** |
| asics-trabuco-max-4 | 8.3 | 9.5 → - → **9.5** | 5.4 → 5.1 → **5.4** | 4.7 → 5.8 → **5.8** | - | 7.1 | - | 5.7 → 5.2 → **5.2** |
| altra-lone-peak-9 | 3.6 | 7.1 | 7.1 → - → **7.1** | 7.5 → 6.9 → **6.9** | 5.8 → 5.3 → **5.3** | 4.8 | 7.6 → 5.8 → **5.8** | 8.0 → 6.0 → **6.0** |
| nnormal-kjerag | 3.2 → 4.1 → **4.1** | 3.0 → - → **3.0** | 6.8 | 7.9 → 7.2 → **7.2** | 9.2 → 8.4 → **8.4** | 9.6 | 6.4 → 6.2 → **6.2** | - |
| inov-8-mudtalon-speed-2 | - | - | - | - | - | - | - | - |
| vibram-fivefingers-v-tr-2 | - | 9.0 → - → **-** | 9.0 → - → **9.0** | - | - | - | 6.5 | - |
| altra-superior-7 | 2.7 | 6.4 | 6.8 → 5.9 → **6.8** | 6.9 → 6.3 → **6.3** | 5.6 → 5.2 → **5.2** | 8.1 → 6.0 → **6.0** | 7.2 → 5.8 → **5.8** | 4.1 → 4.7 → **4.7** |
| merrell-trail-glove-8 | 2.1 | 3.0 → 5.8 → **3.0** | 6.4 | 9.0 → 7.4 → **7.4** | - | 9.9 | 7.5 | 8.3 → 6.1 → **6.1** |

Scores resting 100% on one review: 0. Protection scores from a plate alone: 0.

### Still open

* **Grip from rubber alone**: the FiveFingers V-Trail 2 gets grip 9.0 from "Vibram
  Megagrip" with no lug depth known. Megagrip is sticky, so 9 is defensible on rock, but
  a shoe without real lugs will not grip in mud (its terrain scores stay null).
* **Durability** keeps the 0.2.0 loss (113 → 105): the foam alone (0.40) is below 0.45.
* **Shoes with one review drift towards 5** (damping, kept): MTL Adapt Matryx
  cushioning 6.0 although it is a max-cushion shoe; its stacks are unknown.
* **Unmatched compounds** (FloatPro, Frixion, PWRTRAC, ASICSGRIP, Lightstrike, EGO):
  a sourced mapping from the owner would win back grip, durability and responsiveness.
