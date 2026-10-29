// Types of the data the app reads. They mirror schema/shoe.schema.json and
// schema/meta.schema.json (generated from pipeline/models.py); only the fields the app
// uses are listed.

export const CRITERIA = [
  "cushioning",
  "protection",
  "grip",
  "stability",
  "responsiveness",
  "lightness",
  "durability",
  "fit_width",
] as const;
export type Criterion = (typeof CRITERIA)[number];

export const TERRAINS = [
  "road_to_trail",
  "groomed_mixed",
  "technical_rocky",
  "muddy_soft",
  "wet_roots",
] as const;
export type Terrain = (typeof TERRAINS)[number];

export type Gender = "men" | "women" | "unisex";
export type Width = "narrow" | "standard" | "wide" | "extra_wide";
export type ConfidenceLevel = "high" | "medium" | "low";

export interface SourcedValue<T> {
  value: T | null;
  source_name: string | null;
  source_url: string | null;
  retrieved_at: string | null;
  missing_reason: string | null;
  note: string | null;
  raw_snippet: string | null;
}

export interface Specs {
  weight_g: SourcedValue<number>;
  weight_women_g: SourcedValue<number>;
  stack_heel_mm: SourcedValue<number>;
  stack_forefoot_mm: SourcedValue<number>;
  drop_mm: SourcedValue<number>;
  lug_depth_mm: SourcedValue<number>;
  lug_spacing: SourcedValue<string>;
  platform_width_heel_mm: SourcedValue<number>;
  platform_width_forefoot_mm: SourcedValue<number>;
  midsole_foam: SourcedValue<string>;
  plate: SourcedValue<string>;
  outsole_rubber: SourcedValue<string>;
  waterproof: SourcedValue<boolean>;
  upper_notes: SourcedValue<string>;
  width_options: SourcedValue<Width[]>;
  sources: Record<string, "manufacturer" | "lab_measurement" | "retailer">;
}

export interface RetailOffer {
  retailer: string;
  url: string;
  price_eur: number;
  price_date: string;
  rating: number | null;
  review_count: number | null;
}

export interface AspectAssessment {
  score_0_10: number;
  evidence_excerpt: string;
  mention_count: number;
}

export interface ExpertReview {
  source: string;
  url: string;
  date: string | null;
  language: string | null;
  conclusion_excerpt: string | null;
  aspects: Partial<Record<Criterion, AspectAssessment>>;
}

export interface ScoreInput {
  input: string;
  source: string;
  value: string;
  input_score_0_10: number;
  weight: number;
}

export interface CriterionScore {
  score_0_10: number | null;
  spec_score_0_10: number | null;
  expert_score_0_10: number | null;
  spec_input_coverage: number;
  expert_review_count: number;
  inputs_used: string[];
  inputs_missing: string[];
  provenance: ScoreInput[];
}

export interface TerrainScore {
  score_0_10: number | null;
  inputs_used: string[];
  inputs_missing: string[];
  provenance: ScoreInput[];
}

export interface Confidence {
  spec_completeness_0_1: number;
  expert_review_count: number;
  buyer_review_count: number;
  price_age_days: number | null;
  level: ConfidenceLevel;
  reasons: string[];
}

export interface Shoe {
  id: string;
  brand: string;
  model: string;
  version: string | null;
  category: "trail" | "gravel";
  newer_version_id: string | null;
  gender_variants: Gender[];
  retail: RetailOffer[];
  specs: Specs;
  expert_reviews: ExpertReview[];
  buyer_rating: {
    review_count_total: number;
    raw_mean_0_5: number | null;
    bayesian_mean_0_5: number | null;
  };
  criteria_scores: Record<Criterion, CriterionScore>;
  terrain_scores: Record<Terrain, TerrainScore>;
  confidence: Confidence;
}

export interface Catalog {
  generated_at: string;
  scoring_config_version: string;
  shoes: Shoe[];
}

export interface Meta {
  build_date: string;
  pipeline_version: string;
  scoring_config_version: string;
  aspects_config_version: string;
  shoe_count: number;
  brand_count: number;
  offer_count: number;
  expert_review_count: number;
  confidence_counts: Record<ConfidenceLevel, number>;
  price_date_min: string;
  price_date_max: string;
  retailers: string[];
  review_sources: string[];
}

/** pipeline/config/scoring.yaml as JSON (data/processed/scoring_config.json). Loosely
 * typed on purpose: the engine reads the paths named in docs/scoring-spec.md §9. */
export type ScoringConfig = Record<string, any>;
