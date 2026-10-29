// Confidence (docs/scoring-spec.md §8). The level and its reasons are computed offline by
// the pipeline; the browser only recomputes the price age on the day of viewing and lists
// what is missing, for the model page.

import { CRITERIA, TERRAINS, type ConfidenceLevel, type Criterion, type Shoe, type Specs, type Terrain } from "./types";

export const CONFIDENCE_RANK: Record<ConfidenceLevel, number> = { low: 0, medium: 1, high: 2 };

const DAY_MS = 24 * 60 * 60 * 1000;

/** Most recent price date of a shoe (ISO date), or null. */
export function latestPriceDate(shoe: Shoe): string | null {
  const dates = shoe.retail.map((o) => o.price_date).sort();
  return dates.length ? dates[dates.length - 1] : null;
}

/** Days between the freshest price and `today` (the build date if you pass it). */
export function priceAgeDays(shoe: Shoe, today: Date): number | null {
  const latest = latestPriceDate(shoe);
  if (latest === null) return null;
  const start = Date.parse(`${latest}T00:00:00Z`); // price dates are calendar days (UTC)
  const end = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return Math.max(0, Math.round((end - start) / DAY_MS));
}

export interface MissingData {
  specs: { field: keyof Specs; reason: string }[];
  criteria: Criterion[];
  terrains: Terrain[];
  noExpertReview: boolean;
  noBuyerReview: boolean;
}

/** Everything the model page should list as unknown, with the pipeline's reasons. */
export function missingData(shoe: Shoe): MissingData {
  const specs: MissingData["specs"] = [];
  for (const [field, value] of Object.entries(shoe.specs) as [keyof Specs, Specs[keyof Specs]][]) {
    if (field === "sources") continue;
    const sourced = value as { value: unknown; missing_reason: string | null };
    if (sourced.value === null) specs.push({ field, reason: sourced.missing_reason ?? "unknown" });
  }
  return {
    specs,
    criteria: CRITERIA.filter((c) => shoe.criteria_scores[c].score_0_10 === null),
    terrains: TERRAINS.filter((t) => shoe.terrain_scores[t].score_0_10 === null),
    noExpertReview: shoe.expert_reviews.length === 0,
    noBuyerReview: shoe.confidence.buyer_review_count === 0,
  };
}
