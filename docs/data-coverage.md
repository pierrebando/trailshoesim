# Data coverage

Manufacturer specs (phase 3) first, then expert reviews (phase 4) and the final coverage of `data/processed/shoes.json` (phase 6) at the end.

## Manufacturer specs (phase 3)

Generated 2026-10-29 from `data/interim/specs.json` (`python -m pipeline.specs`).

- Models: **220**
- Official product page found: **49** (22 %)
- Percentages are over ALL models; the last column is over models with a page found.

## Fields

| Field | Filled | % of all models | % of models with a page |
|---|---|---|---|
| `weight_g` | 28 | 13 % | 57 % |
| `weight_women_g` | 3 | 1 % | 6 % |
| `stack_heel_mm` | 17 | 8 % | 35 % |
| `stack_forefoot_mm` | 17 | 8 % | 35 % |
| `drop_mm` | 27 | 12 % | 55 % |
| `lug_depth_mm` | 19 | 9 % | 39 % |
| `midsole_foam` | 31 | 14 % | 63 % |
| `midsole_foam_family` | 31 | 14 % | 63 % |
| `plate` | 3 | 1 % | 6 % |
| `outsole_rubber` | 26 | 12 % | 53 % |
| `waterproof` | 0 | 0 % | 0 % |
| `upper_notes` | 32 | 15 % | 65 % |
| `width_options` | 4 | 2 % | 8 % |
| `release_year` | 0 | 0 % | 0 % |

## Retailer fallback (phase 3b, separate from manufacturer data)

Values shown on Tradeinn/Glisshop product pages (`retailer_fallback`). Phase 6 uses
manufacturer data first, then lab measurements, then these, with lower confidence.

| Field | Manufacturer | Retailer fallback | Either source |
|---|---|---|---|
| `weight_g` | 28 (13 %) | 57 (26 %) | 77 (35 %) |
| `weight_women_g` | 3 (1 %) | 60 (27 %) | 61 (28 %) |
| `drop_mm` | 27 (12 %) | 96 (44 %) | 115 (52 %) |
| `lug_depth_mm` | 19 (9 %) | 47 (21 %) | 57 (26 %) |
| `midsole_foam` | 31 (14 %) | 98 (45 %) | 119 (54 %) |
| `outsole_rubber` | 26 (12 %) | 141 (64 %) | 154 (70 %) |
| `plate` | 3 (1 %) | 35 (16 %) | 36 (16 %) |
| `waterproof` | 0 (0 %) | 16 (7 %) | 16 (7 %) |

| Retailer-only field | Filled |
|---|---|
| `sole_height_unlabelled_mm` | 28 (13 %) |
| `drop_range` | 53 (24 %) |
| `weight_range` | 52 (24 %) |
| `tags.fit_width` (shop classification) | 217 (99 %) |
| `tags.terrain` (shop classification) | 138 (63 %) |
| `tags.cushioning_level` (shop classification) | 22 (10 %) |
| `tags.runner_build` (shop classification) | 94 (43 %) |
| `tags.distance` (shop classification) | 94 (43 %) |
| `tags.pronation` (shop classification) | 94 (43 %) |

## Brands

| Brand | Models | Page found | Why not |
|---|---|---|---|
| La Sportiva | 19 | 0 | manufacturer site not collected: robots.txt itself answers HTTP 403 (bot protection) (19) |
| Altra | 16 | 0 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) (16) |
| Asics | 16 | 0 | manufacturer site not collected: Akamai bot protection (HTTP 403 on every page) (16) |
| Merrell | 15 | 13 | no matching product page in the manufacturer sitemap (2) |
| adidas | 15 | 0 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) (15) |
| Joma | 14 | 0 | manufacturer site not collected: robots.txt disallows scripted clients (Python-requests, curl, Python-urllib) (14) |
| Mizuno | 13 | 8 | no matching product page in the manufacturer sitemap (5) |
| New Balance | 10 | 0 | manufacturer site not collected: HTTP 403 error page on every request (10) |
| Salomon | 9 | 0 | manufacturer site not collected: PerimeterX bot protection ('Access to this page has been denied') (9) |
| Vibram FiveFingers | 9 | 0 | manufacturer site not collected: terms page behind a Cloudflare challenge: terms could not be checked (9) |
| Craft | 8 | 0 | manufacturer site not collected: robots.txt disallows ClaudeBot and anthropic-ai (AI crawlers) (8) |
| Puma | 8 | 4 | no matching product page in the manufacturer sitemap (4) |
| Saucony | 8 | 5 | no matching product page in the manufacturer sitemap (3) |
| Scott | 8 | 0 | manufacturer site not collected: Incapsula bot challenge (8) |
| Brooks | 7 | 0 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) (7) |
| Scarpa | 7 | 7 |  |
| Under Armour | 7 | 0 | manufacturer site not collected: terms page rendered by JavaScript: terms could not be checked (7) |
| NNormal | 6 | 5 | no matching product page in the manufacturer sitemap (1) |
| Rossignol | 5 | 0 | manufacturer site not collected: terms forbid systematic extraction and robots/scrapers (5) |
| Dynafit | 4 | 4 |  |
| Inov-8 | 4 | 0 | manufacturer site not collected: robots.txt disallows ClaudeBot, Claude-Web and anthropic-ai (AI crawlers) (4) |
| Lowa | 4 | 3 | no matching product page in the manufacturer sitemap (1) |
| Millet | 3 | 0 | manufacturer site not collected: legal pages rendered by JavaScript: terms could not be checked (3) |
| Tecnica | 3 | 0 | manufacturer site not collected: site unreachable (TLS certificate error) (3) |
| VEJA | 2 | 0 | no sitemap published by the manufacturer; product page not searched (2) |

## The 20 models with the most missing fields

| Model id | Missing fields (of 14) | Reason |
|---|---|---|
| `adidas-agravic` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-4` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-flow-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-lite` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-sl` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-speed` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-speed-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-speed-ultra-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-tt` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-soulstride` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-soulstride-flow` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-tracefinder` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-tracefinder-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-tracefinder-plus` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `altra-escalante-4` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `altra-experience-wild` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `altra-experience-wild-3-plus` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `altra-king-mt-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `altra-lone-peak-9` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |

## Among models whose page was found: the thinnest pages

| Model id | Missing fields (of 14) | Page |
|---|---|---|
| `mizuno-neo-lumina` | 14 | https://emea.mizuno.com/eu/fr-fr/mizuno-neo-lumina/J1GJ267301.html |
| `dynafit-ultra-dna` | 13 | https://www.dynafit.com/fr-fr/chaussure-ultra-dna |
| `merrell-wrapt` | 13 | https://www.merrell.com/FR/fr_FR/wrapt/50938M.html |
| `mizuno-mxr-sport` | 13 | https://emea.mizuno.com/eu/fr-fr/mxr-sport/D1GA2451.html |
| `mizuno-wave-mujin-11` | 13 | https://emea.mizuno.com/eu/fr-fr/wave-mujin-11/J1GJ257051.html |
| `saucony-guide-tr` | 13 | https://www.saucony.com/FR/fr_FR/guide-tr/61277M.html |
| `merrell-vapor-glove-6` | 12 | https://www.merrell.com/FR/fr_FR/vapor-glove-6-leather/58037W.html |
| `mizuno-neo-accera` | 12 | https://emea.mizuno.com/eu/fr-fr/mizuno-neo-accera/J1GJ265001.html |
| `mizuno-wave-rider-tt-3` | 12 | https://emea.mizuno.com/eu/fr-fr/wave-rider-tt-3/J1GC253251.html |
| `merrell-antora-4` | 11 | https://www.merrell.com/FR/fr_FR/antora-4/60157W.html |
| `merrell-morphlite` | 11 | https://www.merrell.com/FR/fr_FR/morphlite/58734M.html |
| `merrell-nova-4` | 11 | https://www.merrell.com/FR/fr_FR/nova-4/60175M.html |
| `merrell-speed-strike-2` | 11 | https://www.merrell.com/FR/fr_FR/speed-strike-2/59768M.html |
| `merrell-vapor-glove-7` | 11 | https://www.merrell.com/FR/fr_FR/vapor-glove-7/61058M.html |
| `mizuno-neo-daichi-10` | 11 | https://emea.mizuno.com/eu/fr-fr/mizuno-neo-daichi-10/J1GM268051.html |
| `saucony-ride-tr-3` | 11 | https://www.saucony.com/FR/fr_FR/ride-tr3/61276M.html |
| `dynafit-ultra-100-3` | 10 | https://www.dynafit.com/fr-fr/chaussure-running-ultra-100-v3-hommes-08-0000064117 |
| `dynafit-ultra-50` | 10 | https://www.dynafit.com/fr-fr/chaussure-running-ultra-50-hommes-08-0000064066 |
| `merrell-agility-tr` | 10 | https://www.merrell.com/FR/fr_FR/agility-trail/60972M.html |
| `merrell-mtl-adapt-matryx` | 10 | https://www.merrell.com/FR/fr_FR/mtl-adapt-matryx/60174W.html |

<!-- reviews:start -->

## Expert reviews (phase 4)

Generated 2026-10-28 from `data/interim/expert_reviews.json` (`python -m pipeline.reviews --source all`). Doctors of Running is not collected (robots.txt bans AI crawlers), so at most 3 sources per model.

| Sources with a review | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Models | 139 | 49 | 30 | 2 | 0 |

| Source | Models reviewed | of which exact | variant | manual |
|---|---|---|---|---|
| believe_in_the_run | 63 | 58 | 4 | 2 |
| esprit_trail | 7 | 7 | 0 | 0 |
| runrepeat | 45 | 45 | 2 | 0 |

Reviews with lab measurements: 47.

<!-- reviews:end -->

<!-- build:start -->

## Final coverage in data/processed/shoes.json (phase 6)

Generated 2026-10-28 by `python -m pipeline.build` (scoring 0.3.1): 217 shoes. Each spec field takes the manufacturer value, else a lab measurement (RunRepeat), else the retailer's.

| Field | Known | Manufacturer | Lab (RunRepeat) | Retailer |
|---|---|---|---|---|
| weight_g | 97 (45%) | 28 | 39 | 30 |
| weight_women_g | 61 (28%) | 3 | 0 | 58 |
| stack_heel_mm | 58 (27%) | 17 | 41 | 0 |
| stack_forefoot_mm | 58 (27%) | 17 | 41 | 0 |
| drop_mm | 126 (58%) | 27 | 11 | 88 |
| lug_depth_mm | 86 (40%) | 19 | 42 | 25 |
| lug_spacing | 0 (0%) | 0 | 0 | 0 |
| platform_width_heel_mm | 45 (21%) | 0 | 45 | 0 |
| platform_width_forefoot_mm | 45 (21%) | 0 | 45 | 0 |
| midsole_foam | 119 (55%) | 31 | 0 | 88 |
| plate | 36 (17%) | 3 | 0 | 33 |
| outsole_rubber | 154 (71%) | 26 | 0 | 128 |
| waterproof | 16 (7%) | 0 | 0 | 16 |
| upper_notes | 32 (15%) | 32 | 0 | 0 |
| width_options | 4 (2%) | 4 | 0 | 0 |

| Criterion | Scored | Specs only | Reviews only | Both | Median |
|---|---|---|---|---|---|
| cushioning | 82 (38%) | 7 | 24 | 51 | 5.6 |
| protection | 79 (36%) | 14 | 21 | 44 | 6.3 |
| grip | 127 (59%) | 69 | 8 | 50 | 7.1 |
| stability | 79 (36%) | 17 | 21 | 41 | 6.0 |
| responsiveness | 73 (34%) | 14 | 52 | 7 | 6.0 |
| lightness | 127 (59%) | 54 | 16 | 57 | 5.6 |
| durability | 105 (48%) | 43 | 33 | 29 | 6.7 |
| fit_width | 74 (34%) | 2 | 70 | 2 | 5.0 |

| Terrain | Scored |
|---|---|
| road_to_trail | 86 (40%) |
| groomed_mixed | 86 (40%) |
| technical_rocky | 72 (33%) |
| muddy_soft | 86 (40%) |
| wet_roots | 39 (18%) |

<!-- build:end -->
