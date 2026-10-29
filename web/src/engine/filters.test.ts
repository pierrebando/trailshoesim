import { describe, expect, it } from "vitest";
import { applyFilters, failingFilter } from "./filters";
import { DEFAULT_FILTERS, DEFAULT_PROFILE, type Filters } from "./profile";
import { makeShoe } from "./testing";

const filters = (f: Partial<Filters>): Filters => ({ ...DEFAULT_FILTERS, ...f });

describe("hard filters (spec §1)", () => {
  it("lets everything through with the default filters", () => {
    const shoes = [makeShoe({ id: "a" }), makeShoe({ id: "b", drop: null, waterproof: null })];
    expect(applyFilters(shoes, DEFAULT_FILTERS, DEFAULT_PROFILE).passed).toHaveLength(2);
  });

  it("filters on the lowest price", () => {
    const outcome = applyFilters([makeShoe({ id: "cheap", price: 90 }), makeShoe({ id: "dear", price: 200 })],
      filters({ maxPriceEur: 100 }), DEFAULT_PROFILE);
    expect(outcome.passed.map((s) => s.id)).toEqual(["cheap"]);
    expect(outcome.failed.price).toBe(1);
  });

  it("excludes brands case-insensitively", () => {
    const shoe = makeShoe({ brand: "La Sportiva" });
    expect(failingFilter(shoe, filters({ excludedBrands: ["la sportiva"] }), DEFAULT_PROFILE)?.filter).toBe("brand");
  });

  it("fails a shoe whose value is unknown when the filter is set, and counts it apart", () => {
    const shoes = [makeShoe({ id: "wp", waterproof: true }), makeShoe({ id: "dry", waterproof: false }), makeShoe({ id: "?", waterproof: null })];
    const outcome = applyFilters(shoes, filters({ waterproof: "yes" }), DEFAULT_PROFILE);
    expect(outcome.passed.map((s) => s.id)).toEqual(["wp"]);
    expect(outcome.failed.waterproof).toBe(1);
    expect(outcome.unknown.waterproof).toBe(1);
  });

  it("keeps drops inside the range, bounds included", () => {
    const shoes = [4, 6, 8, 10].map((drop) => makeShoe({ id: `d${drop}`, drop }));
    const outcome = applyFilters(shoes, filters({ dropMinMm: 6, dropMaxMm: 8 }), DEFAULT_PROFILE);
    expect(outcome.passed.map((s) => s.id)).toEqual(["d6", "d8"]);
    expect(applyFilters([makeShoe({ drop: null })], filters({ dropMaxMm: 8 }), DEFAULT_PROFILE).unknown.drop).toBe(1);
  });

  it("requires the width to be offered", () => {
    const wide = makeShoe({ widths: ["standard", "wide"] });
    expect(failingFilter(wide, filters({ width: "wide" }), DEFAULT_PROFILE)).toBeNull();
    expect(failingFilter(wide, filters({ width: "narrow" }), DEFAULT_PROFILE)?.filter).toBe("width");
    expect(failingFilter(makeShoe({ widths: null }), filters({ width: "wide" }), DEFAULT_PROFILE)?.unknown).toBe(true);
  });

  it("matches the runner's gender or unisex, and does nothing without a gender", () => {
    const women = { ...DEFAULT_PROFILE, gender: "women" as const };
    const on = filters({ genderMatch: true });
    expect(failingFilter(makeShoe({ genders: ["men"] }), on, women)?.filter).toBe("gender");
    expect(failingFilter(makeShoe({ genders: ["unisex"] }), on, women)).toBeNull();
    expect(failingFilter(makeShoe({ genders: ["men"] }), on, DEFAULT_PROFILE)).toBeNull();
  });
});
