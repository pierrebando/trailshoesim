// Hard filters (spec §1): shoes that fail one are not shown at all.

import { useId } from "react";
import type { Filters, Profile } from "../engine/profile";
import type { Width } from "../engine/types";
import { WIDTH_LABEL } from "../labels";

interface Props {
  filters: Filters;
  profile: Profile;
  brands: string[];
  onChange: (filters: Filters) => void;
}

const optionalNumber = (raw: string): number | null => (raw.trim() === "" ? null : Number(raw));

export function FiltersPanel({ filters, profile, brands, onChange }: Props) {
  const id = useId();
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => onChange({ ...filters, [key]: value });
  const toggleBrand = (b: string) =>
    set("excludedBrands", filters.excludedBrands.includes(b) ? filters.excludedBrands.filter((x) => x !== b) : [...filters.excludedBrands, b]);

  return (
    <form className="panel" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
      <fieldset>
        <legend>Filters</legend>
        <p className="hint">Shoes that fail a filter are hidden. A shoe whose value is unknown is hidden too.</p>
        <div className="field">
          <label htmlFor={`${id}-price`}>Max price (€)</label>
          <input id={`${id}-price`} type="number" min={0} step={10} inputMode="numeric" placeholder="No limit"
            value={filters.maxPriceEur ?? ""} onChange={(e) => set("maxPriceEur", optionalNumber(e.target.value))} />
        </div>
        <div className="field-row">
          <div className="field">
            <label htmlFor={`${id}-dmin`}>Min drop (mm)</label>
            <input id={`${id}-dmin`} type="number" min={0} max={20} step={1} placeholder="Any"
              value={filters.dropMinMm ?? ""} onChange={(e) => set("dropMinMm", optionalNumber(e.target.value))} />
          </div>
          <div className="field">
            <label htmlFor={`${id}-dmax`}>Max drop (mm)</label>
            <input id={`${id}-dmax`} type="number" min={0} max={20} step={1} placeholder="Any"
              value={filters.dropMaxMm ?? ""} onChange={(e) => set("dropMaxMm", optionalNumber(e.target.value))} />
          </div>
        </div>
        <fieldset className="field">
          <legend>Waterproof</legend>
          <div className="choices">
            {(["any", "yes", "no"] as const).map((v) => (
              <label key={v} className="choice">
                <input type="radio" name={`${id}-wp`} checked={filters.waterproof === v} onChange={() => set("waterproof", v)} />
                {v === "any" ? "Any" : v === "yes" ? "Yes" : "No"}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="field">
          <label htmlFor={`${id}-width`}>Width available</label>
          <select id={`${id}-width`} value={filters.width} onChange={(e) => set("width", e.target.value as Width | "any")}>
            <option value="any">Any</option>
            {(["narrow", "standard", "wide", "extra_wide"] as Width[]).map((w) => <option key={w} value={w}>{WIDTH_LABEL[w]}</option>)}
          </select>
        </div>
        <label className="choice">
          <input type="checkbox" checked={filters.genderMatch} disabled={profile.gender === "unspecified"}
            onChange={(e) => set("genderMatch", e.target.checked)} />
          Only shoes sold in my gender (or unisex)
          {profile.gender === "unspecified" && <span className="hint"> — choose a gender in the profile first</span>}
        </label>
        <details className="field">
          <summary>Exclude brands {filters.excludedBrands.length > 0 && `(${filters.excludedBrands.length})`}</summary>
          <div className="brand-list">
            {brands.map((b) => (
              <label key={b} className="choice">
                <input type="checkbox" checked={filters.excludedBrands.includes(b)} onChange={() => toggleBrand(b)} />
                {b}
              </label>
            ))}
          </div>
        </details>
      </fieldset>
    </form>
  );
}
