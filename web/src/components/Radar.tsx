// A small SVG radar of the 8 criterion scores (0-10). Unknown scores are not drawn as 0:
// their axis is labelled "n/a" and the outline skips them, so missing data is not
// mistaken for a weakness.

import { CRITERIA, type Criterion } from "../engine/types";
import { TERM_LABEL } from "../labels";

interface Series {
  name: string;
  values: Record<Criterion, number | null>;
}

const SIZE = 320;
const CENTER = SIZE / 2;
const RADIUS = 105;

function point(index: number, value: number): [number, number] {
  const angle = -Math.PI / 2 + (2 * Math.PI * index) / CRITERIA.length;
  const r = (RADIUS * value) / 10;
  return [CENTER + r * Math.cos(angle), CENTER + r * Math.sin(angle)];
}

export function Radar({ series, title }: { series: Series[]; title: string }) {
  const rings = [2, 4, 6, 8, 10];
  return (
    <figure className="radar">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={title}>
        {rings.map((ring) => (
          <polygon key={ring} className="radar-ring"
            points={CRITERIA.map((_, i) => point(i, ring).join(",")).join(" ")} />
        ))}
        {CRITERIA.map((c, i) => {
          const [x, y] = point(i, 10);
          const [lx, ly] = point(i, 12.4);
          const unknown = series.every((s) => s.values[c] === null);
          return (
            <g key={c}>
              <line className="radar-axis" x1={CENTER} y1={CENTER} x2={x} y2={y} />
              <text x={lx} y={ly} className="radar-label" textAnchor={Math.abs(lx - CENTER) < 5 ? "middle" : lx > CENTER ? "start" : "end"}
                dominantBaseline="middle">
                {TERM_LABEL[c]}{unknown ? " (n/a)" : ""}
              </text>
            </g>
          );
        })}
        {series.map((s, si) => {
          const known = CRITERIA.map((c, i) => [i, s.values[c]] as const).filter(([, v]) => v !== null);
          const points = known.map(([i, v]) => point(i, v as number).join(",")).join(" ");
          return (
            <g key={s.name} className={`radar-series radar-series-${si}`}>
              {known.length >= 3 && <polygon points={points} />}
              {known.map(([i, v]) => {
                const [x, y] = point(i, v as number);
                return <circle key={i} cx={x} cy={y} r={4} />;
              })}
            </g>
          );
        })}
      </svg>
      <figcaption className="hint">
        {title}. Scores 0-10; rings every 2 points. The table below gives the exact values.
      </figcaption>
    </figure>
  );
}
