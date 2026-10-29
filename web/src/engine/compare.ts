// Comparator helpers: which column is best in a row, and whether a row differs at all.

/** Indices of the best known value(s) of a row; empty when fewer than 2 values are known. */
export function bestIndices(values: (number | null)[], higherIsBetter = true): number[] {
  const known = values.filter((v): v is number => v !== null);
  if (known.length < 2) return [];
  const best = higherIsBetter ? Math.max(...known) : Math.min(...known);
  if (known.every((v) => v === best)) return [];
  return values.flatMap((v, i) => (v === best ? [i] : []));
}

/** True when the known values of a row are at least `threshold` apart, or when only
 * some of them are known (an unknown next to a known value is a difference too). */
export function rowDiffers(values: (number | string | boolean | null)[], threshold = 0): boolean {
  const known = values.filter((v) => v !== null);
  if (known.length === 0) return false;
  if (known.length < values.length) return true;
  if (known.every((v) => typeof v === "number")) {
    const numbers = known as number[];
    return Math.max(...numbers) - Math.min(...numbers) >= Math.max(threshold, Number.EPSILON);
  }
  return new Set(known.map(String)).size > 1;
}
