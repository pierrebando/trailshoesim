# Coverage pass (2026-10-29): why data was missing, and what was fixed

Goal: find why data is missing, fix what can legitimately be fixed (causes a, b, c), and
list the rest. Tool: `python -m pipeline.diagnose` writes `docs/coverage-diagnosis.md`
(current state). Causes: (a) crawler missed it, (b) JavaScript-rendered, (c) matching
failed, (d) not published by the source, (e) access forbidden or blocked.

## Diagnosis before the fixes

| Source | (a) | (b) | (c) | (d) | (e) |
|---|---|---|---|---|---|
| Tradeinn | 500 |  |  | 438 |  |
| Glisshop |  |  |  | 149 |  |
| Le Pape |  |  |  |  | 1 |
| i-Run |  |  |  |  | 1 |
| Manufacturer pages | 5 | 10 |  | 16 | 140 |
| Spec fields (all tiers) | 50 | 87 |  | 363 | 902 |
| runrepeat |  |  |  | 175 |  |
| believe_in_the_run |  |  | 4 | 153 |  |
| esprit_trail |  |  |  | 213 |  |
| doctors_of_running |  |  |  |  | 220 |
| Catalogue (phase 2) |  |  | 32 |  |  |

The (a) gaps were all at Tradeinn: 17 shoe brands of the trail menu never visited (Hoka,
Nike, On, Topo, Scott, Scarpa, Inov-8...), 5 category pages cut at 96 products, 477 trail
products linked from product pages but never collected. The (b) gaps were the terms of
Under Armour and Millet, unreadable without JavaScript. The (c) gaps were 4 shoes split in
two by the title parser and 28 possible duplicates never decided.

## Fixes

* **(a) Tradeinn crawl**: brand links are read from the brand menu of every category page
  (single-quoted links were missed), and product pages' links to other trail shoes are
  followed. Tradeinn listings 924 -> 2,046; 86 brands seen instead of 16.
* **(a) RunRepeat discovery**: the road and hiking catalogues are read too (the trail
  catalogue missed road-to-trail and hiking-style shoes). Matching stays strict.
* **(b) Terms rendered by JavaScript**, read with a headless browser: Under Armour and
  Millet forbid copying or reproducing their content, On forbids automated access:
  all three stay blocked, now with a checked reason. Tecnica's robots.txt now bans AI
  crawlers.
* **(c) Catalogue**: "Wos" (Mizuno, women) and "Misty" (a colour) in `titles.yaml`,
  "ATR" stripped for Scarpa in `brands.yaml`: 3 duplicates merged. Undecided merges stay
  in `needs_review.csv` (102 rows after the larger crawl).
* **New manufacturer sites**: 14 new brands with at least 4 models were checked (robots.txt,
  bot protection, terms). Topo Athletic, Xero and Mammut are allowed and configured, with a
  stricter match (only gender/locale words may follow the name in the URL, and the page
  title must name the exact version: Topo's `/mens-pursuit` page is the "Pursuit 3").
  Hoka, Vivobarefoot, Helly Hansen (403), Icebug (429), HI-TEC, Mount to Coast, On
  (terms) stay blocked; +8000, Oriocx, Boreal were unreachable.
* **Manual entries** (B4): `data/manual/missing_specs.csv` lists 175 (model, field) cells
  the student can fill from product pages read in a normal browser; filled rows become the
  "manual (student entry)" tier, right after the manufacturer.

## Diagnosis after the fixes

| Source | (a) | (b) | (c) | (d) | (e) |
|---|---|---|---|---|---|
| Tradeinn | 16 |  |  | 1165 |  |
| Glisshop |  |  |  | 149 |  |
| Le Pape |  |  |  |  | 1 |
| i-Run |  |  |  |  | 1 |
| Manufacturer pages | 62 |  |  | 40 | 229 |
| Spec fields (all tiers) | 451 |  |  | 580 | 1441 |
| runrepeat |  |  | 8 | 323 |  |
| believe_in_the_run |  |  | 16 | 282 |  |
| esprit_trail |  |  | 1 | 391 |  |
| doctors_of_running |  |  |  |  | 401 |
| Catalogue (phase 2) |  |  | 103 |  |  |

The catalogue is larger, so absolute gap counts grew too; most new gaps are (d) and (e):
the new shoes come mostly from brands that publish little or block automated access.

## Before / after

| | Before Part B | After Part B |
|---|---|---|
| Shoes in shoes.json | 217 | 389 |
| Spec `weight_g` known (men's or women's) | 111 (51%) | 211 (54%) |
| Spec `stack_heel_mm` known | 58 (27%) | 85 (22%) |
| Spec `stack_forefoot_mm` known | 58 (27%) | 85 (22%) |
| Spec `drop_mm` known | 126 (58%) | 227 (58%) |
| Spec `lug_depth_mm` known | 86 (40%) | 144 (37%) |
| Spec `midsole_foam` known | 119 (55%) | 209 (54%) |
| Spec `outsole_rubber` known | 154 (71%) | 314 (81%) |
| Spec `plate` known | 36 (17%) | 83 (21%) |
| Spec `waterproof` known | 16 (7%) | 53 (14%) |
| Spec `width_options` known | 4 (2%) | 7 (2%) |
| Spec `platform_width_forefoot_mm` known | 45 (21%) | 70 (18%) |
| At least one manufacturer value | 48 (22%) | 69 (18%) |
| 0 expert review source(s) | 136 (63%) | 256 (66%) |
| 1 expert review source(s) | 49 (23%) | 89 (23%) |
| 2 expert review source(s) | 30 (14%) | 40 (10%) |
| 3 expert review source(s) | 2 (1%) | 4 (1%) |
| Buyer rating | 126 (58%) | 209 (54%) |
| Confidence high | 2 (1%) | 4 (1%) |
| Confidence medium | 45 (21%) | 61 (16%) |
| Confidence low | 170 (78%) | 324 (83%) |
| Criterion `cushioning` scored | 82 (38%) | 132 (34%) |
| Criterion `protection` scored | 79 (36%) | 120 (31%) |
| Criterion `grip` scored | 127 (59%) | 232 (60%) |
| Criterion `stability` scored | 79 (36%) | 116 (30%) |
| Criterion `responsiveness` scored | 73 (34%) | 131 (34%) |
| Criterion `lightness` scored | 127 (59%) | 230 (59%) |
| Criterion `durability` scored | 105 (48%) | 186 (48%) |
| Criterion `fit_width` scored | 74 (34%) | 119 (31%) |
| Terrain scores (lug depth known) | 86 (40%) | 144 (37%) |

On the models present in both versions:

| Same 213 models | Before | After |
|---|---|---|
| with an expert review | 80 | 84 |
| with a RunRepeat review | 45 | 50 |
| buyer rating | 125 | 133 |
| lug depth known | 85 | 90 |
| stack heights known | 57 | 62 |
| confidence medium or high | 46 | 51 |
| retail offers (total) | 1188 | 1413 |

## Rankings of the six example profiles (`npm run examples`)

The heavy ultra runner on technical terrain now gets the Hoka Mafate 5 and Hoka
Challenger 8 at the top (before: adidas Agravic TT, a lighter all-round shoe). The
"I like the Peregrine 15" list now includes the Hoka Speedgoat 6. The Topo Athletic MTN
Racer 3 enters 5 of the 6 top-5 lists, which deserves a look. The mud profile is still led
by the La Sportiva Prodigio Max, whose mud score rests on its lug depth alone.

## Still blocked (e), with the reason

| Source | Reason |
|---|---|
| Le Pape | Cloudflare bot challenge on every page |
| i-Run | terms forbid extracting any part of the site |
| Doctors of Running | robots.txt disallows anthropic-ai and Claude-Web |
| Running Warehouse, iRunFar | terms forbid robots, crawling, scraping |
| Trail Runner Magazine | robots.txt: scraping or data mining with automated tools not allowed |
| La Sportiva, Altra, Asics, adidas, Brooks, New Balance, Salomon, Scott, Hoka, Vivobarefoot, Helly Hansen, Icebug | bot protection (403, 429, challenges) |
| Joma, Craft, Inov-8, Tecnica | robots.txt bans scripted clients or AI crawlers |
| Rossignol, Under Armour, Millet, On, HI-TEC, Mount to Coast | terms forbid extraction or robots |
| Vibram FiveFingers | terms page behind a Cloudflare challenge |

## Decisions waiting for the project owner

* ~~The defaults in `docs/defaults-review.md`~~: decided on 2026-10-29, defaults 1-3
  applied (scoring 0.4.0, see the end of that file), 4-12 kept.
* 102 rows of `data/interim/needs_review.csv` and 66 of `data/interim/reviews_needs_review.csv`.
* The catalogue grew from 220 to 401 models (389 in `shoes.json`), above the 150-200
  announced in `docs/sources.md`'s first version; the purpose statement was updated.
