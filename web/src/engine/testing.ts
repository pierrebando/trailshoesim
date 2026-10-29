// Test helpers: the real scoring constants and fictional shoes built in one line.
// (Not a test file itself; imported by the *.test.ts files.)

import scoringConfig from "../../../data/processed/scoring_config.json";
import { CRITERIA, TERRAINS, type Criterion, type ScoringConfig, type Shoe, type SourcedValue, type Terrain } from "./types";

export const CONFIG = scoringConfig as ScoringConfig;

function sourced<T>(value: T | null): SourcedValue<T> {
  return value === null
    ? { value: null, source_name: null, source_url: null, retrieved_at: null, missing_reason: "fictional: not given", note: null, raw_snippet: null }
    : { value, source_name: "fictional", source_url: "https://example.org", retrieved_at: "2026-10-28", missing_reason: null, note: null, raw_snippet: String(value) };
}

export interface FictionalShoe {
  id?: string;
  brand?: string;
  model?: string;
  version?: string | null;
  criteria?: Partial<Record<Criterion, number | null>>;
  terrain?: Partial<Record<Terrain, number | null>>;
  price?: number;
  priceDate?: string;
  drop?: number | null;
  stackHeel?: number | null;
  lugDepth?: number | null;
  waterproof?: boolean | null;
  widths?: ("narrow" | "standard" | "wide" | "extra_wide")[] | null;
  genders?: ("men" | "women" | "unisex")[];
  buyer?: number | null; // Bayesian mean 0-5
  confidence?: "high" | "medium" | "low";
}

/** A fictional shoe: every criterion and terrain 5/10 unless given. */
export function makeShoe(f: FictionalShoe = {}): Shoe {
  const id = f.id ?? "fictional-shoe";
  const criterion = (c: Criterion) => {
    const v = f.criteria?.[c] === undefined ? 5 : f.criteria[c];
    return { score_0_10: v ?? null, spec_score_0_10: v ?? null, expert_score_0_10: null, spec_input_coverage: 1, expert_review_count: 0, inputs_used: [], inputs_missing: [], provenance: [] };
  };
  const terrain = (t: Terrain) => {
    const v = f.terrain?.[t] === undefined ? 5 : f.terrain[t];
    return { score_0_10: v ?? null, inputs_used: [], inputs_missing: [], provenance: [] };
  };
  return {
    id,
    brand: f.brand ?? "Fictional",
    model: f.model ?? id,
    version: f.version ?? null,
    category: "trail",
    newer_version_id: null,
    gender_variants: f.genders ?? ["men", "women"],
    retail: [{ retailer: "tradeinn", url: "https://example.org/shop", price_eur: f.price ?? 120, price_date: f.priceDate ?? "2026-10-28", rating: null, review_count: null }],
    specs: {
      weight_g: sourced<number>(null),
      weight_women_g: sourced<number>(null),
      stack_heel_mm: sourced(f.stackHeel === undefined ? 30 : f.stackHeel),
      stack_forefoot_mm: sourced<number>(null),
      drop_mm: sourced(f.drop === undefined ? 6 : f.drop),
      lug_depth_mm: sourced(f.lugDepth === undefined ? 4 : f.lugDepth),
      lug_spacing: sourced<string>(null),
      platform_width_heel_mm: sourced<number>(null),
      platform_width_forefoot_mm: sourced<number>(null),
      midsole_softness_ac: sourced<number>(null),
      energy_return_forefoot_pct: sourced<number>(null),
      midsole_foam: sourced<string>(null),
      plate: sourced<string>(null),
      outsole_rubber: sourced<string>(null),
      waterproof: sourced(f.waterproof === undefined ? null : f.waterproof),
      upper_notes: sourced<string>(null),
      width_options: sourced(f.widths === undefined ? null : f.widths),
      fit_width_tag: sourced<string>(null),
      sources: {},
    },
    expert_reviews: [],
    buyer_rating: { review_count_total: f.buyer == null ? 0 : 50, raw_mean_0_5: f.buyer ?? null, bayesian_mean_0_5: f.buyer ?? null },
    criteria_scores: Object.fromEntries(CRITERIA.map((c) => [c, criterion(c)])) as unknown as Shoe["criteria_scores"],
    terrain_scores: Object.fromEntries(TERRAINS.map((t) => [t, terrain(t)])) as unknown as Shoe["terrain_scores"],
    confidence: { spec_completeness_0_1: 0.5, expert_review_count: 0, buyer_review_count: 0, price_age_days: 0, level: f.confidence ?? "medium", reasons: [] },
  };
}
