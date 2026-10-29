// The runner profile, in three sections: Runner, Run, Preferences.

import { useId } from "react";
import { PREFERENCE_AXES, type FootStrike, type FootWidth, type Profile, type ProfileGender } from "../engine/profile";
import { TERRAINS, type Terrain } from "../engine/types";
import { AXIS_LABEL, STRIKE_LABEL, TERRAIN_LABEL, WIDTH_LABEL } from "../labels";

// The distance slider is logarithmic, like the load index (spec §5.1): it gives as much
// room to 5-21 km as to 42-170 km.
const KM_MIN = 5;
const KM_MAX = 170;
const kmToPosition = (km: number) => (100 * Math.log(km / KM_MIN)) / Math.log(KM_MAX / KM_MIN);
const positionToKm = (p: number) => Math.round(KM_MIN * (KM_MAX / KM_MIN) ** (p / 100));

interface Props {
  profile: Profile;
  onChange: (profile: Profile) => void;
}

export function ProfileForm({ profile, onChange }: Props) {
  const id = useId();
  const set = <K extends keyof Profile>(key: K, value: Profile[K]) => onChange({ ...profile, [key]: value });
  const toggleTerrain = (t: Terrain) =>
    set("terrains", profile.terrains.includes(t) ? profile.terrains.filter((x) => x !== t) : [...profile.terrains, t]);

  return (
    <form className="panel" onSubmit={(e) => e.preventDefault()} aria-label="Your profile">
      <fieldset>
        <legend>Runner</legend>
        <div className="field">
          <label htmlFor={`${id}-gender`}>Gender</label>
          <select id={`${id}-gender`} value={profile.gender} onChange={(e) => set("gender", e.target.value as ProfileGender)}>
            <option value="unspecified">Prefer not to say</option>
            <option value="women">Women</option>
            <option value="men">Men</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${id}-weight`}>
            Body weight <output htmlFor={`${id}-weight`}>{profile.weightKg} kg</output>
          </label>
          <input id={`${id}-weight`} type="range" min={40} max={120} step={1} value={profile.weightKg}
            onChange={(e) => set("weightKg", Number(e.target.value))} />
        </div>
        <div className="field">
          <label htmlFor={`${id}-width`}>Foot width</label>
          <select id={`${id}-width`} value={profile.footWidth} onChange={(e) => set("footWidth", e.target.value as FootWidth)}>
            {(Object.keys(WIDTH_LABEL) as FootWidth[]).map((w) => <option key={w} value={w}>{WIDTH_LABEL[w]}</option>)}
          </select>
        </div>
        <fieldset className="field">
          <legend>Foot strike</legend>
          <div className="choices">
            {(Object.keys(STRIKE_LABEL) as FootStrike[]).map((s) => (
              <label key={s} className="choice">
                <input type="radio" name={`${id}-strike`} value={s} checked={profile.footStrike === s}
                  onChange={() => set("footStrike", s)} />
                {STRIKE_LABEL[s]}
              </label>
            ))}
          </div>
          <details className="help">
            <summary>How to tell</summary>
            <p>
              Look at the soles of a well-worn pair. Worn mostly at the back of the heel: heel
              striker. Worn under the ball of the foot: forefoot striker. Evenly worn: midfoot.
              Not sure? Keep "I don't know": it does not change the ranking.
            </p>
          </details>
        </fieldset>
      </fieldset>

      <fieldset>
        <legend>Run</legend>
        <div className="field">
          <label htmlFor={`${id}-distance`}>
            Typical distance <output htmlFor={`${id}-distance`}>{profile.distanceKm} km</output>
          </label>
          <input id={`${id}-distance`} type="range" min={0} max={100} step={0.5}
            value={kmToPosition(Math.min(KM_MAX, Math.max(KM_MIN, profile.distanceKm)))}
            aria-valuetext={`${profile.distanceKm} km`}
            onChange={(e) => set("distanceKm", positionToKm(Number(e.target.value)))} />
        </div>
        <fieldset className="field">
          <legend>Terrain <span className="hint">(none selected = all terrains)</span></legend>
          {TERRAINS.map((t) => (
            <label key={t} className="choice block">
              <input type="checkbox" checked={profile.terrains.includes(t)} onChange={() => toggleTerrain(t)} />
              <span>
                <strong>{TERRAIN_LABEL[t].name}</strong>
                <span className="hint"> {TERRAIN_LABEL[t].description}</span>
              </span>
            </label>
          ))}
        </fieldset>
      </fieldset>

      <fieldset>
        <legend>Preferences</legend>
        {PREFERENCE_AXES.map((axis) => {
          const text = AXIS_LABEL[axis];
          return (
            <div className="field" key={axis}>
              <label htmlFor={`${id}-${axis}`}>{text.title}</label>
              <input id={`${id}-${axis}`} type="range" min={0} max={100} step={5} value={profile.sliders[axis]}
                aria-valuetext={sliderText(profile.sliders[axis], text.left, text.right)}
                onChange={(e) => set("sliders", { ...profile.sliders, [axis]: Number(e.target.value) })} />
              <div className="slider-ends" aria-hidden="true">
                <span>{text.left}</span>
                <span>{text.right}</span>
              </div>
            </div>
          );
        })}
      </fieldset>
    </form>
  );
}

function sliderText(value: number, left: string, right: string): string {
  if (value === 50) return "No preference";
  return value < 50 ? `${left} (${50 - value}%)` : `${right} (${value - 50}%)`;
}
