import { describe, expect, it } from "vitest";
import { DEFAULT_PROFILE, type Profile } from "./profile";
import { CONFIG } from "./testing";
import { computeWeights, largestComponent, loadIndex, terrainShares, TERMS } from "./weights";

const profile = (p: Partial<Profile> = {}): Profile => ({ ...DEFAULT_PROFILE, ...p });

describe("weights (spec §5)", () => {
  it("reproduces the worked example of §5.8", () => {
    const w = computeWeights(
      profile({
        weightKg: 80,
        distanceKm: 42,
        terrains: ["technical_rocky"],
        footStrike: "heel",
        footWidth: "standard",
        sliders: { cushioning_vs_ground_feel: 25, stability_vs_agility: 50, dynamic_vs_comfortable: 50 },
      }),
      CONFIG,
    );
    expect(w.load).toBeCloseTo(0.647, 3);
    const expected = {
      cushioning: 2.697, terrain: 2.0, protection: 1.924, stability: 1.753, grip: 1.5,
      durability: 1.024, fit_width: 0.994, lightness: 0.918, responsiveness: 0.912, drop_fit: 0.6,
    };
    for (const [term, value] of Object.entries(expected)) {
      expect(w.terms[term as keyof typeof expected].total, term).toBeCloseTo(value, 2);
    }
    const total = TERMS.reduce((s, k) => s + w.terms[k].total, 0);
    expect(total).toBeCloseTo(14.322, 2);
    expect(largestComponent(w.terms.protection)).toBe("base");
  });

  it("gives a heavier runner more weight on cushioning and durability, less on lightness", () => {
    const light = computeWeights(profile({ weightKg: 55 }), CONFIG).terms;
    const heavy = computeWeights(profile({ weightKg: 95 }), CONFIG).terms;
    expect(heavy.cushioning.total).toBeGreaterThan(light.cushioning.total);
    expect(heavy.durability.total).toBeGreaterThan(light.durability.total);
    expect(heavy.lightness.total).toBeLessThan(light.lightness.total);
  });

  it("is continuous in runner weight and distance (no jumps)", () => {
    for (const [a, b] of [[{ weightKg: 70 }, { weightKg: 70.1 }], [{ distanceKm: 21 }, { distanceKm: 21.1 }]]) {
      const wa = computeWeights(profile(a), CONFIG).terms;
      const wb = computeWeights(profile(b), CONFIG).terms;
      for (const k of TERMS) expect(Math.abs(wa[k].total - wb[k].total)).toBeLessThan(0.01);
    }
  });

  it("increases cushioning with distance, on a log scale", () => {
    const load = (d: number) => loadIndex(profile({ distanceKm: d, weightKg: 55 }), CONFIG);
    expect(load(20) - load(10)).toBeCloseTo(load(100) - load(50), 6);
    expect(load(100)).toBeGreaterThan(load(10));
  });

  it("maps the sliders to the poles they name", () => {
    const left = computeWeights(profile({ sliders: { ...DEFAULT_PROFILE.sliders, cushioning_vs_ground_feel: 0 } }), CONFIG).terms;
    const right = computeWeights(profile({ sliders: { ...DEFAULT_PROFILE.sliders, cushioning_vs_ground_feel: 100 } }), CONFIG).terms;
    const neutral = computeWeights(profile(), CONFIG).terms;
    expect(left.cushioning.preference).toBeCloseTo(1.5);
    expect(right.ground_feel.total).toBeCloseTo(1.5);
    expect(neutral.ground_feel.total).toBe(0);
    expect(neutral.agility.total).toBe(0);
  });

  it("shares terrains equally, all five when none is selected", () => {
    expect(Object.values(terrainShares([]))).toEqual([0.2, 0.2, 0.2, 0.2, 0.2]);
    const two = terrainShares(["muddy_soft", "wet_roots"]);
    expect(two.muddy_soft).toBe(0.5);
    expect(two.road_to_trail).toBe(0);
    const muddy = computeWeights(profile({ terrains: ["muddy_soft"] }), CONFIG).terms;
    expect(muddy.grip.terrain).toBeCloseTo(0.8);
  });

  it("adds foot strike and foot width boosts, and no drop weight for unknown strike", () => {
    const heel = computeWeights(profile({ footStrike: "heel" }), CONFIG);
    expect(heel.terms.drop_fit.total).toBeCloseTo(0.6);
    expect(heel.terms.cushioning.footStrike).toBeCloseTo(0.3);
    expect(computeWeights(profile({ footStrike: "unknown" }), CONFIG).terms.drop_fit.total).toBe(0);
    expect(computeWeights(profile({ footWidth: "wide" }), CONFIG).terms.fit_width.footWidth).toBeCloseTo(0.5);
  });

  it("gives a narrow foot no extra weight on fit_width, which rewards ROOMY shoes", () => {
    expect(computeWeights(profile({ footWidth: "narrow" }), CONFIG).terms.fit_width.footWidth).toBe(0);
  });
});
