// Helper functions of docs/scoring-spec.md §0.3 (same definitions as the Python pipeline).

export type Anchors = [number, number][];

/** Piecewise-linear interpolation, held constant outside the anchors. */
export function interp(x: number, anchors: Anchors): number {
  if (x <= anchors[0][0]) return anchors[0][1];
  const last = anchors[anchors.length - 1];
  if (x >= last[0]) return last[1];
  for (let i = 0; i < anchors.length - 1; i++) {
    const [x1, y1] = anchors[i];
    const [x2, y2] = anchors[i + 1];
    if (x >= x1 && x <= x2) return y1 + ((x - x1) * (y2 - y1)) / (x2 - x1);
  }
  throw new Error("unreachable: x is inside the anchors");
}

export const clamp = (t: number, low = 0, high = 1): number => Math.min(high, Math.max(low, t));

/** Smooth ramp from 0 to 1 with zero slope at both ends. */
export function smoothstep(t: number): number {
  const c = clamp(t);
  return 3 * c * c - 2 * c * c * c;
}

/** Weighted mean of the known values; null when nothing is known. */
export function weightedMean(items: { value: number | null; weight: number }[]): number | null {
  const known = items.filter((i) => i.value !== null && i.weight > 0);
  const total = known.reduce((sum, i) => sum + i.weight, 0);
  if (total === 0) return null;
  return known.reduce((sum, i) => sum + i.weight * (i.value as number), 0) / total;
}

/** Percentile with linear interpolation between closest ranks (same as numpy's default). */
export function percentile(values: number[], p: number): number {
  const sorted = [...values].sort((a, b) => a - b);
  const position = ((sorted.length - 1) * p) / 100;
  const low = Math.floor(position);
  const high = Math.ceil(position);
  return sorted[low] + (sorted[high] - sorted[low]) * (position - low);
}
