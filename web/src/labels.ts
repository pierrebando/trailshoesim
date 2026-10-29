// Words shown to the user for the engine's keys (UI text only, no logic).

import type { FilterName } from "./engine/filters";
import type { FootStrike, FootWidth, PreferenceAxis } from "./engine/profile";
import type { Terrain } from "./engine/types";
import type { TermKey, WeightComponent } from "./engine/weights";

export const TERM_LABEL: Record<TermKey, string> = {
  cushioning: "Cushioning",
  protection: "Protection",
  grip: "Grip",
  stability: "Stability",
  responsiveness: "Responsiveness",
  lightness: "Lightness",
  durability: "Durability",
  fit_width: "Roomy fit",
  ground_feel: "Ground feel",
  agility: "Agility",
  terrain: "Terrain match",
  drop_fit: "Drop for your foot strike",
};

export const TERRAIN_LABEL: Record<Terrain, { name: string; description: string }> = {
  road_to_trail: { name: "Road to trail", description: "Pavement, bike paths and hard-packed dirt." },
  groomed_mixed: { name: "Groomed trails", description: "Smooth single track, forest roads, some roots." },
  technical_rocky: { name: "Technical / rocky", description: "Rocks, scree, steep and uneven ground." },
  muddy_soft: { name: "Mud / soft ground", description: "Mud, wet grass, snow or loose soil." },
  wet_roots: { name: "Wet rock / roots", description: "Slippery rock slabs and wet roots." },
};

export const STRIKE_LABEL: Record<FootStrike, string> = {
  heel: "Heel",
  midfoot: "Midfoot",
  forefoot: "Forefoot",
  unknown: "I don't know",
};

export const WIDTH_LABEL: Record<FootWidth, string> = {
  narrow: "Narrow",
  standard: "Standard",
  wide: "Wide",
  extra_wide: "Extra wide",
  unknown: "I don't know",
};

export const AXIS_LABEL: Record<PreferenceAxis, { title: string; left: string; right: string }> = {
  cushioning_vs_ground_feel: { title: "Underfoot feel", left: "More cushioning", right: "More ground feel" },
  stability_vs_agility: { title: "Ride", left: "More stability", right: "More agility" },
  dynamic_vs_comfortable: { title: "Character", left: "More dynamic", right: "More comfortable" },
};

/** "Weighted 14 % for you because ..." (spec §6.5). */
export function becauseText(component: WeightComponent, terrains: Terrain[], strike: FootStrike): string {
  switch (component) {
    case "base":
      return "for your weight and distance";
    case "preference":
      return "because of your preference sliders";
    case "terrain":
      return terrains.length
        ? `because you selected ${terrains.map((t) => TERRAIN_LABEL[t].name.toLowerCase()).join(" and ")}`
        : "because it matters on every terrain";
    case "footStrike":
      return `because you are a ${STRIKE_LABEL[strike].toLowerCase()} striker`;
    case "footWidth":
      return "because of your foot width";
  }
}

export const FILTER_UNKNOWN_TEXT: Record<FilterName, string> = {
  price: "their price is unknown",
  brand: "",
  waterproof: "we don't know whether they are waterproof",
  drop: "their drop is unknown",
  width: "their available widths are unknown",
  gender: "",
};

export const SOURCE_LABEL: Record<string, string> = {
  runrepeat: "RunRepeat",
  believe_in_the_run: "Believe in the Run",
  esprit_trail: "Esprit Trail",
  tradeinn: "Tradeinn",
  glisshop: "Glisshop",
};

export const shoeName = (s: { brand: string; model: string; version: string | null }): string =>
  [s.brand, s.model, s.version].filter(Boolean).join(" ");

export const euro = (value: number): string =>
  value.toLocaleString("en-GB", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

/** Words for a similarity feature and the direction of a difference ("lighter", "deeper lugs"). */
export const FEATURE_WORDS: Record<string, { name: string; more: string; less: string }> = {
  cushioning: { name: "cushioning", more: "more cushioned", less: "less cushioned" },
  protection: { name: "protection", more: "more protective", less: "less protective" },
  grip: { name: "grip", more: "grippier", less: "less grippy" },
  stability: { name: "stability", more: "more stable", less: "less stable" },
  responsiveness: { name: "responsiveness", more: "more responsive", less: "less responsive" },
  lightness: { name: "lightness", more: "lighter", less: "heavier" },
  durability: { name: "durability", more: "more durable", less: "less durable" },
  fit_width: { name: "fit", more: "roomier", less: "narrower" },
  road_to_trail: { name: "road-to-trail use", more: "better from road to trail", less: "worse from road to trail" },
  groomed_mixed: { name: "groomed trails", more: "better on groomed trails", less: "worse on groomed trails" },
  technical_rocky: { name: "technical terrain", more: "better on technical terrain", less: "worse on technical terrain" },
  muddy_soft: { name: "mud", more: "better in mud", less: "worse in mud" },
  wet_roots: { name: "wet rock and roots", more: "better on wet rock", less: "worse on wet rock" },
  drop_mm: { name: "drop", more: "higher drop", less: "lower drop" },
  stack_heel_mm: { name: "stack height", more: "higher stack", less: "lower stack" },
  lug_depth_mm: { name: "lug depth", more: "deeper lugs", less: "shallower lugs" },
  waterproof: { name: "waterproofing", more: "waterproof", less: "not waterproof" },
};
