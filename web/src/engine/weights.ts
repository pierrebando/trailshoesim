// Runner profile -> weight of each term of the final score (docs/scoring-spec.md §5).
//
// Every layer is a continuous function of the profile: a runner of 70 kg and one of 71 kg
// get almost the same weights. Each layer is kept apart so the explanation can say WHY a
// weight is high (§5.7).

import { clamp, smoothstep } from "./math";
import { PREFERENCE_AXES, sliderToS, type Profile } from "./profile";
import { CRITERIA, TERRAINS, type Criterion, type ScoringConfig, type Terrain } from "./types";

/** The terms of the final score: 8 criteria, 2 derived poles, terrain, drop fit (§5). */
export type TermKey = Criterion | "ground_feel" | "agility" | "terrain" | "drop_fit";
export const TERMS: TermKey[] = [...CRITERIA, "ground_feel", "agility", "terrain", "drop_fit"];

/** Where a weight comes from; `total` is their sum (W_k of §5.7). */
export interface WeightParts {
  base: number; // load index: runner weight and distance (§5.2)
  preference: number; // sliders (§5.3)
  terrain: number; // selected terrains (§5.4)
  footStrike: number; // §5.5
  footWidth: number; // §5.6
  total: number;
}
export type WeightComponent = Exclude<keyof WeightParts, "total">;

export interface Weights {
  load: number;
  terms: Record<TermKey, WeightParts>;
  /** Share of each terrain in the composite term (they sum to 1). */
  terrainShares: Record<Terrain, number>;
  /** Drop-fit bell curve of the runner's foot strike (§5.5). */
  dropTargetMm: number;
  dropSigmaMm: number;
}

/** Load index between 0 (light runner, short runs) and 1 (heavy runner, ultras) (§5.1). */
export function loadIndex(profile: Profile, config: ScoringConfig): number {
  const { runner_weight_kg: rw, distance_km: dk, load_mix: mix } = config.profile;
  const weightNorm = smoothstep((profile.weightKg - rw.low) / (rw.high - rw.low));
  // Log scale: 10 -> 20 km changes needs about as much as 50 -> 100 km.
  const distance = Math.max(profile.distanceKm, Number.MIN_VALUE);
  const distanceNorm = clamp(Math.log(distance / dk.low) / Math.log(dk.high / dk.low));
  return mix.runner_weight * weightNorm + mix.distance * distanceNorm;
}

/** Equal shares over the selected terrains; all five at 0.2 if none is selected (§5.4). */
export function terrainShares(selected: Terrain[]): Record<Terrain, number> {
  const chosen = selected.length > 0 ? selected : [...TERRAINS];
  return Object.fromEntries(
    TERRAINS.map((t) => [t, chosen.includes(t) ? 1 / chosen.length : 0]),
  ) as Record<Terrain, number>;
}

export function computeWeights(profile: Profile, config: ScoringConfig): Weights {
  const p = config.profile;
  const load = loadIndex(profile, config);
  const parts = Object.fromEntries(
    TERMS.map((k) => [k, { base: 0, preference: 0, terrain: 0, footStrike: 0, footWidth: 0, total: 0 }]),
  ) as Record<TermKey, WeightParts>;

  for (const c of CRITERIA) {
    const [low, high] = p.base_weights[c];
    parts[c].base = low + (high - low) * load;
  }

  const strength = p.preference_axes.strength;
  for (const axis of PREFERENCE_AXES) {
    const s = sliderToS(profile.sliders[axis]);
    const { left, right } = p.preference_axes[axis];
    for (const [term, w] of Object.entries(left) as [TermKey, number][]) {
      parts[term].preference += strength * Math.max(-s, 0) * w;
    }
    for (const [term, w] of Object.entries(right) as [TermKey, number][]) {
      parts[term].preference += strength * Math.max(s, 0) * w;
    }
  }

  const shares = terrainShares(profile.terrains);
  for (const t of TERRAINS) {
    for (const [c, boost] of Object.entries(p.terrain.criterion_boosts[t] ?? {}) as [Criterion, number][]) {
      parts[c].terrain += shares[t] * boost;
    }
  }
  parts.terrain.terrain = p.terrain.composite_weight;

  const strike = p.foot_strike[profile.footStrike];
  parts.drop_fit.footStrike = strike.weight;
  for (const [c, boost] of Object.entries(strike.criterion_boosts) as [Criterion, number][]) {
    parts[c].footStrike += boost;
  }

  parts.fit_width.footWidth = p.foot_width_boosts[profile.footWidth];

  for (const k of TERMS) {
    const w = parts[k];
    w.total = w.base + w.preference + w.terrain + w.footStrike + w.footWidth;
  }
  return {
    load,
    terms: parts,
    terrainShares: shares,
    dropTargetMm: strike.target_drop_mm,
    dropSigmaMm: strike.sigma_mm,
  };
}

/** The component that contributes most to a term's weight (for "Weighted x% because..."). */
export function largestComponent(parts: WeightParts): WeightComponent {
  const components: WeightComponent[] = ["base", "preference", "terrain", "footStrike", "footWidth"];
  return components.reduce((best, c) => (parts[c] > parts[best] ? c : best), components[0]);
}
