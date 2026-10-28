# Phase 4 report — specialist reviews

Date: 2026-10-28. Sources: RunRepeat, Believe in the Run, Esprit Trail (French).
Doctors of Running was dropped (robots.txt bans `anthropic-ai` and `Claude-Web`).
Access checks: `docs/sources.md`. Output: `data/interim/expert_reviews.json`.

## Coverage

| Sources with a review | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Models (of 220) | 139 | 49 | 30 | 2 | 0 |

| Source | Models | Reviews | exact | variant (GTX...) | ratings given |
|---|---|---|---|---|---|
| RunRepeat | 45 | 47 | 45 | 2 | 47 (score /100 + sub-scores) |
| Believe in the Run | 63 | 64 | 58 | 4 (+2 manual) | 38 (grades A-F) |
| Esprit Trail | 7 | 7 | 7 | 0 | 0 (no score published) |

All 118 reviews have a date; nearly all have a conclusion excerpt (<= 30 words, our selection:
the first whole sentences of the verdict). Full conclusions and pros/cons (about 45 500
words) are only in `data/raw/reviews/conclusions.json` (gitignored), for phase 5.

## Matching

Strict rule: model words then the exact version in the URL slug, confirmed by the title,
with no "modifier" word around the name (pro, max, speed, st, S/Lab...). Two bugs were
found on the real data and fixed before this report: a model without version first took
reviews of longer names ("Prodigio" got Prodigio Pro and Max, "Agravic" got 9 models),
and a later over-strict version rejected French slugs with free text after the name.

## Ambiguous matches (8, in `data/interim/reviews_needs_review.csv`, decided 2026-10-28)

| Model | Review | Why |
|---|---|---|
| adidas-agravic-4 | BITR "This Cheap Adidas Terrex Shoe Is Your Gateway To Trail Running" | title does not name the model |
| nnormal-kjerag-2 | BITR "Nnormal's Kjerag 02 keeps Kilian-level agility, but fixes the tough ride" | title wording ("Nnormal's") |
| new-balance-rebel | BITR FuelCell Rebel review | our model has no version; the source reviews numbered versions |
| puma-velocity-nitro | BITR Velocity Nitro review | same |
| brooks-range | Tracksmith Eliot Range | another brand |
| salomon-genesis | Saucony Pro Grid Shadow Genesis | another brand |
| scott-pursuit (x2) | Topo Athletic Pursuit, New Balance Zante Pursuit | other brands |

Decisions applied: accepted adidas Agravic 4 and NNormal Kjerag 2 (attached as
`manual`); rejected the four other-brand matches and the two version-unknown cases.
Result: 118 reviews on 81 models.

## Lab-measured values (RunRepeat only): 47 reviews, 45 models

Every RunRepeat review has heel and forefoot stack, lug depth, weight, midsole widths
(forefoot/heel) and outsole thickness; most also drop (46), outsole wear (45), toebox
width (42), energy return, shock absorption and stiffness (37), softness (32),
torsional rigidity (24). Each value keeps the page line ("Heel stack | 31.7 mm |
33.0 mm" = this shoe | average) and is labelled "RunRepeat lab measurement (not
manufacturer data)".

Models with lab stack and lug depth: adidas Agravic 4 / SL / Speed / Speed Ultra 2 / TT,
Altra Experience Wild, Lone Peak 9, Mont Blanc Carbon, Olympus 275 / 5 / 6, Superior 7,
Timp 5 / 6, Asics Gel-Trabuco 13 / 14, Gel-Venture 10, Trabuco Max 4, Brooks Cascadia
19 / 20 / Elite, Catamount 4, Inov-8 Trailtalon, La Sportiva Mutant, Prodigio / 2 / Max /
Pro, Merrell Agility Peak 6, Morphlite, Nova 4, Trail Glove 7 / 8, New Balance DynaSoft
Nitrel 6, Tektrel, NNormal Kjerag, Salomon Genesis, Ultra Glide 4, XA Pro 3D 9, Saucony
Peregrine 13 / 15 / 16, Xodus Ultra 4, Scarpa Spin Planet.

## Known problems

- Coverage is limited: 140 of 220 models have no review (smaller brands, old versions,
  Joma, Vibram FiveFingers...).
- The catalogue has both `asics-gel-trabuco-14` and `asics-trabuco-14` (a phase 2
  duplicate); the same RunRepeat review is attached to both.
- Believe in the Run's Peregrine 16 page contains a heading about the Peregrine 15
  (the source's own error); the review itself is about the 16.
- RunRepeat sells licences for its lab data, and Believe in the Run forbids reproducing
  any part: settle before publishing.

## What to verify

Fill `decision` (accept / reject) in `reviews_needs_review.csv`, re-run
`python -m pipeline.reviews --source all`, and open 3-4 attached reviews.
