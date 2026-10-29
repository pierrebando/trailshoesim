// Model page: everything we know about one shoe, where it comes from, and what is missing.

import { useMemo } from "react";
import { ConfidenceBadge } from "../components/ConfidenceBadge";
import { Radar } from "../components/Radar";
import type { AppData } from "../data";
import { missingData, priceAgeDays } from "../engine/confidence";
import { scoreShoe } from "../engine/scoring";
import { CRITERIA, TERRAINS, type Criterion, type Shoe, type Specs } from "../engine/types";
import { computeWeights } from "../engine/weights";
import { euro, SOURCE_LABEL, shoeName, TERM_LABEL, TERRAIN_LABEL } from "../labels";
import type { AppState } from "../url";

const SPEC_LABEL: Record<Exclude<keyof Specs, "sources">, [string, string]> = {
  weight_g: ["Weight (men's reference size)", "g"],
  weight_women_g: ["Weight (women's reference size)", "g"],
  stack_heel_mm: ["Stack height, heel", "mm"],
  stack_forefoot_mm: ["Stack height, forefoot", "mm"],
  drop_mm: ["Drop", "mm"],
  lug_depth_mm: ["Lug depth", "mm"],
  lug_spacing: ["Lug spacing", ""],
  platform_width_heel_mm: ["Platform width, heel", "mm"],
  platform_width_forefoot_mm: ["Platform width, forefoot", "mm"],
  midsole_foam: ["Midsole foam", ""],
  plate: ["Plate", ""],
  outsole_rubber: ["Outsole rubber", ""],
  waterproof: ["Waterproof", ""],
  upper_notes: ["Upper", ""],
  width_options: ["Widths available", ""],
};
const TIER_LABEL = { manufacturer: "manufacturer", lab_measurement: "lab measurement", retailer: "retailer page" } as const;

const day = (iso: string | null) =>
  iso ? new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }) : "no date";

function formatValue(value: unknown, unit: string): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.map((v) => String(v).replace("_", " ")).join(", ");
  if (typeof value === "string") return value.replace("_", " ");
  return `${value}${unit ? ` ${unit}` : ""}`;
}

interface Props {
  data: AppData;
  state: AppState;
  setState: (next: AppState) => void;
  shoeId: string;
}

export function ShoePage({ data, state, setState, shoeId }: Props) {
  const shoe = data.catalog.shoes.find((s) => s.id === shoeId);
  const result = useMemo(
    () => (shoe ? scoreShoe(shoe, computeWeights(state.profile, data.config), data.config) : null),
    [shoe, state.profile, data.config],
  );
  if (!shoe || !result) {
    return <p className="notice">No shoe with the id "{shoeId}". <a href="#/">Back to the finder</a></p>;
  }
  const inCompare = state.compare.includes(shoe.id);
  const toggleCompare = () =>
    setState({ ...state, compare: inCompare ? state.compare.filter((x) => x !== shoe.id) : [...state.compare, shoe.id].slice(0, 4) });
  const newer = shoe.newer_version_id ? data.catalog.shoes.find((s) => s.id === shoe.newer_version_id) : undefined;

  return (
    <article className="shoe-page">
      <header className="shoe-header">
        <div>
          <p className="hint"><a href="#/">← Results</a></p>
          <h2>{shoeName(shoe)}</h2>
          <p className="hint">
            {shoe.category === "gravel" ? "Gravel / road-to-trail shoe" : "Trail shoe"} · sold for{" "}
            {shoe.gender_variants.join(", ")}
            {newer && <> · a newer version exists: <a href={`#/shoe/${newer.id}`}>{shoeName(newer)}</a></>}
          </p>
        </div>
        <div className="shoe-actions">
          <ConfidenceBadge confidence={shoe.confidence} />
          <button type="button" className={inCompare ? "button selected" : "button"} aria-pressed={inCompare}
            disabled={!inCompare && state.compare.length >= 4} onClick={toggleCompare}>
            {inCompare ? "✓ In comparator" : "+ Compare"}
          </button>
          <a className="button" href={`#/similar/${shoe.id}`}>Find similar shoes</a>
        </div>
      </header>

      <section aria-labelledby="fit-title" className="panel">
        <h3 id="fit-title">Score for your profile: {result.score === null ? "–" : `${Math.round(result.score)}/100`}</h3>
        {!result.ranked && result.score !== null && (
          <p className="hint">Not ranked in the results: only {Math.round(result.coverage * 100)} % of what matters to you is known.</p>
        )}
        <table className="table">
          <caption className="hint">How the score is made (points add up to the score; unknown values count as 5/10).</caption>
          <thead><tr><th scope="col">Term</th><th scope="col">Weight for you</th><th scope="col">Score /10</th><th scope="col">Points</th></tr></thead>
          <tbody>
            {result.terms.filter((t) => t.share > 0).sort((a, b) => b.points - a.points).map((t) => (
              <tr key={t.key}>
                <th scope="row">{TERM_LABEL[t.key]}</th>
                <td>{Math.round(t.share * 100)} %</td>
                <td>{t.value === null ? <span className="hint">unknown (5)</span> : t.value.toFixed(1)}</td>
                <td>{t.points.toFixed(1)}</td>
              </tr>
            ))}
            {result.buyerScore !== null && (
              <tr><th scope="row">Buyer rating</th><td>{Math.round(result.buyerShare * 100)} %</td><td>{result.buyerScore.toFixed(1)}</td><td>{result.buyerPoints.toFixed(1)}</td></tr>
            )}
          </tbody>
        </table>
      </section>

      <CriteriaSection shoe={shoe} />
      <TerrainSection shoe={shoe} />
      <SpecsSection shoe={shoe} />
      <ReviewsSection shoe={shoe} />
      <OffersSection shoe={shoe} />
      <ConfidenceSection shoe={shoe} buildDate={data.meta.build_date} />
    </article>
  );
}

function CriteriaSection({ shoe }: { shoe: Shoe }) {
  const values = Object.fromEntries(CRITERIA.map((c) => [c, shoe.criteria_scores[c].score_0_10])) as Record<Criterion, number | null>;
  return (
    <section aria-labelledby="criteria-title" className="panel">
      <h3 id="criteria-title">Criteria</h3>
      <div className="two-columns">
        <Radar series={[{ name: shoeName(shoe), values }]} title={`Criterion scores of the ${shoeName(shoe)}`} />
        <table className="table">
          <thead><tr><th scope="col">Criterion</th><th scope="col">Score</th><th scope="col">Based on</th></tr></thead>
          <tbody>
            {CRITERIA.map((c) => {
              const score = shoe.criteria_scores[c];
              return (
                <tr key={c}>
                  <th scope="row">{TERM_LABEL[c]}</th>
                  <td>{score.score_0_10 === null ? <span className="hint">unknown</span> : score.score_0_10.toFixed(1)}</td>
                  <td>
                    {score.provenance.length === 0 ? <span className="hint">no data</span> : (
                      <details>
                        <summary>{score.provenance.map((p) => sourceWord(p.source)).filter((v, i, a) => a.indexOf(v) === i).join(" + ")}</summary>
                        <ul className="provenance">
                          {score.provenance.map((p) => (
                            <li key={p.input}>
                              {Math.round(p.weight * 100)} % · {inputWord(p.input)}: {p.value} → {p.input_score_0_10.toFixed(1)}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function sourceWord(source: string): string {
  return { manufacturer: "specs", lab_measurement: "lab", retailer: "retailer specs", expert_reviews: "reviews", neutral_prior: "neutral (few reviews)" }[source] ?? source;
}
function inputWord(input: string): string {
  if (input === "expert_reviews") return "expert reviews";
  if (input === "neutral_prior") return "neutral value";
  const field = input.replace("specs.", "") as keyof typeof SPEC_LABEL;
  return SPEC_LABEL[field]?.[0] ?? input;
}

function TerrainSection({ shoe }: { shoe: Shoe }) {
  return (
    <section aria-labelledby="terrain-title" className="panel">
      <h3 id="terrain-title">Terrain</h3>
      <p className="hint">From specs only (lug depth is required). Reviews are not used here.</p>
      <ul className="bars">
        {TERRAINS.map((t) => {
          const v = shoe.terrain_scores[t].score_0_10;
          return (
            <li key={t}>
              <span className="bar-label">{TERRAIN_LABEL[t].name}</span>
              <span className="bar-track" aria-hidden="true"><span className="bar-fill" style={{ width: `${(v ?? 0) * 10}%` }} /></span>
              <span className="bar-value">{v === null ? "unknown" : `${v.toFixed(1)}/10`}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function SpecsSection({ shoe }: { shoe: Shoe }) {
  return (
    <section aria-labelledby="specs-title" className="panel">
      <h3 id="specs-title">Specs and their sources</h3>
      <table className="table specs">
        <tbody>
          {(Object.keys(SPEC_LABEL) as (keyof typeof SPEC_LABEL)[]).map((field) => {
            const spec = shoe.specs[field];
            const [label, unit] = SPEC_LABEL[field];
            const tier = shoe.specs.sources[field];
            return (
              <tr key={field}>
                <th scope="row">{label}</th>
                {spec.value === null ? (
                  <td colSpan={2}><span className="hint">Unknown — {spec.missing_reason}</span></td>
                ) : (
                  <>
                    <td>{formatValue(spec.value, unit)}{spec.note && <span className="hint"> ({spec.note})</span>}</td>
                    <td>
                      {spec.source_url ? <a href={spec.source_url} target="_blank" rel="noopener noreferrer">{spec.source_name}</a> : spec.source_name}
                      {tier && <span className="hint"> · {TIER_LABEL[tier]}</span>}
                      {spec.raw_snippet && <details><summary>Quote</summary><q className="quote">{spec.raw_snippet}</q></details>}
                    </td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function ReviewsSection({ shoe }: { shoe: Shoe }) {
  return (
    <section aria-labelledby="reviews-title" className="panel">
      <h3 id="reviews-title">Specialist reviews ({shoe.expert_reviews.length})</h3>
      {shoe.expert_reviews.length === 0 && <p className="hint">No specialist review found for this model.</p>}
      {shoe.expert_reviews.map((r) => (
        <div key={r.url} className="review">
          <p>
            <strong>{SOURCE_LABEL[r.source] ?? r.source}</strong> <span className="hint">· {day(r.date)}</span> ·{" "}
            <a href={r.url} target="_blank" rel="noopener noreferrer">Read the full review</a>
          </p>
          {r.conclusion_excerpt && <q className="quote">{r.conclusion_excerpt}</q>}
          {Object.keys(r.aspects).length > 0 && (
            <details>
              <summary>What our text analysis found ({Object.keys(r.aspects).length} criteria)</summary>
              <ul className="provenance">
                {(Object.entries(r.aspects) as [Criterion, { score_0_10: number; evidence_excerpt: string }][]).map(([c, a]) => (
                  <li key={c}><strong>{TERM_LABEL[c]} {a.score_0_10.toFixed(1)}</strong>: <q>{a.evidence_excerpt}</q></li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ))}
      <p className="hint">Excerpts are short quotes (30 words at most); the criterion scores come from an automatic text analysis that agrees with a careful reading about 6 times in 10 (see How it works).</p>
    </section>
  );
}

function OffersSection({ shoe }: { shoe: Shoe }) {
  const offers = [...shoe.retail].sort((a, b) => a.price_eur - b.price_eur);
  const b = shoe.buyer_rating;
  return (
    <section aria-labelledby="offers-title" className="panel">
      <h3 id="offers-title">Prices and buyer ratings</h3>
      <p>
        {b.bayesian_mean_0_5 === null
          ? "No buyer rating."
          : `Buyers rate it ${b.raw_mean_0_5?.toFixed(1)}/5 over ${b.review_count_total} reviews (adjusted for small samples: ${b.bayesian_mean_0_5.toFixed(2)}).`}
      </p>
      <table className="table">
        <thead><tr><th scope="col">Retailer</th><th scope="col">Price</th><th scope="col">Checked</th><th scope="col">Rating</th><th scope="col">Offer</th></tr></thead>
        <tbody>
          {offers.map((o) => (
            <tr key={o.url}>
              <td>{SOURCE_LABEL[o.retailer] ?? o.retailer}</td>
              <td>{euro(o.price_eur)}</td>
              <td>{day(o.price_date)}</td>
              <td>{o.rating === null ? "–" : `${o.rating.toFixed(1)}/5 (${o.review_count})`}</td>
              <td><a href={o.url} target="_blank" rel="noopener noreferrer">View</a></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">Listings include colours, genders and variants (e.g. GTX) of the same model.</p>
    </section>
  );
}

function ConfidenceSection({ shoe, buildDate }: { shoe: Shoe; buildDate: string }) {
  const missing = missingData(shoe);
  const age = priceAgeDays(shoe, new Date());
  const c = shoe.confidence;
  return (
    <section aria-labelledby="confidence-title" className="panel">
      <h3 id="confidence-title">Data confidence</h3>
      <p><ConfidenceBadge confidence={c} /></p>
      <ul>
        <li>Specs known: {Math.round(c.spec_completeness_0_1 * 100)} % (weighted)</li>
        <li>Specialist reviews: {c.expert_review_count} · buyer reviews: {c.buyer_review_count}</li>
        <li>Prices checked {age === null ? "never" : age === 0 ? "today" : `${age} day${age > 1 ? "s" : ""} ago`} (data built {day(buildDate)})</li>
      </ul>
      {c.reasons.length > 0 && (
        <>
          <h4>Why not higher</h4>
          <ul>{c.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        </>
      )}
      <h4>What is missing</h4>
      <ul>
        {missing.criteria.length > 0 && <li>No score for: {missing.criteria.map((k) => TERM_LABEL[k].toLowerCase()).join(", ")}</li>}
        {missing.terrains.length > 0 && <li>No terrain score for: {missing.terrains.map((t) => TERRAIN_LABEL[t].name.toLowerCase()).join(", ")}</li>}
        {missing.specs.length > 0 && <li>Unknown specs: {missing.specs.map((s) => SPEC_LABEL[s.field as keyof typeof SPEC_LABEL]?.[0].toLowerCase() ?? s.field).join(", ")}</li>}
        {missing.noExpertReview && <li>No specialist review</li>}
        {missing.noBuyerReview && <li>No buyer review</li>}
      </ul>
    </section>
  );
}
