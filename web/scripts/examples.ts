// Top 5 for six realistic runners, computed by the same engine as the app.
//   npm run examples
import { readFileSync } from "node:fs";
import { applyFilters } from "../src/engine/filters";
import { DEFAULT_FILTERS, DEFAULT_PROFILE, type Filters, type Profile } from "../src/engine/profile";
import { rankShoes, type Point } from "../src/engine/scoring";
import { similarToModel } from "../src/engine/similarity";
import type { Catalog, ScoringConfig } from "../src/engine/types";
import { computeWeights } from "../src/engine/weights";
import { encodeState } from "../src/url";

const read = (name: string) => JSON.parse(readFileSync(new URL(`../../data/processed/${name}`, import.meta.url), "utf-8"));
const catalog = read("shoes.json") as Catalog;
const config = read("scoring_config.json") as ScoringConfig;
const name = (s: { brand: string; model: string; version: string | null }) => [s.brand, s.model, s.version].filter(Boolean).join(" ");
const points = (list: Point[]) => list.map((p) => `${p.key} ${p.value.toFixed(1)}`).join(", ");
const sliders = (s1: number, s2: number, s3: number) => ({ cushioning_vs_ground_feel: s1, stability_vs_agility: s2, dynamic_vs_comfortable: s3 });

const EXAMPLES: { title: string; profile: Profile; filters?: Partial<Filters> }[] = [
  {
    title: "1. Heavy runner, technical terrain, ultra: 92 kg, 100 km, technical/rocky, heel striker, wants cushioning",
    profile: { ...DEFAULT_PROFILE, weightKg: 92, distanceKm: 100, footStrike: "heel", terrains: ["technical_rocky"], sliders: sliders(20, 35, 70) },
  },
  {
    title: "2. Light runner, groomed trails, 10 km: 58 kg, 10 km, groomed, midfoot, no preference",
    profile: { ...DEFAULT_PROFILE, weightKg: 58, distanceKm: 10, footStrike: "midfoot", terrains: ["groomed_mixed"] },
  },
  {
    title: "3. Forefoot striker wanting a low drop: 68 kg, 21 km, all terrains, forefoot, filter drop <= 6 mm",
    profile: { ...DEFAULT_PROFILE, weightKg: 68, distanceKm: 21, footStrike: "forefoot", sliders: sliders(65, 60, 50) },
    filters: { dropMaxMm: 6 },
  },
  {
    title: "4. Budget-limited beginner: 78 kg, 12 km, road-to-trail and groomed, unknown strike, comfort, max 90 EUR",
    profile: { ...DEFAULT_PROFILE, weightKg: 78, distanceKm: 12, terrains: ["road_to_trail", "groomed_mixed"], sliders: sliders(35, 40, 75) },
    filters: { maxPriceEur: 90 },
  },
  {
    title: "5. Wet and muddy terrain: 72 kg, 25 km, mud/soft and wet rock/roots, midfoot",
    profile: { ...DEFAULT_PROFILE, weightKg: 72, distanceKm: 25, footStrike: "midfoot", terrains: ["muddy_soft", "wet_roots"] },
  },
];

for (const { title, profile, filters: extra } of EXAMPLES) {
  const filters = { ...DEFAULT_FILTERS, ...extra };
  const weights = computeWeights(profile, config);
  const outcome = applyFilters(catalog.shoes, filters, profile);
  const ranking = rankShoes(outcome.passed, weights, config);
  const hidden = catalog.shoes.length - outcome.passed.length;
  console.log(`\n${title}\n  link: ?${encodeState({ profile, filters, compare: [] })}`);
  console.log(`  ${ranking.ranked.length} ranked, ${ranking.notEnoughData.length} not enough data, ${hidden} hidden by filters`);
  ranking.ranked.slice(0, 5).forEach((r, i) => {
    const watch = [points(r.explanation.drawbacks), ...r.explanation.missing.map((m) => `no data: ${m.key}`)].filter(Boolean).join(", ") || "-";
    console.log(`  ${i + 1}. ${name(r.shoe).padEnd(32)} ${Math.round(r.score ?? 0)}/100 (${r.shoe.confidence.level}) why: ${points(r.explanation.reasons) || "-"} | watch: ${watch}`);
  });
}

const reference = catalog.shoes.find((s) => s.id === "saucony-peregrine-15")!;
const liked = similarToModel(reference, catalog.shoes, DEFAULT_FILTERS, DEFAULT_PROFILE, config);
console.log(`\n6. "I like the ${name(reference)}" (default filters; ${liked.notComparable} shoes not comparable)`);
liked.similar.slice(0, 5).forEach((s, i) => {
  const close = s.closest.map((d) => d.feature).join(", ");
  const far = s.furthest.map((d) => `${d.feature} ${d.difference > 0 ? "+" : "-"}`).join(", ");
  console.log(`  ${i + 1}. ${name(s.shoe).padEnd(32)} ${Math.round(s.similarity ?? 0)}% similar${s.otherVersion ? " (other version)" : ""}; close on ${close}; differs ${far}`);
});
