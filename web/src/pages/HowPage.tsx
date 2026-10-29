// "How it works": the scoring in plain English, the sources and the limits.

import type { AppData } from "../data";
import { SOURCE_LABEL } from "../labels";

const day = (iso: string) => new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

export function HowPage({ data }: { data: AppData }) {
  const { meta, config } = data;
  const pct = (v: number) => `${Math.round(v * 100)} %`;
  return (
    <article className="narrow-page prose">
      <h2>How it works</h2>
      <p>
        Trail Shoe Finder ranks the shoes sold by French retailers for <em>your</em> profile and
        always says why. Everything is computed from public data; nothing is sponsored.
      </p>

      <h3>1. What we know about each shoe</h3>
      <ul>
        <li><strong>Which shoes and prices</strong>: the shoes currently sold by {meta.retailers.map((r) => SOURCE_LABEL[r] ?? r).join(" and ")}, with their price, buyer rating and number of reviews.</li>
        <li><strong>Specs</strong> (weight, stack height, drop, lug depth, foam, rubber...): from the manufacturer's page when we could read it, else measured in a lab by RunRepeat, else shown by the retailer. Every value links to its source. When RunRepeat measured the foam (softness, energy return), the measurement is used instead of a guess from the foam's name; the shop's own fit class ("Pied large"...) counts a little in the fit score.</li>
        <li><strong>Specialist reviews</strong> from {meta.review_sources.map((s) => SOURCE_LABEL[s] ?? s).join(", ")}: we keep a short quote and the link, never the full text.</li>
      </ul>

      <h3>2. Eight criteria, scored 0-10</h3>
      <p>
        Cushioning, protection, grip, stability, responsiveness, lightness, durability and roomy
        fit. Each score mixes two things: what the <strong>specs</strong> suggest (for example,
        more stack height means more cushioning, deeper lugs mean more grip) and what the
        <strong> reviews</strong> say. A small AI model, running offline, reads the reviews
        and finds sentences about each criterion and whether they are positive or negative.
        One review only moves a score a little; it takes three reviews to count fully. Terrain
        scores (mud, rock, groomed trails...) come from the specs only, mainly lug depth.
      </p>

      <h3>3. Your profile sets the weights</h3>
      <p>
        Heavier runners and longer distances give more weight to cushioning, stability,
        protection and durability, and less to lightness and responsiveness. This changes
        smoothly: 70 kg and 71 kg give almost the same ranking. The sliders, the terrains you
        pick, your foot strike (it sets a preferred drop) and your foot width add to it.
      </p>

      <h3>4. The score out of 100</h3>
      <p>
        The score is the weighted average of the shoe's criteria for you, with {pct(config.final.buyer_share)} for
        the buyer rating. Buyer ratings are adjusted for small samples: a 5/5 from 3 buyers
        counts less than a 4.6/5 from 200. When a value is unknown it counts as an average
        5/10, so a shoe cannot rank high because its weak points were never measured. A shoe
        whose known data covers less than {pct(config.final.min_ranking_coverage)} of what matters to you is not ranked;
        it appears in "Not enough data to rank". The score is absolute: 100 would mean 10/10
        on everything you care about, so it is not "the best shoe gets 100".
      </p>
      <p>
        "Why it fits" lists the criteria where the shoe is good <em>and</em> better than the other
        shoes that pass your filters. The confidence badge says how much data stands behind
        the shoe: specs known, number of reviews, how fresh the prices are.
      </p>

      <h3>5. Limits</h3>
      <ul>
        <li>The rules are <strong>heuristics, not science</strong>: reasonable rules of thumb from the running world, tunable, but not validated biomechanics.</li>
        <li>Data is thin: many manufacturers' sites could not be read, so many shoes have few specs and most have no specialist review.</li>
        <li>The text analysis of reviews agrees with a careful human reading on low / medium / high about 6 times in 10; it is better at ordering shoes than at exact levels.</li>
        <li>Prices change: they were checked on {day(meta.price_date_max)}. Always check the retailer's page.</li>
        <li>Retailer listings mix colours, genders and variants (e.g. Gore-Tex versions) of a model.</li>
      </ul>

      <h3>Data of this version</h3>
      <p>
        Built on {day(meta.build_date)} · {meta.shoe_count} shoes from {meta.brand_count} brands ·{" "}
        {meta.offer_count} retailer offers · {meta.expert_review_count} specialist reviews · scoring rules version{" "}
        {meta.scoring_config_version}. Full method: <code>docs/scoring-spec.md</code> in the project repository.
      </p>
    </article>
  );
}
