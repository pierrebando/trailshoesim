# Phase 8 report: deployment and documentation

## What was produced

* `.github/workflows/deploy.yml`: on every push to `main` (or a manual run), install
  Node 22, `npm ci`, run the Vitest suite, build `web/` from the committed
  `data/processed/` and publish `web/dist/` with `actions/deploy-pages`. The pipeline is
  not run in CI. The same steps were replayed locally (`npm ci`, `npm test`,
  `npm run build`): they pass.
* `README.md` rewritten for a reader with 5 minutes: what it is, live URL, screenshot
  placeholder, how it works + Mermaid diagram, sources and the legal/ethical approach,
  scoring and AI in 10 lines each (with the evaluation numbers), limitations, how to
  reproduce, data refresh, deployment, repository map.
* Docs made consistent with the code: `docs/data-coverage.md` gets a "Final coverage"
  block written by `python -m pipeline.build` (and the phase 3 generator now keeps it),
  `schema/README.md` names `shoes.json` and `meta.schema.json`, `docs/README.md` lists
  `evaluation.md`, `CLAUDE.md` says where lab measurements live.

## Audit

| Check | Result |
|---|---|
| pytest | 209 passed |
| ruff check / ruff format | clean / 91 files formatted |
| JSON Schemas vs pydantic models | in sync |
| Vitest | 36 passed |
| Type check + production build | OK (87 kB of gzipped JS; data loaded separately) |
| HTML files committed | only the 12 hand-written fictional test fixtures and `web/index.html` |
| Third-party text in `data/` | no single excerpt over 30 words; longer cells are our own text (missing reasons) or lists of short retailer titles |
| Quotes over 30 words in Markdown files | none |
| `.gitignore` | raw cache, review texts, `node_modules`, `dist`, copied web data, venv, `.env`, tool settings all ignored |
| README links | all present except `docs/img/screenshot.png` (placeholder for the owner) |
| Site under the GitHub Pages sub-path (`vite preview --base /trailshoesim/`) | data loads from `/trailshoesim/data/`, profile read from the URL, model page OK, no console error |

## Owner's decision (2026-10-29)

The project owner publishes the site and keeps the repository public as a
non-commercial school project, accepting the risk described in issue 1 below rather than
waiting for Tradeinn's (and RunRepeat's) permission. Collection rules are unchanged: sites
that block bots, ban AI crawlers or forbid extraction stay uncollected.

## Remaining issues

1. **Permission before publishing (blocking, owner's decision).** `docs/sources.md`
   recorded that Tradeinn's legal notice requires written permission for any reuse of
   its content, and that the owner should ask **before publishing the web app or pushing
   `data/interim/` to a public repository**. The repository is already public with that
   data (pushed in phase 6), and the site would show Tradeinn prices and ratings.
   Same family of caveats: RunRepeat sells its lab data (the site shows its measurements
   with a link); Believe in the Run's terms forbid reproducing any part (we show 30-word
   excerpts with links). Options: ask Tradeinn (and RunRepeat) for permission first; or
   make the repository private until then (a free GitHub account then cannot serve Pages).
2. `docs/img/screenshot.png` is a placeholder until the owner adds it.
3. Data limits are unchanged (see README "Limitations"): about 140 of 217 shoes cannot
   be ranked for a typical profile.
4. The engine is tested; the React pages are checked by hand in a browser, not by
   automated UI tests.

## More data within the rules (2026-10-29, branch `more-data`)

The owner asked for more data. Sites that refused automated access stay uncollected; two
sources we were already allowed to use were exploited further.

1. **RunRepeat lab weight and drop** (already collected in phase 4, previously unused).
   Weight: lab before retailer, as decision 14 says. On the 25 shoes with both, the median
   difference is 8 g; where they disagree the lab is more credible (La Sportiva Mutant:
   retailer 260 g, lab 323 g; reviewers call it "unquestionably heavy"). Drop: **stated
   values first** (manufacturer, retailer), lab only when nobody states one, because a
   measured drop can be far from the designed drop runners filter on (Agravic Speed
   Ultra 2: 0.1 mm measured, 8 mm stated). Scoring 0.3.1.
2. **Sitemap matching** for the 20 models of readable brand sites that were not found:
   URLs are now percent-decoded (Puma hides a non-breaking space: `nitro%C2%A04`), and
   two synonyms are applied to both sides ("TR" = "trail", "ATR" = "all terrain"). New
   pages: Merrell Agility Trail, Puma Voyage Nitro 4, Puma Fast-Trac Nitro 4, Scarpa
   Golden Gate 2 ATR (45 -> 49 models with a manufacturer page); Puma Pounce Lite 2 now
   uses its base page instead of the PTX (waterproof) variant. The other 16 are really
   absent from the brands' sitemaps (older versions such as Peregrine 13/15, lifestyle
   models such as Mizuno MXR) or are catalogue duplicates ("Wave Rider TT 3 Wos",
   "Amplux 2 Misty": phase 2 should merge them).

| Field known (of 217 shoes) | Before | After |
|---|---|---|
| Weight (men's) | 75 | 97 |
| Drop | 114 | 126 |
| Stack heights | 57 | 58 |
| Lug depth | 85 | 86 |
| Midsole foam | 117 | 119 |

Confidence: low 174 -> 170, medium 41 -> 45, high 2. Criterion scores barely move
(lightness 126 -> 127, stability 78 -> 79): most of these shoes already had a women's weight.
