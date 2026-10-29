import { describe, expect, it } from "vitest";
import { DEFAULT_FILTERS, DEFAULT_PROFILE } from "./engine/profile";
import { decodeState, encodeState, type AppState } from "./url";

describe("URL state", () => {
  it("writes nothing for the defaults", () => {
    expect(encodeState({ profile: DEFAULT_PROFILE, filters: DEFAULT_FILTERS, compare: [] })).toBe("");
  });

  it("round-trips a full state", () => {
    const state: AppState = {
      profile: {
        ...DEFAULT_PROFILE,
        gender: "women",
        weightKg: 58,
        footStrike: "forefoot",
        distanceKm: 50,
        terrains: ["technical_rocky", "wet_roots"],
        sliders: { cushioning_vs_ground_feel: 80, stability_vs_agility: 50, dynamic_vs_comfortable: 20 },
      },
      filters: { ...DEFAULT_FILTERS, maxPriceEur: 150, excludedBrands: ["Hoka", "La Sportiva"], dropMaxMm: 6, genderMatch: true },
      compare: ["a-1", "b-2"],
    };
    expect(decodeState(encodeState(state))).toEqual(state);
  });

  it("ignores invalid values", () => {
    const state = decodeState("kg=abc&fs=tiptoe&t=moon,muddy_soft&s1=500");
    expect(state.profile.weightKg).toBe(DEFAULT_PROFILE.weightKg);
    expect(state.profile.footStrike).toBe("unknown");
    expect(state.profile.terrains).toEqual(["muddy_soft"]);
    expect(state.profile.sliders.cushioning_vs_ground_feel).toBe(100);
  });
});
