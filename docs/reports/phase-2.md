# Phase 2 report — canonical models

Date: 2026-10-28 (re-run with Tradeinn + Glisshop). Input: `data/interim/retailer_listings.json`.

## Counts

- Listings in: **1 228** (Tradeinn 924, Glisshop 304). Dropped: 30 kids' shoes. Used: 1 198.
- Canonical models out: **220** (exact key match: 220; fuzzy merges applied: **0**).
- Models on 1 / 2 / 3 retailers: **186 / 34 / 0**.
- Old versions still on sale next to a newer one: 24, of which 19 are cheaper than the newest.
- `needs_review.csv`: 28 rows (19 possible duplicates, 8 "version unknown", 1 product
  code in a title). None is merged by default.
- Buyer ratings: 126 models have real reviews; prior 4.956; Bayesian means 4.733 to 4.994.

## Brands (models)

La Sportiva 19, Altra 16, Asics 16, adidas 15, Merrell 15, Joma 14, Mizuno 13,
New Balance 10, Salomon 9, Vibram FiveFingers 9, Craft 8, Puma 8, Saucony 8, Scott 8,
Brooks 7, Scarpa 7, Under Armour 7, NNormal 6, Rossignol 5, Dynafit 4, Inov-8 4, Lowa 4,
Millet 3, Tecnica 3, VEJA 2.

## The 15 most uncertain matches (none merged; merge threshold 92)

| Score | Keys |
|---|---|
| 90.3 | under armour\|charged bandit tr\|3 vs under armour\|charged bandit\|3 |
| 88.0 | scott\|kinabalu tr\| vs scott\|kinabalu ultra\| |
| 87.5 | new balance\|tektrel s\| vs new balance\|tektrel\| |
| 87.0 | mizuno\|wave rider tt\|3 vs mizuno\|wave rider\|3 |
| 87.0 | scott\|kinabalu mtn\| vs scott\|kinabalu tr\| |
| 85.7 | scott\|supertrac rc\|3 vs scott\|supertrac\|3 |
| 85.7 | joma\|sierra barefoot\| vs joma\|sima barefoot\| |
| 85.7 | puma\|flare pro tr\| vs puma\|flare pro\| |
| 83.9 | scarpa\|golden gate 2 atr\| vs scarpa\|golden gate lt\| |
| 82.4 | adidas\|agravic sl\| vs adidas\|agravic\| |
| 82.4 | adidas\|agravic tt\| vs adidas\|agravic\| |
| 81.8 | adidas\|agravic lite\| vs adidas\|agravic sl\| |
| 81.8 | adidas\|agravic lite\| vs adidas\|agravic tt\| |
| 81.5 | adidas\|tracefinder plus\| vs adidas\|tracefinder\| |
| 81.2 | adidas\|agravic speed ultra\|2 vs adidas\|agravic speed\|2 |

## Models found at both retailers (34)

adidas Agravic Lite / SL / Speed / TT, Soulstride Flow; Asics Fuji Lite 6 and 7,
Gel-Trabuco 13, Trabuco Max 4 and 5; La Sportiva Akasha 2, Bushido 3, Cyklon Cross,
Jackal 2, Levante, Mutant, Prodigio, Prodigio 2, Prodigio Max, Prodigio Pro, Tempesta;
Merrell Agility Remix; Mizuno Neo Accera, Neo Daichi 10, Wave Daichi 9, Wave Mujin 11,
Wave Rider TT 3; Salomon Alphaglide, Ultra Flow 2, XA Pro 3D 9; Saucony Guide TR,
Peregrine 16, Ride TR 3, Xodus Ultra 4.

## What changed for Glisshop

- The key comes from the retailer's model name without colour (`model_name`), not from
  the marketing title ("Prodigio Yellow Black" -> "Prodigio").
- Short gender markers in names ("W", "Ms", "Wmn", "Woman", "W's") are removed. Before
  this fix, two wrong fuzzy merges happened (Prodigio 2 Woman + Prodigio Woman, Bushido
  II Woman + Bushido III Woman): the marker hid the version number.
- Brands that the retailer names but `brands.yaml` did not know are trusted (with a warning).
- Gravel shoes are also recognised from retailer facts ("Type: Chaussures Gravel Running").

## Known problems

- A few Glisshop model names still contain an edition word ("Xa Pro 3D V9 Gore-Tex
  Equipe"), which then becomes a separate model without version.
- Joma TR-6 / TR-8 / TR-9 are treated as versions of one "TR" line.
- 8 lines have a version-less title next to numbered ones ("Salomon Genesis" + "Genesis 2").
- Ratings remain weakly informative (most real ratings are 4.7-5.0).

## What to verify

- Fill `decision` in `data/interim/needs_review.csv`, then `python -m pipeline.normalize.apply_review`.
- Spot-check 3-4 of the 34 cross-retailer models (same shoe at both shops?).
