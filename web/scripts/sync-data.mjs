// Copy the pipeline's output into web/public/data/ so Vite serves it next to the app.
//
// data/processed/scoring_config.json is the JSON copy of pipeline/config/scoring.yaml
// written by `python -m pipeline.build`: the browser engine reads exactly the constants
// the pipeline used. This script refuses to copy files whose scoring versions differ.
import { copyFileSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "..", "..", "data", "processed");
const target = join(here, "..", "public", "data");
const FILES = ["shoes.json", "meta.json", "scoring_config.json"];

const read = (name) => JSON.parse(readFileSync(join(source, name), "utf-8"));
const shoesVersion = read("shoes.json").scoring_config_version;
const configVersion = read("scoring_config.json").version;
if (shoesVersion !== configVersion) {
  console.error(
    `shoes.json was built with scoring ${shoesVersion} but scoring_config.json is ` +
      `${configVersion}: run \`python -m pipeline.build\` again.`,
  );
  process.exit(1);
}
mkdirSync(target, { recursive: true });
for (const name of FILES) copyFileSync(join(source, name), join(target, name));
console.log(`copied ${FILES.join(", ")} (scoring ${configVersion}) to web/public/data/`);
