# Phase 7 report: the web app

## What was produced

`web/`: a static React + Vite + TypeScript app (dependencies: react, react-dom; dev: vite,
vitest, typescript). Plain CSS, a hand-written SVG radar, no UI kit or chart library.

| Feature | Where |
|---|---|
| Profile form (Runner, Run, Preferences) with defaults and a "how to tell" help for foot strike | `components/ProfileForm.tsx` |
| Hard filters: max price, excluded brands, waterproof, drop range, width, gender; "No shoe matches your filters" | `components/FiltersPanel.tsx`, `engine/filters.ts` |
| Ranked results: score, price range + cheapest retailer link, up to 3 reasons with review quotes, 1-2 drawbacks or missing data, confidence badge, "+ Compare"; "Not enough data to rank" list | `pages/FinderPage.tsx`, `components/ResultCard.tsx` |
| Model page: score breakdown for the profile, criteria radar + provenance, terrain bars, specs with sources and quotes (or the reason they are unknown), specialist excerpts with links, offers per retailer with date and rating, confidence panel and what is missing | `pages/ShoePage.tsx` |
| "I like this model": search, top 10 similar shoes with what is close and what differs, other versions labelled, hard filters applied | `pages/SimilarPage.tsx`, `engine/similarity.ts` |
| Comparator: 2-4 shoes, a small radar per shoe, rows that differ highlighted, "▲ best" marks, "show only differences" | `pages/ComparePage.tsx`, `engine/compare.ts` |
| How it works: scoring in plain English, sources, limits, data dates | `pages/HowPage.tsx` |
| Footer: build date and price dates from `meta.json` | `components/Footer.tsx` |
| Profile, filters and comparator in the query string (shareable) | `url.ts` |

Engine (`web/src/engine/`, pure TypeScript): `filters.ts` (§1), `weights.ts` (§5),
`scoring.ts` (§6), `similarity.ts` (§7), `confidence.ts` (§8), `compare.ts`.

## Tests

`npm test`: **36 Vitest tests pass** (6 files): the §5.8 worked example of the weights
(all 10 terms and the 14.322 total), heavier runner → more cushioning and durability
weight and less lightness, continuity in weight and distance, log-scale distance,
sliders, terrain shares, foot strike/width boosts; every filter including unknown values
and gender/unisex; points of the explanation add up to the score; the score is absolute
(all 10s = 100); drop-fit bell curve (6 mm for a heel striker ≈ 7.5); derived poles;
unknown terms count as neutral; no score when nothing is known; not ranked below 60 %
coverage; reasons/drawbacks; missing data; tie-breaking; similarity of a shoe with itself
= 100, symmetry, explanations, "not comparable", other versions; price age; comparator
helpers; URL round trip. Python: 209 tests still pass.

Checked in a browser: every page, no console error, no horizontal scroll at 375 px, and
the static build served under `/trailshoesim/` (as GitHub Pages will).

## Deviations from the spec or the brief

1. **Spec changed (0.3.0) after the owner's review of the example rankings**: an unknown
   weighted term now counts as a neutral 5 in the final score instead of being dropped
   (the Asics Trabuco Max 4, a max-cushion shoe with unknown responsiveness, ranked first
   for a light runner who asked for a dynamic shoe). Reasons and drawbacks still use known
   values only; unknown terms are listed as missing data. Tests cover it.
2. **"Converts scoring.yaml to JSON"**: the Python build already writes
   `data/processed/scoring_config.json`; `web/scripts/sync-data.mjs` copies it with the
   data and refuses if the scoring versions of `shoes.json` and the config differ, so the
   browser always uses the constants the pipeline used.
3. **Gender**: the profile's gender drives the gender filter ("only shoes sold in my
   gender, or unisex"), as spec §1 says; there is no separate gender choice in the filters.
4. **Buyer term**: it is shown in the score breakdown (model page) but not among "why it
   fits" reasons, which compare criteria and terrain against the alternatives (§6.5).
5. **Comparator radar**: one small radar per shoe instead of overlaid outlines; overlaid
   shapes stop being readable beyond three, and one hue per radar needs no legend.
6. **Routing**: pages are hash routes (`#/shoe/<id>`) so a static host needs no rewrite
   rules; the profile is in the real query string before the hash.

## Known limits

* About 140 of the 217 shoes cannot be ranked for a typical profile (too little known
  data, spec §6.3), and similarity skips about 157 for lack of shared features. The app
  says so on each page.
* The width and waterproof filters hide most shoes: width options are known for 4 shoes,
  waterproofing for 16. The results say how many were hidden because the value is unknown.
* Retailer listings of a model include its variants (GTX...), so the price range of a
  card can mix them.
* Scores of the top shoes are close (within a few points): the ranking is a shortlist,
  not a verdict.

## What the project owner should verify

1. `cd web && npm install && npm run dev`, then try your own profile and two friends'.
2. `npm run examples` prints the top 5 of the three example runners.
3. Read the "How it works" page as a visitor would.
