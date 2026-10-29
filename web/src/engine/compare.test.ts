import { describe, expect, it } from "vitest";
import { bestIndices, rowDiffers } from "./compare";

describe("comparator helpers", () => {
  it("finds the best value, both directions, and none when all are equal", () => {
    expect(bestIndices([6, 8.5, null, 8.5])).toEqual([1, 3]);
    expect(bestIndices([280, 240, 310], false)).toEqual([1]);
    expect(bestIndices([7, 7])).toEqual([]);
    expect(bestIndices([7, null])).toEqual([]);
  });

  it("flags rows whose values differ enough, or are known for some shoes only", () => {
    expect(rowDiffers([6.0, 6.5], 1)).toBe(false);
    expect(rowDiffers([6.0, 7.5], 1)).toBe(true);
    expect(rowDiffers([6.0, null])).toBe(true);
    expect(rowDiffers(["EVA", "EVA"])).toBe(false);
    expect(rowDiffers([true, false])).toBe(true);
    expect(rowDiffers([null, null])).toBe(false);
  });
});
