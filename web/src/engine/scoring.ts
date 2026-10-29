// Final score 0-100 and its explanation (docs/scoring-spec.md §5.3-5.5 values, §6).

import { lowestPrice } from "./filters";
import { interp, weightedMean } from "./math";
import { CONFIDENCE_RANK } from "./confidence";
import { largestComponent, TERMS, type TermKey, type WeightComponent, type Weights } from "./weights";
import { CRITERIA, TERRAINS, type Criterion, type ScoringConfig, type Shoe } from "./types";

/** x_k: the 0-10 value of each term for one shoe (null = unknown). */
export function termValues(shoe: Shoe, weights: Weights, config: ScoringConfig): Record<TermKey, number | null> {
  const values = {} as Record<TermKey, number | null>;
  for (const c of CRITERIA) values[c] = shoe.criteria_scores[c].score_0_10;

  // Derived poles (§5.3): ground_feel = 10 - cushioning; agility mixes lightness and it.
  values.ground_feel = values.cushioning === null ? null : 10 - values.cushioning;
  const mix = config.profile.derived_scores.agility.mix as Record<string, number>;
  values.agility = weightedMean(
    Object.entries(mix).map(([term, weight]) => ({ value: values[term as TermKey], weight })),
  );

  // Terrain composite (§5.4): mean of the selected terrains' scores that are known.
  values.terrain = weightedMean(
    TERRAINS.map((t) => ({ value: shoe.terrain_scores[t].score_0_10, weight: weights.terrainShares[t] })),
  );

  // Drop fit (§5.5): bell curve around the target drop of the runner's foot strike.
  const drop = shoe.specs.drop_mm.value;
  values.drop_fit =
    drop === null ? null : 10 * Math.exp(-0.5 * ((drop - weights.dropTargetMm) / weights.dropSigmaMm) ** 2);
  return values;
}

export interface TermResult {
  key: TermKey;
  weight: number; // W_k
  value: number | null; // x_k (null = unknown)
  counted: number | null; // x̃_k: x_k, or the neutral value when unknown; null if W_k = 0
  share: number; // W_k / sum of W over the weighted terms (0 if W_k = 0)
  points: number; // contribution to the 0-100 score
}

export interface ScoreResult {
  shoe: Shoe;
  score: number | null; // 0-100, null if no weighted term is known
  fit: number | null; // 0-10
  coverage: number; // share of the weight whose value is known (§6.1)
  ranked: boolean; // coverage >= final.min_ranking_coverage (§6.3)
  buyerScore: number | null; // B, 0-10
  buyerShare: number; // lambda
  buyerPoints: number;
  terms: TermResult[];
  values: Record<TermKey, number | null>;
}

/** Score of one shoe for the given weights (§6.1). Points of the terms + buyer = score.
 *
 * A weighted term whose value is unknown counts as final.missing_term_value (neutral 5):
 * dropping it would re-weight the known terms, so a shoe whose weak point was never
 * measured would rank as if it had none (spec 0.3.0). */
export function scoreShoe(shoe: Shoe, weights: Weights, config: ScoringConfig): ScoreResult {
  const values = termValues(shoe, weights, config);
  const neutral: number = config.final.missing_term_value;
  const weighted = TERMS.filter((k) => weights.terms[k].total > 0);
  const known = weighted.filter((k) => values[k] !== null);
  const totalWeighted = weighted.reduce((s, k) => s + weights.terms[k].total, 0);
  const totalKnown = known.reduce((s, k) => s + weights.terms[k].total, 0);

  const bayesian = shoe.buyer_rating.bayesian_mean_0_5;
  const buyerScore = bayesian === null ? null : interp(bayesian, config.buyer_rating.score_anchors);
  const lambda = buyerScore === null ? 0 : config.final.buyer_share;

  const counted = (k: TermKey) => values[k] ?? neutral;
  const fit =
    known.length === 0
      ? null // nothing at all is known: no score rather than a score made of defaults
      : weighted.reduce((s, k) => s + weights.terms[k].total * counted(k), 0) / totalWeighted;
  const score = fit === null ? null : 10 * ((1 - lambda) * fit + lambda * (buyerScore ?? 0));
  const coverage = totalWeighted === 0 ? 0 : totalKnown / totalWeighted;

  const terms: TermResult[] = TERMS.map((key) => {
    const weight = weights.terms[key].total;
    const share = weight > 0 && fit !== null ? weight / totalWeighted : 0;
    return {
      key,
      weight,
      value: values[key],
      counted: weight > 0 ? counted(key) : null,
      share,
      points: share > 0 ? 10 * (1 - lambda) * share * counted(key) : 0,
    };
  });
  return {
    shoe,
    score,
    fit,
    coverage,
    ranked: score !== null && coverage >= config.final.min_ranking_coverage,
    buyerScore,
    buyerShare: lambda,
    buyerPoints: buyerScore === null || fit === null ? 0 : 10 * lambda * buyerScore,
    terms,
    values,
  };
}

// ---------------------------------------------------------------------------
// Explanation (§6.5)
// ---------------------------------------------------------------------------

export interface Quote {
  text: string;
  source: string;
  url: string;
  date: string | null;
}

export interface Point {
  key: TermKey;
  value: number;
  label: string; // excellent / good / average / weak / poor
  weightShare: number; // share of the weight among the terms used
  because: WeightComponent;
  advantage: number; // a_k = share_k * (x_k - mean_k)
  quote: Quote | null;
}

export interface Explanation {
  reasons: Point[];
  drawbacks: Point[];
  /** Terms that would weigh at least explanation.missing_data_min_weight_share but are unknown. */
  missing: { key: TermKey; weightShare: number }[];
}

/** Mean of each term over the candidates (shoes that passed the filters), or 5 (§6.5). */
export function candidateMeans(results: ScoreResult[], config: ScoringConfig): Record<TermKey, number> {
  const means = {} as Record<TermKey, number>;
  for (const key of TERMS) {
    const known = results.map((r) => r.values[key]).filter((v): v is number => v !== null);
    means[key] =
      known.length < config.explanation.min_candidates_for_mean
        ? 5
        : known.reduce((s, v) => s + v, 0) / known.length;
  }
  return means;
}

export function scoreLabel(value: number, config: ScoringConfig): string {
  const bands = config.explanation.score_labels as [number, string][];
  return (bands.find(([threshold]) => value >= threshold) ?? bands[bands.length - 1])[1];
}

/** Evidence excerpt of the review with the highest (best=true) or lowest aspect score. */
export function aspectQuote(shoe: Shoe, criterion: Criterion, best: boolean): Quote | null {
  let chosen: Quote | null = null;
  let chosenScore = best ? -Infinity : Infinity;
  for (const review of shoe.expert_reviews) {
    const aspect = review.aspects[criterion];
    if (!aspect) continue;
    if (best ? aspect.score_0_10 > chosenScore : aspect.score_0_10 < chosenScore) {
      chosenScore = aspect.score_0_10;
      chosen = { text: aspect.evidence_excerpt, source: review.source, url: review.url, date: review.date };
    }
  }
  return chosen;
}

export function explain(
  result: ScoreResult,
  weights: Weights,
  means: Record<TermKey, number>,
  config: ScoringConfig,
): Explanation {
  const e = config.explanation;
  // Reasons and drawbacks use known values only; unknown ones go to `missing`.
  const points: Point[] = result.terms
    .filter((t) => t.share > 0 && t.value !== null)
    .map((t) => ({
      key: t.key,
      value: t.value as number,
      label: scoreLabel(t.value as number, config),
      weightShare: t.share,
      because: largestComponent(weights.terms[t.key]),
      advantage: t.share * ((t.value as number) - means[t.key]),
      quote: null,
    }));
  const isCriterion = (k: TermKey): k is Criterion => (CRITERIA as readonly string[]).includes(k);

  const reasons = points
    .filter((p) => p.advantage > 0 && p.value >= e.reason_min_score)
    .sort((a, b) => b.advantage - a.advantage)
    .slice(0, e.max_reasons)
    .map((p) => ({ ...p, quote: isCriterion(p.key) ? aspectQuote(result.shoe, p.key, true) : null }));
  const drawbacks = points
    .filter((p) => p.advantage < 0 && p.value <= e.drawback_max_score)
    .sort((a, b) => a.advantage - b.advantage)
    .slice(0, e.max_drawbacks)
    .map((p) => ({ ...p, quote: isCriterion(p.key) ? aspectQuote(result.shoe, p.key, false) : null }));

  const totalWeighted = TERMS.reduce((s, k) => s + weights.terms[k].total, 0);
  const missing = result.terms
    .filter((t) => t.weight > 0 && t.value === null)
    .map((t) => ({ key: t.key, weightShare: t.weight / totalWeighted }))
    .filter((m) => m.weightShare >= e.missing_data_min_weight_share)
    .sort((a, b) => b.weightShare - a.weightShare);
  return { reasons, drawbacks, missing };
}

// ---------------------------------------------------------------------------
// Ranking (§6.3-6.4)
// ---------------------------------------------------------------------------

export interface RankedShoe extends ScoreResult {
  explanation: Explanation;
}

export interface Ranking {
  ranked: RankedShoe[];
  /** Shoes that passed the filters but whose known data covers too little weight (§6.3). */
  notEnoughData: RankedShoe[];
}

/** Sort by rounded score, then confidence, then coverage, then lower price (§6.4). */
export function compareResults(a: ScoreResult, b: ScoreResult): number {
  const byScore = Math.round(b.score ?? -1) - Math.round(a.score ?? -1);
  if (byScore !== 0) return byScore;
  const byConfidence = CONFIDENCE_RANK[b.shoe.confidence.level] - CONFIDENCE_RANK[a.shoe.confidence.level];
  if (byConfidence !== 0) return byConfidence;
  if (b.coverage !== a.coverage) return b.coverage - a.coverage;
  return (lowestPrice(a.shoe) ?? Infinity) - (lowestPrice(b.shoe) ?? Infinity);
}

/** Score, explain and rank the candidates (the shoes that passed the hard filters). */
export function rankShoes(candidates: Shoe[], weights: Weights, config: ScoringConfig): Ranking {
  const results = candidates.map((shoe) => scoreShoe(shoe, weights, config));
  const means = candidateMeans(results, config);
  const explained = results.map((r) => ({ ...r, explanation: explain(r, weights, means, config) }));
  return {
    ranked: explained.filter((r) => r.ranked).sort(compareResults),
    notEnoughData: explained
      .filter((r) => !r.ranked)
      .sort((a, b) => b.coverage - a.coverage || a.shoe.id.localeCompare(b.shoe.id)),
  };
}
