# Data coverage

Manufacturer specs (phase 3) first, then expert reviews (phase 4) and the final coverage of `data/processed/shoes.json` (phase 6) at the end.

## Manufacturer specs (phase 3)

Generated 2026-10-29 from `data/interim/specs.json` (`python -m pipeline.specs`).

- Models: **401**
- Official product page found: **70** (17 %)
- Percentages are over ALL models; the last column is over models with a page found.

## Fields

| Field | Filled | % of all models | % of models with a page |
|---|---|---|---|
| `weight_g` | 44 | 11 % | 63 % |
| `weight_women_g` | 3 | 1 % | 4 % |
| `stack_heel_mm` | 19 | 5 % | 27 % |
| `stack_forefoot_mm` | 19 | 5 % | 27 % |
| `drop_mm` | 44 | 11 % | 63 % |
| `lug_depth_mm` | 27 | 7 % | 39 % |
| `midsole_foam` | 35 | 9 % | 50 % |
| `midsole_foam_family` | 35 | 9 % | 50 % |
| `plate` | 10 | 2 % | 14 % |
| `outsole_rubber` | 42 | 10 % | 60 % |
| `waterproof` | 0 | 0 % | 0 % |
| `upper_notes` | 40 | 10 % | 57 % |
| `width_options` | 7 | 2 % | 10 % |
| `release_year` | 0 | 0 % | 0 % |

## Retailer fallback (phase 3b, separate from manufacturer data)

Values shown on Tradeinn/Glisshop product pages (`retailer_fallback`). Phase 6 uses
manufacturer data first, then lab measurements, then these, with lower confidence.

| Field | Manufacturer | Retailer fallback | Either source |
|---|---|---|---|
| `weight_g` | 44 (11 %) | 121 (30 %) | 147 (37 %) |
| `weight_women_g` | 3 (1 %) | 118 (29 %) | 119 (30 %) |
| `drop_mm` | 44 (11 %) | 190 (47 %) | 209 (52 %) |
| `lug_depth_mm` | 27 (7 %) | 94 (23 %) | 106 (26 %) |
| `midsole_foam` | 35 (9 %) | 191 (48 %) | 209 (52 %) |
| `outsole_rubber` | 42 (10 %) | 307 (77 %) | 314 (78 %) |
| `plate` | 10 (2 %) | 80 (20 %) | 83 (21 %) |
| `waterproof` | 0 (0 %) | 53 (13 %) | 53 (13 %) |

| Retailer-only field | Filled |
|---|---|
| `sole_height_unlabelled_mm` | 41 (10 %) |
| `drop_range` | 143 (36 %) |
| `weight_range` | 132 (33 %) |
| `tags.fit_width` (shop classification) | 389 (97 %) |
| `tags.terrain` (shop classification) | 158 (39 %) |
| `tags.cushioning_level` (shop classification) | 37 (9 %) |
| `tags.runner_build` (shop classification) | 91 (23 %) |
| `tags.distance` (shop classification) | 91 (23 %) |
| `tags.pronation` (shop classification) | 91 (23 %) |

## Brands

| Brand | Models | Page found | Why not |
|---|---|---|---|
| adidas | 22 | 0 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) (22) |
| La Sportiva | 19 | 0 | manufacturer site not collected: robots.txt itself answers HTTP 403 (bot protection) (19) |
| Salomon | 19 | 0 | manufacturer site not collected: PerimeterX bot protection ('Access to this page has been denied') (19) |
| Topo Athletic | 19 | 5 | no matching product page in the manufacturer sitemap (8); product page answered HTTP 404 (4) |
| Altra | 18 | 0 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) (18) |
| Asics | 16 | 0 | manufacturer site not collected: Akamai bot protection (HTTP 403 on every page) (16) |
| Inov-8 | 15 | 0 | manufacturer site not collected: robots.txt disallows ClaudeBot, Claude-Web and anthropic-ai (AI crawlers) (15) |
| Merrell | 15 | 13 | no matching product page in the manufacturer sitemap (2) |
| Joma | 14 | 0 | manufacturer site not collected: robots.txt disallows scripted clients (Python-requests, curl, Python-urllib) (14) |
| Scott | 14 | 0 | manufacturer site not collected: Incapsula bot challenge (14) |
| Dynafit | 13 | 13 |  |
| +8000 | 12 | 0 | manufacturer site not collected: site unreachable (TLS certificate error) (12) |
| Mizuno | 12 | 8 | no matching product page in the manufacturer sitemap (4) |
| Scarpa | 12 | 9 | no matching product page in the manufacturer sitemap (3) |
| Craft | 10 | 0 | manufacturer site not collected: robots.txt disallows ClaudeBot and anthropic-ai (AI crawlers) (10) |
| New Balance | 10 | 0 | manufacturer site not collected: HTTP 403 error page on every request (10) |
| Vibram FiveFingers | 9 | 0 | manufacturer site not collected: terms page behind a Cloudflare challenge: terms could not be checked (9) |
| Icebug | 8 | 0 | manufacturer site not collected: HTTP 429 (too many requests) from the first request: treated as a refusal (8) |
| Puma | 8 | 4 | no matching product page in the manufacturer sitemap (4) |
| Saucony | 8 | 5 | no matching product page in the manufacturer sitemap (3) |
| Boreal | 7 | 0 | manufacturer site not collected: site unreachable (connection error) (7) |
| Brooks | 7 | 0 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) (7) |
| CMP | 7 | 0 | no sitemap published by the manufacturer; product page not searched (7) |
| HOKA | 7 | 0 | manufacturer site not collected: homepage answers HTTP 403 (bot protection) (7) |
| Under Armour | 7 | 0 | manufacturer site not collected: terms forbid downloading, copying or saving site content (7) |
| Vivobarefoot | 7 | 0 | manufacturer site not collected: robots.txt answers HTTP 403 (bot protection) (7) |
| Xero shoes | 7 | 2 | no matching product page in the manufacturer sitemap (4); loose match only (https://xeroshoes.com/products/mesa-summit-men, extra words: summit); check by hand (1) |
| HI-TEC | 6 | 0 | manufacturer site not collected: terms forbid to spider, crawl or scrape (6) |
| Lowa | 6 | 6 |  |
| NNormal | 6 | 5 | no matching product page in the manufacturer sitemap (1) |
| Mount to coast | 5 | 0 | manufacturer site not collected: terms forbid to spider, crawl or scrape (5) |
| Rossignol | 5 | 0 | manufacturer site not collected: terms forbid systematic extraction and robots/scrapers (5) |
| Helly hansen | 4 | 0 | manufacturer site not collected: robots.txt answers HTTP 403 (bot protection) (4) |
| Mammut | 4 | 0 | no matching product page in the manufacturer sitemap (3); loose match only (https://www.mammut.com/fr/fr/products/3090-00160/aenergy-trail-speed-low-men, extra words: speed); check by hand (1) |
| On | 4 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (4) |
| Oriocx | 4 | 0 | manufacturer site not collected: site unreachable (TLS certificate error) (4) |
| Tecnica | 4 | 0 | manufacturer site not collected: robots.txt disallows ClaudeBot, anthropic-ai and Claude-Web (AI crawlers) (4) |
| Ande | 3 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (3) |
| Millet | 3 | 0 | manufacturer site not collected: terms forbid any use or reproduction of site content (3) |
| Nike | 3 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (3) |
| Oakley | 3 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (3) |
| Skechers | 3 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (3) |
| Columbia | 2 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (2) |
| Keen | 2 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (2) |
| Kelme | 2 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (2) |
| Kilpi | 2 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (2) |
| VEJA | 2 | 0 | no sitemap published by the manufacturer; product page not searched (2) |
| X-BIONIC | 2 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (2) |
| 4t2 | 1 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (1) |
| Hummel | 1 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (1) |
| Olympikus | 1 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (1) |
| Raidlight | 1 | 0 | manufacturer site not checked yet (brand missing from manufacturers.yaml) (1) |

## The 20 models with the most missing fields

| Model id | Missing fields (of 14) | Reason |
|---|---|---|
| `4t2-get-lost` | 14 | manufacturer site not checked yet (brand missing from manufacturers.yaml) |
| `adidas-agravic` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-3` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-4` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-flow-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-lite` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-sl` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-speed` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-speed-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-speed-ultra` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-speed-ultra-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-agravic-tt` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-skychaser-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-soulstride` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-soulstride-flow` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-soulstride-ultra` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-tracefinder` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-tracefinder-2` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |
| `adidas-tracefinder-plus` | 14 | manufacturer site not collected: Akamai bot protection (HTTP 403 on robots.txt) |

## Among models whose page was found: the thinnest pages

| Model id | Missing fields (of 14) | Page |
|---|---|---|
| `mizuno-neo-lumina` | 14 | https://emea.mizuno.com/eu/fr-fr/mizuno-neo-lumina/J1GJ267301.html |
| `dynafit-ultra-dna` | 13 | https://www.dynafit.com/fr-fr/chaussure-ultra-dna |
| `merrell-wrapt` | 13 | https://www.merrell.com/FR/fr_FR/wrapt/50938M.html |
| `mizuno-mxr-sport` | 13 | https://emea.mizuno.com/eu/fr-fr/mxr-sport/D1GA2451.html |
| `mizuno-wave-mujin-11` | 13 | https://emea.mizuno.com/eu/fr-fr/wave-mujin-11/J1GJ257051.html |
| `saucony-guide-tr` | 13 | https://www.saucony.com/FR/fr_FR/guide-tr/61277M.html |
| `xero-shoes-hfs-2` | 13 | https://xeroshoes.com/products/hfs-ii-men-clearance |
| `xero-shoes-prio` | 13 | https://xeroshoes.com/products/prio-men |
| `dynafit-ultra-100` | 12 | https://www.dynafit.com/fr-fr/chaussure-running-ultra-100-hommes-08-0000064051 |
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
| `dynafit-alpine` | 10 | https://www.dynafit.com/fr-fr/chaussure-running-alpine-hommes-08-0000064064 |

<!-- reviews:start -->

## Expert reviews (phase 4)

Generated 2026-10-29 from `data/interim/expert_reviews.json` (`python -m pipeline.reviews --source all`). Doctors of Running is not collected (robots.txt bans AI crawlers), so at most 3 sources per model.

| Sources with a review | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Models | 267 | 90 | 40 | 4 | 0 |

| Source | Models reviewed | of which exact | variant | manual |
|---|---|---|---|---|
| believe_in_the_run | 103 | 102 | 9 | 2 |
| esprit_trail | 9 | 9 | 0 | 0 |
| runrepeat | 70 | 70 | 6 | 0 |

Reviews with lab measurements: 76.

<!-- reviews:end -->

<!-- build:start -->

## Final coverage in data/processed/shoes.json (phase 6)

Generated 2026-10-29 by `python -m pipeline.build` (scoring 0.4.1): 389 shoes. Each spec field takes the manufacturer value, else a lab measurement (RunRepeat), else the retailer's.

| Field | Known | Manufacturer | Manual (student) | Lab (RunRepeat) | Retailer |
|---|---|---|---|---|---|
| weight_g | 180 (46%) | 44 | 0 | 64 | 72 |
| weight_women_g | 119 (31%) | 3 | 0 | 0 | 116 |
| stack_heel_mm | 85 (22%) | 19 | 0 | 66 | 0 |
| stack_forefoot_mm | 85 (22%) | 19 | 0 | 66 | 0 |
| drop_mm | 227 (58%) | 44 | 0 | 18 | 165 |
| lug_depth_mm | 144 (37%) | 27 | 0 | 62 | 55 |
| lug_spacing | 0 (0%) | 0 | 0 | 0 | 0 |
| platform_width_heel_mm | 70 (18%) | 0 | 0 | 70 | 0 |
| platform_width_forefoot_mm | 70 (18%) | 0 | 0 | 70 | 0 |
| midsole_softness_ac | 42 (11%) | 0 | 0 | 42 | 0 |
| energy_return_forefoot_pct | 56 (14%) | 0 | 0 | 56 | 0 |
| midsole_foam | 209 (54%) | 35 | 0 | 0 | 174 |
| plate | 83 (21%) | 10 | 0 | 0 | 73 |
| outsole_rubber | 314 (81%) | 42 | 0 | 0 | 272 |
| waterproof | 53 (14%) | 0 | 0 | 0 | 53 |
| upper_notes | 40 (10%) | 40 | 0 | 0 | 0 |
| width_options | 7 (2%) | 7 | 0 | 0 | 0 |
| fit_width_tag | 389 (100%) | 0 | 0 | 0 | 389 |

| Criterion | Scored | Specs only | Reviews only | Both | Median |
|---|---|---|---|---|---|
| cushioning | 132 (34%) | 11 | 47 | 74 | 5.5 |
| protection | 120 (31%) | 17 | 35 | 68 | 6.0 |
| grip | 232 (60%) | 139 | 15 | 78 | 7.0 |
| stability | 116 (30%) | 22 | 31 | 63 | 6.0 |
| responsiveness | 140 (36%) | 43 | 46 | 51 | 6.0 |
| lightness | 230 (59%) | 113 | 19 | 98 | 5.8 |
| durability | 186 (48%) | 89 | 51 | 46 | 7.3 |
| fit_width | 389 (100%) | 275 | 0 | 114 | 5.0 |

| Terrain | Scored |
|---|---|
| road_to_trail | 144 (37%) |
| groomed_mixed | 144 (37%) |
| technical_rocky | 111 (29%) |
| muddy_soft | 144 (37%) |
| wet_roots | 62 (16%) |

<!-- build:end -->
