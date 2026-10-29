// Profile + filters on the side, ranked results next to them.

import { useMemo, useState } from "react";
import { FiltersPanel } from "../components/FiltersPanel";
import { ProfileForm } from "../components/ProfileForm";
import { ResultCard } from "../components/ResultCard";
import type { AppData } from "../data";
import { applyFilters, type FilterName } from "../engine/filters";
import { DEFAULT_FILTERS, DEFAULT_PROFILE } from "../engine/profile";
import { rankShoes } from "../engine/scoring";
import { computeWeights } from "../engine/weights";
import { FILTER_UNKNOWN_TEXT, shoeName } from "../labels";
import type { AppState } from "../url";

const PAGE = 20;

interface Props {
  data: AppData;
  state: AppState;
  setState: (next: AppState) => void;
}

export function FinderPage({ data, state, setState }: Props) {
  const { catalog, config } = data;
  const { profile, filters } = state;
  const [shown, setShown] = useState(PAGE);

  const brands = useMemo(() => [...new Set(catalog.shoes.map((s) => s.brand))].sort(), [catalog]);
  const outcome = useMemo(() => applyFilters(catalog.shoes, filters, profile), [catalog, filters, profile]);
  const weights = useMemo(() => computeWeights(profile, config), [profile, config]);
  const ranking = useMemo(() => rankShoes(outcome.passed, weights, config), [outcome, weights, config]);

  const toggleCompare = (id: string) =>
    setState({
      ...state,
      compare: state.compare.includes(id) ? state.compare.filter((x) => x !== id) : [...state.compare, id].slice(0, 4),
    });
  const unknownNotes = (Object.entries(outcome.unknown) as [FilterName, number][]).filter(([, n]) => n > 0);

  return (
    <div className="finder">
      <a className="jump-link" href="#results-title" onClick={(e) => {
        e.preventDefault(); // a plain #anchor would change the hash route
        document.getElementById("results-title")?.scrollIntoView();
        document.getElementById("results-title")?.focus();
      }}>
        Jump to the results ({ranking.ranked.length})
      </a>
      <aside className="sidebar">
        <ProfileForm profile={profile} onChange={(p) => { setState({ ...state, profile: p }); setShown(PAGE); }} />
        <FiltersPanel filters={filters} profile={profile} brands={brands}
          onChange={(f) => { setState({ ...state, filters: f }); setShown(PAGE); }} />
        <button type="button" className="button link"
          onClick={() => setState({ ...state, profile: DEFAULT_PROFILE, filters: DEFAULT_FILTERS })}>
          Reset profile and filters
        </button>
      </aside>

      <section className="results" aria-labelledby="results-title">
        <h2 id="results-title" tabIndex={-1}>Shoes for you</h2>
        <div aria-live="polite" className="summary">
          {outcome.passed.length === 0 ? (
            <p className="notice">No shoe matches your filters.</p>
          ) : (
            <p>
              {ranking.ranked.length} shoes ranked
              {ranking.notEnoughData.length > 0 && `, ${ranking.notEnoughData.length} without enough data to rank`}.
            </p>
          )}
          {unknownNotes.map(([filter, n]) => (
            <p key={filter} className="hint">{n} shoe{n > 1 ? "s" : ""} hidden because {FILTER_UNKNOWN_TEXT[filter]}.</p>
          ))}
        </div>

        <ol className="cards">
          {ranking.ranked.slice(0, shown).map((r, i) => (
            <li key={r.shoe.id}>
              <ResultCard rank={i + 1} result={r} profile={profile} inCompare={state.compare.includes(r.shoe.id)}
                compareFull={state.compare.length >= 4} onToggleCompare={() => toggleCompare(r.shoe.id)} />
            </li>
          ))}
        </ol>
        {shown < ranking.ranked.length && (
          <button type="button" className="button" onClick={() => setShown(shown + PAGE)}>
            Show {Math.min(PAGE, ranking.ranked.length - shown)} more
          </button>
        )}

        {ranking.notEnoughData.length > 0 && (
          <details className="not-enough">
            <summary>Not enough data to rank ({ranking.notEnoughData.length})</summary>
            <p className="hint">
              Too little of what matters to you is known about these shoes, so they are not ranked
              (spec: less than {Math.round(config.final.min_ranking_coverage * 100)} % of your weights covered).
            </p>
            <ul>
              {ranking.notEnoughData.map((r) => (
                <li key={r.shoe.id}>
                  <a href={`#/shoe/${r.shoe.id}`}>{shoeName(r.shoe)}</a>{" "}
                  <span className="hint">({Math.round(r.coverage * 100)} % covered)</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>
    </div>
  );
}
