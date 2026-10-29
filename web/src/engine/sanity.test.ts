// Behaviour checks on the REAL catalogue (data/processed/shoes.json), not only on
// fictional shoes: weights move the right way, every filter removes exactly what it
// should, explanations add up, similarity respects the filters.

import { describe, expect, it } from "vitest";
import catalogJson from "../../../data/processed/shoes.json";
import { applyFilters, lowestPrice } from "./filters";
import { DEFAULT_FILTERS, DEFAULT_PROFILE, type Filters, type Profile } from "./profile";
import { rankShoes } from "./scoring";
import { catalogueNormalisation, similarity, similarToModel } from "./similarity";
import { CONFIG } from "./testing";
import type { Catalog, Shoe } from "./types";
import { computeWeights, TERMS } from "./weights";

const SHOES = (catalogJson as unknown as Catalog).shoes;
const profile = (p: Partial<Profile> = {}): Profile => ({ ...DEFAULT_PROFILE, ...p });
const filters = (f: Partial<Filters>): Filters => ({ ...DEFAULT_FILTERS, ...f });
const ids = (shoes: Shoe[]) => shoes.map((s) => s.id).sort();

function nonDecreasing(values: number[]): boolean {
  return values.every((v, i) => i === 0 || v >= values[i - 1] - 1e-12);
}

describe("weights move the right way (spec §5)", () => {
  const weights = Array.from({ length: 81 }, (_, i) => 40 + i); // 40..120 kg
  const distances = [1, 3, 5, 8, 10, 15, 21, 30, 42, 50, 80, 100, 160, 250];

  it("a heavier runner never lowers the weight of cushioning, durability, stability or protection", () => {
    for (const term of ["cushioning", "durability", "stability", "protection"] as const) {
      const w = weights.map((kg) => computeWeights(profile({ weightKg: kg }), CONFIG).terms[term].total);
      expect(nonDecreasing(w), term).toBe(true);
    }
  });

  it("a longer distance never lowers the weight of durability or protection", () => {
    for (const term of ["durability", "protection", "cushioning"] as const) {
      const w = distances.map((km) => computeWeights(profile({ distanceKm: km }), CONFIG).terms[term].total);
      expect(nonDecreasing(w), term).toBe(true);
    }
  });
});

describe("each hard filter removes exactly what it should (spec §1), on the real catalogue", () => {
  const passed = (f: Partial<Filters>, p: Partial<Profile> = {}) => ids(applyFilters(SHOES, filters(f), profile(p)).passed);

  it("max price", () => {
    expect(passed({ maxPriceEur: 100 })).toEqual(ids(SHOES.filter((s) => (lowestPrice(s) ?? Infinity) <= 100)));
  });
  it("excluded brands", () => {
    expect(passed({ excludedBrands: ["Salomon", "la sportiva"] })).toEqual(
      ids(SHOES.filter((s) => !["salomon", "la sportiva"].includes(s.brand.toLowerCase()))),
    );
  });
  it("waterproof yes / no (unknown fails)", () => {
    expect(passed({ waterproof: "yes" })).toEqual(ids(SHOES.filter((s) => s.specs.waterproof.value === true)));
    expect(passed({ waterproof: "no" })).toEqual(ids(SHOES.filter((s) => s.specs.waterproof.value === false)));
  });
  it("drop range (unknown fails)", () => {
    expect(passed({ dropMinMm: 4, dropMaxMm: 8 })).toEqual(
      ids(SHOES.filter((s) => s.specs.drop_mm.value !== null && s.specs.drop_mm.value >= 4 && s.specs.drop_mm.value <= 8)),
    );
  });
  it("width (unknown fails)", () => {
    expect(passed({ width: "wide" })).toEqual(ids(SHOES.filter((s) => s.specs.width_options.value?.includes("wide"))));
  });
  it("gender: the runner's gender or unisex", () => {
    expect(passed({ genderMatch: true }, { gender: "women" })).toEqual(
      ids(SHOES.filter((s) => s.gender_variants.includes("women") || s.gender_variants.includes("unisex"))),
    );
  });
});

describe("explanations (spec §6.5), on the real catalogue", () => {
  const profiles = [profile(), profile({ weightKg: 90, distanceKm: 80, terrains: ["technical_rocky"], footStrike: "heel" })];

  it("the points of every term plus the buyer term add up to the score", () => {
    for (const p of profiles) {
      for (const r of rankShoes(SHOES, computeWeights(p, CONFIG), CONFIG).ranked) {
        const total = r.terms.reduce((s, t) => s + t.points, 0) + r.buyerPoints;
        expect(total).toBeCloseTo(r.score as number, 9);
      }
    }
  });

  it("the reasons shown are the largest advantages over the alternatives", () => {
    // Spec: a reason is a term where the shoe is good (>= reason_min_score) AND better than
    // the candidates' mean, ranked by a_k = share_k * (x_k - mean_k); not simply the term
    // with the most points (a heavily weighted term where every shoe scores 7 explains nothing).
    const e = CONFIG.explanation;
    for (const p of profiles) {
      const weights = computeWeights(p, CONFIG);
      const ranking = rankShoes(SHOES, weights, CONFIG);
      for (const r of ranking.ranked) {
        const shown = r.explanation.reasons;
        expect(shown.length).toBeLessThanOrEqual(e.max_reasons);
        const advantages = shown.map((x) => x.advantage);
        expect(advantages).toEqual([...advantages].sort((a, b) => b - a));
        expect(shown.every((x) => x.value >= e.reason_min_score && x.advantage > 0)).toBe(true);
        // No eligible term with a larger advantage was left out.
        const weakestShown = Math.min(...advantages, Infinity);
        if (shown.length === e.max_reasons) {
          const shownKeys = new Set(shown.map((x) => x.key));
          for (const t of r.terms) {
            if (shownKeys.has(t.key) || t.value === null || t.share === 0 || t.value < e.reason_min_score) continue;
            const mean = ranking.ranked.concat(ranking.notEnoughData).map((x) => x.values[t.key]).filter((v): v is number => v !== null);
            const advantage = t.share * (t.value - mean.reduce((a, b) => a + b, 0) / mean.length);
            expect(advantage).toBeLessThanOrEqual(weakestShown + 1e-9);
          }
        }
      }
    }
  });
});

describe("similarity (spec §7), on the real catalogue", () => {
  const norm = catalogueNormalisation(SHOES, CONFIG);

  it("every shoe is most similar to itself", () => {
    for (const reference of SHOES.slice(0, 40)) {
      const self = similarity(reference, reference, norm, CONFIG).similarity;
      if (self === null) continue; // too little data to compare at all
      expect(self).toBeCloseTo(100);
      for (const other of SHOES) {
        const s = similarity(reference, other, norm, CONFIG).similarity;
        if (s !== null) expect(s).toBeLessThanOrEqual(self + 1e-9);
      }
    }
  });

  it("hard filters still apply in 'I like this model' mode", () => {
    const reference = SHOES.find((s) => s.id === "saucony-peregrine-15")!;
    const f = filters({ maxPriceEur: 120, excludedBrands: ["Saucony"] });
    const result = similarToModel(reference, SHOES, f, profile(), CONFIG);
    expect(result.similar.length).toBeGreaterThan(0);
    for (const s of result.similar) {
      expect(s.shoe.brand).not.toBe("Saucony");
      expect(lowestPrice(s.shoe)).toBeLessThanOrEqual(120);
    }
    expect(result.hiddenByFilters).toBe(SHOES.length - applyFilters(SHOES, f, profile()).passed.length);
  });
});

describe("terms", () => {
  it("lists every term of the spec once", () => {
    expect(new Set(TERMS).size).toBe(12);
  });
});
