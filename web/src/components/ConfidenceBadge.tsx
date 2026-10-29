import type { Confidence } from "../engine/types";

const TEXT = { high: "High confidence", medium: "Medium confidence", low: "Low confidence" } as const;
// Three filled dots for high, two for medium, one for low: readable without colour.
const DOTS = { high: "●●●", medium: "●●○", low: "●○○" } as const;

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const title = confidence.reasons.length ? `Not higher because: ${confidence.reasons.join("; ")}` : "All conditions met";
  return (
    <span className={`badge badge-${confidence.level}`} title={title}>
      <span aria-hidden="true">{DOTS[confidence.level]}</span> {TEXT[confidence.level]}
    </span>
  );
}
