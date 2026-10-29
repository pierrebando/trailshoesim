// Hard filters (docs/scoring-spec.md §1). They run before scoring: a shoe that fails one
// is not ranked. If a filter is set and the shoe's value is unknown, the shoe FAILS (we
// cannot promise it matches) and the UI says how many shoes were hidden that way.

import type { Filters, Profile } from "./profile";
import type { Shoe } from "./types";

export type FilterName = "price" | "brand" | "waterproof" | "drop" | "width" | "gender";

export interface FilterOutcome {
  passed: Shoe[];
  /** Shoes removed by each filter because their value does not match. */
  failed: Record<FilterName, number>;
  /** Shoes removed by each filter because their value is unknown. */
  unknown: Record<FilterName, number>;
}

/** Lowest price of a shoe over all its offers (null if it has none). */
export function lowestPrice(shoe: Shoe): number | null {
  if (shoe.retail.length === 0) return null;
  return Math.min(...shoe.retail.map((o) => o.price_eur));
}

/** First filter the shoe fails, and whether because its value is unknown; null = passes. */
export function failingFilter(
  shoe: Shoe,
  filters: Filters,
  profile: Profile,
): { filter: FilterName; unknown: boolean } | null {
  if (filters.maxPriceEur !== null) {
    const price = lowestPrice(shoe);
    if (price === null) return { filter: "price", unknown: true };
    if (price > filters.maxPriceEur) return { filter: "price", unknown: false };
  }
  const excluded = filters.excludedBrands.map((b) => b.toLowerCase());
  if (excluded.includes(shoe.brand.toLowerCase())) return { filter: "brand", unknown: false };

  if (filters.waterproof !== "any") {
    const value = shoe.specs.waterproof.value;
    if (value === null) return { filter: "waterproof", unknown: true };
    if (value !== (filters.waterproof === "yes")) return { filter: "waterproof", unknown: false };
  }
  if (filters.dropMinMm !== null || filters.dropMaxMm !== null) {
    const drop = shoe.specs.drop_mm.value;
    if (drop === null) return { filter: "drop", unknown: true };
    if (filters.dropMinMm !== null && drop < filters.dropMinMm) return { filter: "drop", unknown: false };
    if (filters.dropMaxMm !== null && drop > filters.dropMaxMm) return { filter: "drop", unknown: false };
  }
  if (filters.width !== "any") {
    const widths = shoe.specs.width_options.value;
    if (widths === null) return { filter: "width", unknown: true };
    if (!widths.includes(filters.width)) return { filter: "width", unknown: false };
  }
  // The gender filter needs to know the runner's gender; without it, it does nothing.
  if (filters.genderMatch && profile.gender !== "unspecified") {
    const sold = shoe.gender_variants;
    if (!sold.includes(profile.gender) && !sold.includes("unisex")) {
      return { filter: "gender", unknown: false };
    }
  }
  return null;
}

/** Apply every hard filter and count why shoes were removed. */
export function applyFilters(shoes: Shoe[], filters: Filters, profile: Profile): FilterOutcome {
  const zero = (): Record<FilterName, number> => ({
    price: 0, brand: 0, waterproof: 0, drop: 0, width: 0, gender: 0,
  });
  const outcome: FilterOutcome = { passed: [], failed: zero(), unknown: zero() };
  for (const shoe of shoes) {
    const failure = failingFilter(shoe, filters, profile);
    if (failure === null) outcome.passed.push(shoe);
    else if (failure.unknown) outcome.unknown[failure.filter] += 1;
    else outcome.failed[failure.filter] += 1;
  }
  return outcome;
}
