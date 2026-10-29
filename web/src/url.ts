// Profile, filters and comparator kept in the URL query string, so a result can be shared.
// Only values that differ from the defaults are written, with short keys.

import {
  DEFAULT_FILTERS,
  DEFAULT_PROFILE,
  type Filters,
  type FootStrike,
  type FootWidth,
  type Profile,
  type ProfileGender,
} from "./engine/profile";
import { TERRAINS, type Terrain, type Width } from "./engine/types";

export interface AppState {
  profile: Profile;
  filters: Filters;
  compare: string[]; // shoe ids, at most 4
}

const GENDERS: ProfileGender[] = ["men", "women", "unspecified"];
const WIDTHS: FootWidth[] = ["narrow", "standard", "wide", "extra_wide", "unknown"];
const STRIKES: FootStrike[] = ["heel", "midfoot", "forefoot", "unknown"];
const SLIDER_KEYS = { s1: "cushioning_vs_ground_feel", s2: "stability_vs_agility", s3: "dynamic_vs_comfortable" } as const;

function numberParam(params: URLSearchParams, key: string, min: number, max: number): number | null {
  const raw = params.get(key);
  if (raw === null || raw === "") return null;
  const value = Number(raw);
  return Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : null;
}

const oneOf = <T extends string>(value: string | null, allowed: readonly T[], fallback: T): T =>
  allowed.includes(value as T) ? (value as T) : fallback;

const list = (params: URLSearchParams, key: string): string[] =>
  (params.get(key) ?? "").split(",").map((v) => v.trim()).filter(Boolean);

/** Read the state from a query string; anything invalid falls back to the default. */
export function decodeState(search: string): AppState {
  const q = new URLSearchParams(search);
  const sliders = { ...DEFAULT_PROFILE.sliders };
  for (const [key, axis] of Object.entries(SLIDER_KEYS)) sliders[axis] = numberParam(q, key, 0, 100) ?? sliders[axis];
  const profile: Profile = {
    gender: oneOf(q.get("g"), GENDERS, DEFAULT_PROFILE.gender),
    weightKg: numberParam(q, "kg", 35, 150) ?? DEFAULT_PROFILE.weightKg,
    footWidth: oneOf(q.get("fw"), WIDTHS, DEFAULT_PROFILE.footWidth),
    footStrike: oneOf(q.get("fs"), STRIKES, DEFAULT_PROFILE.footStrike),
    distanceKm: numberParam(q, "km", 1, 250) ?? DEFAULT_PROFILE.distanceKm,
    terrains: list(q, "t").filter((t): t is Terrain => (TERRAINS as readonly string[]).includes(t)),
    sliders,
  };
  const wp = q.get("wp");
  const filters: Filters = {
    maxPriceEur: numberParam(q, "pmax", 0, 10000),
    excludedBrands: list(q, "xb"),
    waterproof: wp === "y" ? "yes" : wp === "n" ? "no" : "any",
    dropMinMm: numberParam(q, "dmin", 0, 20),
    dropMaxMm: numberParam(q, "dmax", 0, 20),
    width: oneOf(q.get("w"), ["any", "narrow", "standard", "wide", "extra_wide"] as const, "any") as Width | "any",
    genderMatch: q.get("gm") === "1",
  };
  return { profile, filters, compare: list(q, "cmp").slice(0, 4) };
}

/** Write the state as a query string (without the leading "?"). */
export function encodeState(state: AppState): string {
  const q = new URLSearchParams();
  const { profile: p, filters: f } = state;
  const d = DEFAULT_PROFILE;
  if (p.gender !== d.gender) q.set("g", p.gender);
  if (p.weightKg !== d.weightKg) q.set("kg", String(p.weightKg));
  if (p.footWidth !== d.footWidth) q.set("fw", p.footWidth);
  if (p.footStrike !== d.footStrike) q.set("fs", p.footStrike);
  if (p.distanceKm !== d.distanceKm) q.set("km", String(p.distanceKm));
  if (p.terrains.length) q.set("t", p.terrains.join(","));
  for (const [key, axis] of Object.entries(SLIDER_KEYS)) {
    if (p.sliders[axis] !== d.sliders[axis]) q.set(key, String(p.sliders[axis]));
  }
  const df = DEFAULT_FILTERS;
  if (f.maxPriceEur !== df.maxPriceEur && f.maxPriceEur !== null) q.set("pmax", String(f.maxPriceEur));
  if (f.excludedBrands.length) q.set("xb", f.excludedBrands.join(","));
  if (f.waterproof !== "any") q.set("wp", f.waterproof === "yes" ? "y" : "n");
  if (f.dropMinMm !== null) q.set("dmin", String(f.dropMinMm));
  if (f.dropMaxMm !== null) q.set("dmax", String(f.dropMaxMm));
  if (f.width !== "any") q.set("w", f.width);
  if (f.genderMatch) q.set("gm", "1");
  if (state.compare.length) q.set("cmp", state.compare.join(","));
  return q.toString();
}
