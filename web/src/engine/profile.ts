// The runner profile and the hard filters: what the user enters in the form.

import type { Terrain, Width } from "./types";

export type ProfileGender = "men" | "women" | "unspecified";
export type FootWidth = Width | "unknown";
export type FootStrike = "heel" | "midfoot" | "forefoot" | "unknown";
export type PreferenceAxis = "cushioning_vs_ground_feel" | "stability_vs_agility" | "dynamic_vs_comfortable";
export const PREFERENCE_AXES: PreferenceAxis[] = [
  "cushioning_vs_ground_feel",
  "stability_vs_agility",
  "dynamic_vs_comfortable",
];

export interface Profile {
  gender: ProfileGender;
  weightKg: number;
  footWidth: FootWidth;
  footStrike: FootStrike;
  distanceKm: number;
  /** Selected terrains; none selected = all terrains equally (spec §5.4). */
  terrains: Terrain[];
  /** UI slider positions 0-100 (50 = no preference); spec §5.3 maps them to -1..+1. */
  sliders: Record<PreferenceAxis, number>;
}

export interface Filters {
  maxPriceEur: number | null;
  excludedBrands: string[];
  waterproof: "any" | "yes" | "no";
  dropMinMm: number | null;
  dropMaxMm: number | null;
  width: Width | "any";
  /** Only shoes sold in the runner's gender (or unisex); needs profile.gender. */
  genderMatch: boolean;
}

export const DEFAULT_PROFILE: Profile = {
  gender: "unspecified",
  weightKg: 70,
  footWidth: "standard",
  footStrike: "unknown",
  distanceKm: 21,
  terrains: [],
  sliders: { cushioning_vs_ground_feel: 50, stability_vs_agility: 50, dynamic_vs_comfortable: 50 },
};

export const DEFAULT_FILTERS: Filters = {
  maxPriceEur: null,
  excludedBrands: [],
  waterproof: "any",
  dropMinMm: null,
  dropMaxMm: null,
  width: "any",
  genderMatch: false,
};

/** Slider position 0-100 -> s in [-1, +1] (spec §5.3: s = (v - 50) / 50). */
export const sliderToS = (v: number): number => (v - 50) / 50;
