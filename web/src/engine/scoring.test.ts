import { describe, expect, it } from "vitest";
import { DEFAULT_PROFILE, type Profile } from "./profile";
import { rankShoes, scoreLabel, scoreShoe, termValues } from "./scoring";
import { CONFIG, makeShoe } from "./testing";
import { CRITERIA } from "./types";
import { computeWeights } from "./weights";

const weightsFor = (p: Partial<Profile> = {}) => computeWeights({ ...DEFAULT_PROFILE, ...p }, CONFIG);

describe("score and explanation (spec §6)", () => {
  it("adds the points of every term and the buyer term up to the score", () => {
    const shoe = makeShoe({ criteria: { cushioning: 8, grip: 3 }, buyer: 4.6 });
    for (const w of [weightsFor(), weightsFor({ weightKg: 90, footStrike: "heel", terrains: ["muddy_soft"] })]) {
      const r = scoreShoe(shoe, w, CONFIG);
      const total = r.terms.reduce((s, t) => s + t.points, 0) + r.buyerPoints;
      expect(total).toBeCloseTo(r.score as number, 9);
    }
  });

  it("is absolute: 10/10 everywhere and top buyer rating gives 100", () => {
    const perfect = makeShoe({
      criteria: Object.fromEntries(CRITERIA.map((c) => [c, 10])),
      terrain: { road_to_trail: 10, groomed_mixed: 10, technical_rocky: 10, muddy_soft: 10, wet_roots: 10 },
      buyer: 5,
    });
    expect(scoreShoe(perfect, weightsFor(), CONFIG).score).toBeCloseTo(100);
    expect(scoreShoe(makeShoe(), weightsFor(), CONFIG).score).toBeCloseTo(50); // all 5, no buyer rating
  });

  it("scores the drop fit with the bell curve of §5.5 (6 mm for a heel striker ≈ 7.5)", () => {
    const values = termValues(makeShoe({ drop: 6 }), weightsFor({ footStrike: "heel" }), CONFIG);
    expect(values.drop_fit).toBeCloseTo(10 * Math.exp(-0.5 * (3 / 4) ** 2), 9);
    expect(values.drop_fit).toBeCloseTo(7.5, 1);
    expect(termValues(makeShoe({ drop: null }), weightsFor(), CONFIG).drop_fit).toBeNull();
  });

  it("derives ground feel and agility (§5.3)", () => {
    const v = termValues(makeShoe({ criteria: { cushioning: 8, lightness: 6 } }), weightsFor(), CONFIG);
    expect(v.ground_feel).toBe(2);
    expect(v.agility).toBeCloseTo(0.6 * 6 + 0.4 * 2);
  });

  it("counts an unknown weighted term as neutral: missing data neither helps nor hurts", () => {
    const w = weightsFor({ sliders: { cushioning_vs_ground_feel: 50, stability_vs_agility: 50, dynamic_vs_comfortable: 0 } });
    const score = (responsiveness: number | null) =>
      scoreShoe(makeShoe({ criteria: { cushioning: 9, responsiveness } }), w, CONFIG).score as number;
    expect(score(null)).toBeCloseTo(score(5));
    expect(score(null)).toBeGreaterThan(score(2));
    expect(score(null)).toBeLessThan(score(8));
    const r = scoreShoe(makeShoe({ criteria: { responsiveness: null } }), w, CONFIG);
    expect(r.coverage).toBeLessThan(1);
    expect(r.terms.find((t) => t.key === "responsiveness")?.counted).toBe(5);
  });

  it("gives no score when nothing weighted is known", () => {
    const empty = makeShoe({
      criteria: Object.fromEntries(CRITERIA.map((c) => [c, null])),
      terrain: { road_to_trail: null, groomed_mixed: null, technical_rocky: null, muddy_soft: null, wet_roots: null },
      drop: null,
    });
    expect(scoreShoe(empty, weightsFor(), CONFIG).score).toBeNull();
  });

  it("does not rank a shoe whose known data covers too little weight (§6.3)", () => {
    const sparse = makeShoe({
      criteria: Object.fromEntries(CRITERIA.map((c) => [c, c === "grip" ? 9 : null])),
      terrain: { road_to_trail: null, groomed_mixed: null, technical_rocky: null, muddy_soft: null, wet_roots: null },
    });
    const ranking = rankShoes([sparse, makeShoe({ id: "full" })], weightsFor(), CONFIG);
    expect(ranking.ranked.map((r) => r.shoe.id)).toEqual(["full"]);
    expect(ranking.notEnoughData[0].coverage).toBeLessThan(CONFIG.final.min_ranking_coverage);
  });

  it("gives reasons that are good AND better than the alternatives, drawbacks the reverse", () => {
    const candidates = [
      makeShoe({ id: "grippy", criteria: { grip: 9.5, lightness: 2 } }),
      ...[1, 2, 3, 4, 5].map((i) => makeShoe({ id: `average-${i}`, criteria: { grip: 6, lightness: 6 } })),
    ];
    const grippy = rankShoes(candidates, weightsFor(), CONFIG).ranked.find((r) => r.shoe.id === "grippy")!;
    expect(grippy.explanation.reasons[0].key).toBe("grip");
    expect(grippy.explanation.reasons.every((p) => p.value >= 6.5 && p.advantage > 0)).toBe(true);
    expect(grippy.explanation.drawbacks.map((p) => p.key)).toContain("lightness");
  });

  it("lists heavily weighted unknown terms as missing data", () => {
    const noTerrain = makeShoe({
      terrain: { road_to_trail: null, groomed_mixed: null, technical_rocky: null, muddy_soft: null, wet_roots: null },
    });
    const r = rankShoes([noTerrain], weightsFor(), CONFIG).ranked[0];
    expect(r.explanation.missing.map((m) => m.key)).toContain("terrain");
  });

  it("breaks ties by confidence, then coverage, then lower price (§6.4)", () => {
    const shoes = [
      makeShoe({ id: "low-conf", confidence: "low", price: 80 }),
      makeShoe({ id: "high-dear", confidence: "high", price: 200 }),
      makeShoe({ id: "high-cheap", confidence: "high", price: 100 }),
    ];
    expect(rankShoes(shoes, weightsFor(), CONFIG).ranked.map((r) => r.shoe.id)).toEqual(["high-cheap", "high-dear", "low-conf"]);
  });

  it("labels scores with the bands of the config", () => {
    expect([9, 7, 5, 3, 1].map((v) => scoreLabel(v, CONFIG))).toEqual(["excellent", "good", "average", "weak", "poor"]);
  });
});
