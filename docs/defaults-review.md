# Review of the project's defaults (2026-10-29)

CLAUDE.md mixes two kinds of rules. **Hard lines** come from law, the sites' own wishes
or honesty, and do not change because the project is educational. **Defaults** are
cautious engineering choices that can be revisited.

**Decision of the project owner (2026-10-29): defaults 1, 2 and 3 are changed; 4 to 12
stay as they are.** What was done is under "Applied" at the end.

Figures are measured on the catalogue after the coverage pass (389 shoes).

## Hard lines (kept as they are)

| Rule | Why it stays |
|---|---|
| Respect robots.txt, including bans of AI crawlers (ClaudeBot, anthropic-ai) and of scripted clients | The site owner's explicit wish; the collection is done by an AI assistant |
| Respect the terms of use (no collection where they forbid extraction or robots) | Contract with the site; a school project is not an exception in the terms we read |
| No circumvention of technical protections (Cloudflare, Akamai, PerimeterX, 403, 429) | A challenge is a refusal; working around it is not polite collection |
| No full third-party text; excerpts of at most 30 words with a link | Copyright (short quotation) |
| No secrets in the repository | Security |
| Never invent data; null with a reason | The scores must stay explainable |

## Defaults that may have been over-conservative

| Default | Recommendation | Why | What it would add |
|---|---|---|---|
| 1. A site that fails for a *technical* reason (TLS, timeout) is not retried | **Changed**: re-check such sites once per data refresh (never sites that refused us) | A technical failure is not a refusal | Today 0: Tecnica now bans AI crawlers; +8000, Oriocx, Boreal still fail; worth re-checking next time |
| 2. Retailer classifications ("Pied large", "Standard"...) are hints only, unused by the scores | **Changed, low weight**: use the fit tag as a second `fit_width` spec input (weight 0.3) | It is the shop's own statement about the shoe, labelled as such | A fit-width spec score for 389 shoes instead of 7; but 333 say "Standard", so it separates few shoes |
| 3. RunRepeat lab values used only for stacks, lug depth, platform widths, weight, drop | **Changed**: use measured energy return for responsiveness and midsole softness for cushioning, as spec inputs | They are measurements, better than our foam-name lookups | A responsiveness spec score for 51 more shoes (43 today); softness for 42 shoes |
| 4. `final.min_ranking_coverage` = 0.6 (shoes with less known data are not ranked) | **Keep, or 0.5** | Since scoring 0.3.0 unknown values count as a neutral 5, so a lower threshold is less risky | 0.5: 128 ranked instead of 122 (+6); 0.4: 167 (+45) for the default profile |
| 5. Fuzzy model matching needs score >= 92, same brand and version | **Keep the threshold; decide the queue** | Lowering it merges real distinct models (Agravic SL vs TT) | 102 rows in `data/interim/needs_review.csv` wait for a decision; a few are true duplicates |
| 6. A review must name the exact model and version (decision 15) | **Keep** | A Speedgoat 5 review does not describe a Speedgoat 6 | Using older versions would add a review to 48-54 models per source, but describing another shoe |
| 7. Ambiguous review matches go to a human | **Keep; decide the queue** | Comparisons and unconfirmed titles are often wrong | 66 rows in `data/interim/reviews_needs_review.csv` |
| 8. Derived values only by documented conversion (oz -> g, drop = heel - forefoot) | **Keep** (already done) | Women's -> men's weight would need a guessed factor | Drop from stacks: 0 shoes left to derive |
| 9. Review sources limited to RunRepeat, Believe in the Run, Esprit Trail | **Keep; ask permission** | Running Warehouse, iRunFar and Trail Runner Magazine all forbid scraping in their terms or robots.txt | Only with written permission |
| 10. Excerpt length 30 words | **Keep** | Copyright; no effect on coverage | - |
| 11. Request pacing 1.1 s per site, cache forever, `--refresh` to re-download | **Keep** | Faster pacing (up to 2/s) would only save time, not add data | - |
| 12. Models without any gender on the retailer pages are dropped | **Keep** | Assigning "unisex" would invent a value | 12 models |

## Applied (scoring 0.4.0)

1. **Technical failures are re-checked.** `manufacturers.yaml` has a third status,
   `unreachable` (+8000, Oriocx, Boreal), with the homepage to try. `python -m
   pipeline.recheck` asks each one again, without the cache, and only reports: if a site
   answers, a person reads its robots.txt and terms before setting `allowed`. `blocked`
   sites are never re-checked. Run on 2026-10-29: all three still fail (TLS error for
   +8000 and Oriocx, connection error for Boreal). The YAML key `+8000` is now quoted:
   unquoted, YAML read it as the number 8000, so the brand looked "not checked yet".
2. **Shop's fit class.** New spec `fit_width_tag` (retailer tier, verbatim). fit_width
   inputs: width options 0.7, fit class 0.3 ("Standard" and "Pied moyen" 5, "Lâche" 7.5,
   "Pied large" 8.5), with its own minimum coverage of 0.3 so the tag can score alone.
   fit_width now has a spec sub-score for 389 shoes (7 before) and a score for 389 (119
   before). 370 tags are neutral; 19 shoes move.
3. **Lab foam measurements.** New specs `midsole_softness_ac` and
   `energy_return_forefoot_pct` (lab tier only). They replace the foam class in cushioning
   and responsiveness when measured (the foam class is the fallback). Responsiveness now
   has a spec sub-score for 94 shoes (43 before); cushioning uses the measured softness
   for 42 shoes (its spec coverage stays at 85, because the stacks are still required to
   reach the threshold). The heel energy return (2 shoes without a forefoot value) is not
   used, because its scale differs from the forefoot one.

**Follow-up (scoring 0.4.1).** With the shop's class in fit_width, the narrow-foot boost
(0.3) pushed narrow-footed runners towards shoes the shops call wide, because fit_width
scores how roomy a shoe is. The project owner set it to 0; wide feet keep their boost.
