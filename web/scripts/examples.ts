// Top 5 for three example runners, computed by the same engine as the app.
//   npm run examples
import { readFileSync } from "node:fs";
import { applyFilters } from "../src/engine/filters";
import { DEFAULT_FILTERS, DEFAULT_PROFILE, type Profile } from "../src/engine/profile";
import { rankShoes } from "../src/engine/scoring";
import type { Catalog, ScoringConfig } from "../src/engine/types";
import { computeWeights } from "../src/engine/weights";
import { encodeState } from "../src/url";

const read = (name: string) => JSON.parse(readFileSync(new URL(`../../data/processed/${name}`, import.meta.url), "utf-8"));
const catalog = read("shoes.json") as Catalog;
const config = read("scoring_config.json") as ScoringConfig;

const EXAMPLES: { title: string; profile: Profile }[] = [
  {
    title: "A. Light, fast runner: 60 kg, 12 km, road-to-trail and groomed paths, midfoot, wants dynamism",
    profile: {
      ...DEFAULT_PROFILE, weightKg: 60, distanceKm: 12, footStrike: "midfoot",
      terrains: ["road_to_trail", "groomed_mixed"],
      sliders: { cushioning_vs_ground_feel: 50, stability_vs_agility: 60, dynamic_vs_comfortable: 15 },
    },
  },
  {
    title: "B. Heavier ultra runner: 88 kg, 80 km, groomed and technical trails, heel striker, wants cushioning and comfort",
    profile: {
      ...DEFAULT_PROFILE, weightKg: 88, distanceKm: 80, footStrike: "heel",
      terrains: ["groomed_mixed", "technical_rocky"],
      sliders: { cushioning_vs_ground_feel: 20, stability_vs_agility: 40, dynamic_vs_comfortable: 75 },
    },
  },
  {
    title: "C. Mountain runner: 68 kg, 25 km, technical, mud and wet roots, forefoot, wants ground feel and agility",
    profile: {
      ...DEFAULT_PROFILE, weightKg: 68, distanceKm: 25, footStrike: "forefoot",
      terrains: ["technical_rocky", "muddy_soft", "wet_roots"],
      sliders: { cushioning_vs_ground_feel: 75, stability_vs_agility: 75, dynamic_vs_comfortable: 40 },
    },
  },
];

for (const { title, profile } of EXAMPLES) {
  const weights = computeWeights(profile, config);
  const ranking = rankShoes(applyFilters(catalog.shoes, DEFAULT_FILTERS, profile).passed, weights, config);
  console.log(`\n${title}\n  link: ?${encodeState({ profile, filters: DEFAULT_FILTERS, compare: [] })}`);
  console.log(`  ${ranking.ranked.length} ranked, ${ranking.notEnoughData.length} not enough data`);
  ranking.ranked.slice(0, 5).forEach((r, i) => {
    const name = [r.shoe.brand, r.shoe.model, r.shoe.version].filter(Boolean).join(" ");
    const why = r.explanation.reasons.map((p) => `${p.key} ${p.value.toFixed(1)}`).join(", ") || "-";
    const watch = [...r.explanation.drawbacks.map((p) => `${p.key} ${p.value.toFixed(1)}`),
      ...r.explanation.missing.map((m) => `no data: ${m.key}`)].join(", ") || "-";
    console.log(`  ${i + 1}. ${name.padEnd(34)} ${Math.round(r.score ?? 0)}/100  cov ${Math.round(r.coverage * 100)}%  ${r.shoe.confidence.level.padEnd(6)} why: ${why} | watch: ${watch}`);
  });
}
