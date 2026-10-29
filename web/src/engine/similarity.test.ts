import { describe, expect, it } from "vitest";
import { priceAgeDays } from "./confidence";
import { catalogueNormalisation, findSimilar, similarity } from "./similarity";
import { CONFIG, makeShoe } from "./testing";
import { CRITERIA } from "./types";

const catalogue = [
  makeShoe({ id: "ref", criteria: { cushioning: 8 }, drop: 8, stackHeel: 38 }),
  makeShoe({ id: "close", criteria: { cushioning: 7.5 }, drop: 8, stackHeel: 37 }),
  makeShoe({ id: "far", criteria: { cushioning: 2, lightness: 9 }, drop: 0, stackHeel: 20 }),
  makeShoe({ id: "ref-v2", model: "ref", criteria: { cushioning: 8 }, drop: 6, stackHeel: 36 }),
];
const norm = catalogueNormalisation(catalogue, CONFIG);
const [ref, close, far] = catalogue;

describe("similarity (spec §7)", () => {
  it("is maximal (100) for a shoe compared with itself", () => {
    expect(similarity(ref, ref, norm, CONFIG).similarity).toBeCloseTo(100);
  });

  it("is symmetric and ranks the closer shoe first", () => {
    expect(similarity(ref, far, norm, CONFIG).similarity).toBeCloseTo(similarity(far, ref, norm, CONFIG).similarity as number);
    const result = findSimilar(ref, catalogue, catalogue, CONFIG).similar.map((s) => s.shoe.id);
    expect(result[0]).toBe("close");
    expect(result[result.length - 1]).toBe("far");
    expect(result).not.toContain("ref");
  });

  it("explains with the closest and furthest features, with a direction", () => {
    const s = similarity(ref, far, norm, CONFIG);
    // 20 vs 38 mm spans the whole catalogue range once scaled: the biggest difference.
    expect(s.furthest[0].feature).toBe("stack_heel_mm");
    expect(s.furthest[0].difference).toBeLessThan(0); // the candidate is lower
    expect(s.closest).toHaveLength(3);
  });

  it("says 'not comparable' when too few features are known for both", () => {
    const empty = makeShoe({
      id: "empty",
      criteria: Object.fromEntries(CRITERIA.map((c) => [c, null])),
      terrain: { road_to_trail: null, groomed_mixed: null, technical_rocky: null, muddy_soft: null, wet_roots: null },
    });
    expect(similarity(ref, empty, norm, CONFIG).similarity).toBeNull();
    expect(findSimilar(ref, [empty, close], catalogue, CONFIG).notComparable).toBe(1);
  });

  it("labels other versions of the same model", () => {
    const v2 = findSimilar(ref, catalogue, catalogue, CONFIG).similar.find((s) => s.shoe.id === "ref-v2");
    expect(v2?.otherVersion).toBe(true);
    expect(similarity(ref, close, norm, CONFIG).otherVersion).toBe(false);
  });
});

describe("confidence (spec §8)", () => {
  it("recomputes the price age on the day of viewing", () => {
    const shoe = makeShoe({ priceDate: "2026-10-28" });
    expect(priceAgeDays(shoe, new Date("2026-10-28T15:00:00Z"))).toBe(0);
    expect(priceAgeDays(shoe, new Date("2026-11-12T08:00:00Z"))).toBe(15);
  });
});
