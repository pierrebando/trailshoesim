// Search a shoe by name (brand, model, version); used by "I like this model" and the comparator.

import { useId, useState } from "react";
import type { Shoe } from "../engine/types";
import { shoeName } from "../labels";

interface Props {
  shoes: Shoe[];
  label: string;
  onPick: (shoe: Shoe) => void;
  exclude?: string[];
}

const MAX_MATCHES = 8;

export function ShoeSearch({ shoes, label, onPick, exclude = [] }: Props) {
  const id = useId();
  const [query, setQuery] = useState("");
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const matches = words.length === 0 ? [] : shoes
    .filter((s) => !exclude.includes(s.id))
    .filter((s) => words.every((w) => shoeName(s).toLowerCase().includes(w)))
    .slice(0, MAX_MATCHES);
  return (
    <div className="search">
      <label htmlFor={id}>{label}</label>
      <input id={id} type="search" value={query} placeholder="e.g. speedgoat, peregrine 15, la sportiva"
        autoComplete="off" onChange={(e) => setQuery(e.target.value)} aria-describedby={`${id}-count`} />
      <p id={`${id}-count`} className="hint" aria-live="polite">
        {words.length > 0 && (matches.length === 0 ? "No shoe found." : `${matches.length}${matches.length === MAX_MATCHES ? "+" : ""} found`)}
      </p>
      {matches.length > 0 && (
        <ul className="search-results">
          {matches.map((s) => (
            <li key={s.id}>
              <button type="button" className="button link" onClick={() => { onPick(s); setQuery(""); }}>
                {shoeName(s)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
