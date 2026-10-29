// "I like this model": pick a shoe, see the most similar ones (spec §7). Hard filters apply.

import { useMemo } from "react";
import { ShoeSearch } from "../components/ShoeSearch";
import type { AppData } from "../data";
import { similarToModel, type FeatureDifference } from "../engine/similarity";
import { FEATURE_WORDS, shoeName } from "../labels";
import type { AppState } from "../url";

interface Props {
  data: AppData;
  state: AppState;
  setState: (next: AppState) => void;
  referenceId: string | null;
}

const closeText = (d: FeatureDifference[]) => d.map((x) => FEATURE_WORDS[x.feature].name).join(", ");
const farText = (d: FeatureDifference[]) =>
  d.map((x) => (x.difference > 0 ? FEATURE_WORDS[x.feature].more : FEATURE_WORDS[x.feature].less)).join(", ");

export function SimilarPage({ data, state, setState, referenceId }: Props) {
  const { catalog, config } = data;
  const reference = referenceId ? catalog.shoes.find((s) => s.id === referenceId) : undefined;
  const result = useMemo(
    () => (reference ? similarToModel(reference, catalog.shoes, state.filters, state.profile, config) : null),
    [reference, catalog, state.filters, state.profile, config],
  );
  const hiddenByFilters = result?.hiddenByFilters ?? 0;
  const toggleCompare = (id: string) =>
    setState({ ...state, compare: state.compare.includes(id) ? state.compare.filter((x) => x !== id) : [...state.compare, id].slice(0, 4) });

  return (
    <section aria-labelledby="similar-title" className="narrow-page">
      <h2 id="similar-title">I like this model</h2>
      <p>Pick a shoe you like: we list the shoes closest to it on the 8 criteria, the 5 terrains, drop, stack, lug depth and waterproofing.</p>
      <ShoeSearch shoes={catalog.shoes} label="Shoe you like" onPick={(s) => { window.location.hash = `#/similar/${s.id}`; }} />
      {referenceId && !reference && <p className="notice">No shoe with the id "{referenceId}".</p>}

      {reference && result && (
        <>
          <h3>Similar to <a href={`#/shoe/${reference.id}`}>{shoeName(reference)}</a></h3>
          <p className="hint">
            Your filters apply{hiddenByFilters > 0 && ` (${hiddenByFilters} shoes hidden by them)`}.
            {result.notComparable > 0 && ` ${result.notComparable} shoes have too little data to compare.`}
          </p>
          {result.similar.length === 0 ? (
            <p className="notice">No shoe matches your filters.</p>
          ) : (
            <ol className="cards">
              {result.similar.map((s) => (
                <li key={s.shoe.id} className="card">
                  <div className="card-head">
                    <div className="card-title">
                      <h4><a href={`#/shoe/${s.shoe.id}`}>{shoeName(s.shoe)}</a>{s.otherVersion && <span className="tag">other version</span>}</h4>
                    </div>
                    <div className="score" aria-label={`Similarity ${Math.round(s.similarity ?? 0)} percent`}>
                      <span className="score-value">{Math.round(s.similarity ?? 0)}</span><span className="score-max">% similar</span>
                    </div>
                  </div>
                  <p>Very close on {closeText(s.closest)}.</p>
                  {s.furthest.length > 0 && <p>Differs: {farText(s.furthest)}.</p>}
                  <button type="button" className={state.compare.includes(s.shoe.id) ? "button selected" : "button"}
                    aria-pressed={state.compare.includes(s.shoe.id)}
                    disabled={!state.compare.includes(s.shoe.id) && state.compare.length >= 4}
                    onClick={() => toggleCompare(s.shoe.id)}>
                    {state.compare.includes(s.shoe.id) ? "✓ In comparator" : "+ Compare"}
                  </button>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  );
}
