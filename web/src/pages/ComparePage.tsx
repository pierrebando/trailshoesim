// Comparator: 2-4 shoes side by side. Rows that differ are highlighted, the best score of
// a row is marked with "▲ best" (text, not only colour).

import { useMemo, useState, type ReactNode } from "react";
import { Radar } from "../components/Radar";
import { ShoeSearch } from "../components/ShoeSearch";
import type { AppData } from "../data";
import { bestIndices, rowDiffers } from "../engine/compare";
import { lowestPrice } from "../engine/filters";
import { scoreShoe } from "../engine/scoring";
import { CRITERIA, TERRAINS, type Criterion, type Shoe } from "../engine/types";
import { computeWeights } from "../engine/weights";
import { euro, shoeName, TERM_LABEL, TERRAIN_LABEL } from "../labels";
import type { AppState } from "../url";

interface Props {
  data: AppData;
  state: AppState;
  setState: (next: AppState) => void;
}

interface Row {
  label: string;
  values: (number | string | boolean | null)[];
  format: (v: number | string | boolean) => string;
  /** "higher" / "lower" marks the best column; undefined = no "best" (e.g. drop is a preference). */
  best?: "higher" | "lower";
  threshold?: number;
}

const score = (v: number | string | boolean) => (v as number).toFixed(1);
const mm = (v: number | string | boolean) => `${v} mm`;

export function ComparePage({ data, state, setState }: Props) {
  const { catalog, config } = data;
  const [onlyDifferences, setOnlyDifferences] = useState(false);
  const shoes = state.compare.map((id) => catalog.shoes.find((s) => s.id === id)).filter((s): s is Shoe => !!s);
  const weights = useMemo(() => computeWeights(state.profile, config), [state.profile, config]);
  const remove = (id: string) => setState({ ...state, compare: state.compare.filter((x) => x !== id) });
  const add = (s: Shoe) => setState({ ...state, compare: [...state.compare, s.id].slice(0, 4) });

  const groups: { title: string; rows: Row[] }[] = [
    {
      title: "Overview",
      rows: [
        { label: "Score for your profile", values: shoes.map((s) => scoreShoe(s, weights, config).score), format: (v) => `${Math.round(v as number)}/100`, best: "higher", threshold: 3 },
        { label: "Price from", values: shoes.map((s) => lowestPrice(s)), format: (v) => euro(v as number), best: "lower", threshold: 10 },
        { label: "Confidence", values: shoes.map((s) => s.confidence.level), format: String },
      ],
    },
    {
      title: "Criteria (0-10)",
      rows: CRITERIA.map((c: Criterion) => ({ label: TERM_LABEL[c], values: shoes.map((s) => s.criteria_scores[c].score_0_10), format: score, best: "higher" as const, threshold: 1 })),
    },
    {
      title: "Terrain (0-10)",
      rows: TERRAINS.map((t) => ({ label: TERRAIN_LABEL[t].name, values: shoes.map((s) => s.terrain_scores[t].score_0_10), format: score, best: "higher" as const, threshold: 1 })),
    },
    {
      title: "Specs",
      rows: [
        { label: "Weight (men's)", values: shoes.map((s) => s.specs.weight_g.value), format: (v) => `${Math.round(v as number)} g`, best: "lower", threshold: 15 },
        { label: "Stack height, heel", values: shoes.map((s) => s.specs.stack_heel_mm.value), format: mm, threshold: 2 },
        { label: "Drop", values: shoes.map((s) => s.specs.drop_mm.value), format: mm, threshold: 1 },
        { label: "Lug depth", values: shoes.map((s) => s.specs.lug_depth_mm.value), format: mm, threshold: 0.5 },
        { label: "Waterproof", values: shoes.map((s) => s.specs.waterproof.value), format: (v) => (v ? "Yes" : "No") },
        { label: "Midsole foam", values: shoes.map((s) => s.specs.midsole_foam.value), format: String },
        { label: "Outsole rubber", values: shoes.map((s) => s.specs.outsole_rubber.value), format: String },
      ],
    },
  ];

  return (
    <section aria-labelledby="compare-title">
      <h2 id="compare-title">Compare</h2>
      {shoes.length < 4 && (
        <ShoeSearch shoes={catalog.shoes} exclude={state.compare} label={`Add a shoe (${shoes.length}/4)`} onPick={add} />
      )}
      {shoes.length < 2 ? (
        <p className="notice">Add at least two shoes, here or with the "+ Compare" buttons of the results.</p>
      ) : (
        <>
          <label className="choice">
            <input type="checkbox" checked={onlyDifferences} onChange={(e) => setOnlyDifferences(e.target.checked)} />
            Show only the rows that differ
          </label>
          <div className="table-scroll" role="region" aria-label="Comparison table" tabIndex={0}>
            <table className="table compare">
              <thead>
                <tr>
                  <td />
                  {shoes.map((s) => (
                    <th key={s.id} scope="col">
                      <a href={`#/shoe/${s.id}`}>{shoeName(s)}</a>
                      <button type="button" className="button link remove" onClick={() => remove(s.id)} aria-label={`Remove ${shoeName(s)}`}>
                        Remove
                      </button>
                    </th>
                  ))}
                </tr>
                <tr>
                  <td />
                  {shoes.map((s) => (
                    <td key={s.id} className="mini-radar">
                      <Radar
                        series={[{ name: shoeName(s), values: Object.fromEntries(CRITERIA.map((c) => [c, s.criteria_scores[c].score_0_10])) as Record<Criterion, number | null> }]}
                        title={`Criteria of the ${shoeName(s)}`}
                      />
                    </td>
                  ))}
                </tr>
              </thead>
              {groups.map((group) => (
                <tbody key={group.title}>
                  <tr className="group-row"><th colSpan={shoes.length + 1} scope="colgroup">{group.title}</th></tr>
                  {group.rows.map((row) => {
                    const differs = rowDiffers(row.values, row.threshold);
                    if (onlyDifferences && !differs) return null;
                    const best = row.best ? bestIndices(row.values as (number | null)[], row.best === "higher") : [];
                    return (
                      <tr key={row.label} className={differs ? "differs" : undefined}>
                        <th scope="row">{row.label}{differs && <span className="visually-hidden"> (differs)</span>}</th>
                        {row.values.map((v, i): ReactNode => (
                          <td key={shoes[i].id} className={best.includes(i) ? "best" : undefined}>
                            {v === null ? <span className="hint">unknown</span> : row.format(v)}
                            {best.includes(i) && <span className="best-mark"> ▲ best</span>}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              ))}
            </table>
          </div>
          <p className="hint">Highlighted rows differ noticeably between the shoes. "Best" is only marked where more (or less) is clearly better.</p>
        </>
      )}
    </section>
  );
}
