// "I like this model": shoes similar to a reference shoe (docs/scoring-spec.md §7).

import { clamp, percentile } from "./math";
import { CRITERIA, TERRAINS, type ScoringConfig, type Shoe } from "./types";

export type Feature =
  | (typeof CRITERIA)[number]
  | (typeof TERRAINS)[number]
  | "drop_mm"
  | "stack_heel_mm"
  | "lug_depth_mm"
  | "waterproof";

const NUMERIC_FEATURES = ["drop_mm", "stack_heel_mm", "lug_depth_mm"] as const;
type NumericFeature = (typeof NUMERIC_FEATURES)[number];

/** P5 / P95 of each numeric spec over the WHOLE catalogue (robust min-max scaling). */
export type Normalisation = Record<NumericFeature, { low: number; high: number } | null>;

export function catalogueNormalisation(catalogue: Shoe[], config: ScoringConfig): Normalisation {
  const { lower_percentile: lo, upper_percentile: hi } = config.similarity.numeric_normalisation;
  const result = {} as Normalisation;
  for (const f of NUMERIC_FEATURES) {
    const values = catalogue.map((s) => s.specs[f].value).filter((v): v is number => v !== null);
    result[f] = values.length >= 2 ? { low: percentile(values, lo), high: percentile(values, hi) } : null;
  }
  return result;
}

/** The feature vector of a shoe, every feature between 0 and 1 (null = unknown). */
export function featureVector(shoe: Shoe, norm: Normalisation): Record<Feature, number | null> {
  const vector = {} as Record<Feature, number | null>;
  for (const c of CRITERIA) {
    const v = shoe.criteria_scores[c].score_0_10;
    vector[c] = v === null ? null : v / 10;
  }
  for (const t of TERRAINS) {
    const v = shoe.terrain_scores[t].score_0_10;
    vector[t] = v === null ? null : v / 10;
  }
  for (const f of NUMERIC_FEATURES) {
    const v = shoe.specs[f].value;
    const range = norm[f];
    vector[f] =
      v === null || range === null || range.high === range.low
        ? null
        : clamp((v - range.low) / (range.high - range.low));
  }
  const waterproof = shoe.specs.waterproof.value;
  vector.waterproof = waterproof === null ? null : waterproof ? 1 : 0;
  return vector;
}

export interface FeatureDifference {
  feature: Feature;
  /** Candidate minus reference, on the 0-1 scale (positive = candidate has more). */
  difference: number;
  weighted: number; // w_f * difference^2, what the distance adds up
}

export interface Similarity {
  shoe: Shoe;
  similarity: number | null; // 0-100, null when not comparable
  sharedWeightShare: number;
  closest: FeatureDifference[];
  furthest: FeatureDifference[];
  otherVersion: boolean; // same brand and model, another version
}

/** Similarity of `candidate` to `reference` (§7): 100 * (1 - weighted RMS distance). */
export function similarity(
  reference: Shoe,
  candidate: Shoe,
  norm: Normalisation,
  config: ScoringConfig,
): Similarity {
  const weights = config.similarity.feature_weights as Record<Feature, number>;
  const r = featureVector(reference, norm);
  const s = featureVector(candidate, norm);
  const total = Object.values(weights).reduce((sum, w) => sum + w, 0);
  const shared = (Object.keys(weights) as Feature[]).filter((f) => r[f] !== null && s[f] !== null);
  const sharedWeight = shared.reduce((sum, f) => sum + weights[f], 0);
  const differences = shared.map((f) => {
    const difference = (s[f] as number) - (r[f] as number);
    return { feature: f, difference, weighted: weights[f] * difference * difference };
  });
  const comparable = sharedWeight / total >= config.similarity.min_shared_weight_share;
  const distance = comparable
    ? Math.sqrt(differences.reduce((sum, d) => sum + d.weighted, 0) / sharedWeight)
    : null;
  const byCloseness = [...differences].sort((a, b) => a.weighted - b.weighted);
  return {
    shoe: candidate,
    similarity: distance === null ? null : 100 * (1 - distance),
    sharedWeightShare: sharedWeight / total,
    closest: byCloseness.slice(0, 3),
    furthest: byCloseness.filter((d) => d.difference !== 0).reverse().slice(0, 2),
    otherVersion:
      candidate.id !== reference.id &&
      candidate.brand === reference.brand &&
      candidate.model === reference.model,
  };
}

/** The most similar candidates (the shoes that passed the same hard filters). */
export function findSimilar(
  reference: Shoe,
  candidates: Shoe[],
  catalogue: Shoe[],
  config: ScoringConfig,
): { similar: Similarity[]; notComparable: number } {
  const norm = catalogueNormalisation(catalogue, config);
  const all = candidates.filter((c) => c.id !== reference.id).map((c) => similarity(reference, c, norm, config));
  const comparable = all.filter((x) => x.similarity !== null);
  comparable.sort((a, b) => (b.similarity as number) - (a.similarity as number) || a.shoe.id.localeCompare(b.shoe.id));
  return {
    similar: comparable.slice(0, config.similarity.max_results),
    notComparable: all.length - comparable.length,
  };
}
