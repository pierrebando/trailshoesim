# Phase 3 report — manufacturer specs

Date: 2026-10-28. Output: `data/interim/specs.json` (220 records, keyed by model id),
`docs/data-coverage.md`. Access decisions per brand: `docs/sources.md`.

## Results

- Brand sites: 25 checked; **9 allowed**, 16 not collected (bot protection 9, robots.txt
  bans on AI crawlers or scripted clients 3, terms 1, terms unreadable 3... see sources.md).
- Models with an official page found: **45 of 220 (20 %)**. Of the 67 models of allowed
  brands, 45 were found; the others are older versions no longer in the brand's sitemap,
  or VEJA (no sitemap).
- Values rejected by verification in the final run: 0. Values skipped as implausible: 6
  weights of 580-680 g (pair weights on Mizuno and Merrell pages).

| Field | % of all models | % of models with a page |
|---|---|---|
| weight_g | 11 % | 56 % |
| weight_women_g | 1 % | 7 % |
| stack_heel_mm / stack_forefoot_mm | 7 % | 36 % |
| drop_mm | 11 % | 53 % |
| lug_depth_mm | 8 % | 38 % |
| midsole_foam (+ family) | 12 % | 58 % |
| plate | 1 % | 7 % |
| outsole_rubber | 12 % | 58 % |
| waterproof | 0 % | 0 % |
| upper_notes | 13 % | 64 % |
| width_options | 2 % | 9 % |
| release_year | 0 % | 0 % |

## The 10 biggest data holes

1. La Sportiva (19 models): site refuses robots.txt (403).
2. Altra (16): Akamai bot protection.
3. Asics (16): Akamai.
4. adidas (15): Akamai.
5. Joma (14): robots.txt bans scripted clients.
6. New Balance (10): 403.
7. Salomon (9): PerimeterX.
8. Vibram FiveFingers (9): terms behind a Cloudflare challenge.
9. `waterproof` and `release_year`: 0 % everywhere. We read the base (non-GTX) page, and
   a product name without "GORE-TEX" is not proof that a shoe is not waterproof.
   Phase 2's title variants (`variants.waterproof`) remain the source for this.
10. `plate` (7 % of found pages) and `width_options` (9 %): rarely stated.

## How values are kept honest

- Every known value has `raw_snippet` (max 30 words, verbatim) and is checked against
  the page text (`pipeline/specs/extract.py: verify`).
- Non-verbatim steps are labelled `derivation`: `order_from_drop` (16 stack pairs whose
  heel/forefoot order is fixed by the stated drop), `unit_from_label` (6 Scarpa weights
  written without unit), `family_from_name` (foam family from the foam's own name only:
  "PWRRUN", "FloatPro™", "BOUNCE FOAM" are `other`, not guessed).
- Lab measurements from review sites have their own `lab_fallback` slot, empty for now.
- No LLM was used: rules are deterministic and every value is reproducible.

## Known problems

- Loose URL matches to check: Lowa "Madrix" -> `madrix-evo` (perhaps a newer model),
  Merrell "Vapor Glove 6" -> the leather variant, Puma "Pounce Lite 2" -> the PTX
  (waterproof) variant. Each record lists `url_extra_words`.
- Weight size reference is often not stated (Saucony, Dynafit, Merrell): see `note`.
- Mixed foams are reduced to the first name: Scarpa Golden Gate LT is stored as "EVA"
  while the page says "EVA ... combinée à 20 % de Pebax".
- Several Mizuno pages are marketing-only (no spec table).

## What to verify

Open 3-4 `manufacturer_url`s and compare with the `raw_snippet`s (5 examples are in the
phase 3 checkpoint message). Decide whether to contact the blocked brands or accept the gap.

## Phase 3b — retailer specs fallback (added 2026-10-28)

`ModelSpecs.retailer_fallback`, built from what Tradeinn and Glisshop show on their
product pages (`python -m pipeline.specs --retailer-only`, offline, from the caches).
Manufacturer fields are untouched; phase 6 uses manufacturer > lab > retailer.

| Field | Manufacturer | Retailer fallback | Either source |
|---|---|---|---|
| weight_g | 11 % | 26 % | 34 % |
| weight_women_g | 1 % | 27 % | 28 % |
| drop_mm | 11 % | 44 % | 52 % |
| lug_depth_mm | 8 % | 21 % | 25 % |
| midsole_foam | 12 % | 45 % | 53 % |
| outsole_rubber | 12 % | 64 % | 70 % |
| plate | 1 % | 16 % | 16 % |
| waterproof | 0 % | 7 % | 7 % |

Extra retailer-only data: unlabelled sole height 13 %, drop/weight buckets 24 % each,
shop classifications (fit width 99 %, terrain 63 %, runner build / distance / pronation
43 %, cushioning level 10 %).

Rules: exact numbers only; buckets stay text; weight from men's/unisex standard-version
listings within 120-480 g, combined only within 5 % (lower median, a value a listing
really shows); listings that disagree give null with the reason; every value re-found in
the cached page (0 failures). Where both sources exist they agree: drop 6/6, lug depth
8/8, weight 8/9 (the miss was a women's weight).

Known problems with retailer data: it can be wrong (Tradeinn gives Vibram FiveFingers
KMD EVO a 6 mm drop; FiveFingers are zero-drop), women's listings sometimes repeat the
men's weight (flagged in the note), and almost all numbers come from Tradeinn, whose
legal notice requires written permission for reuse before publication.
