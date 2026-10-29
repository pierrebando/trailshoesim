# web/ (phase 7)

Static web app: React + Vite + TypeScript, no backend. It loads `data/shoes.json`,
`meta.json` and `scoring_config.json` with relative URLs, so the built site works under
any sub-path (GitHub Pages). Pages are hash routes (`#/shoe/<id>`); the profile, filters
and comparator live in the query string, so a result can be shared.

```
npm install        # once
npm run dev        # copies ../data/processed/*.json to public/data/, then starts Vite
npm test           # Vitest: the engine (filters, weights, scoring, similarity) and URL state
npm run build      # type check + static site in dist/
npm run examples   # top 5 for three example runners
```

| Folder | Content |
|---|---|
| `src/engine/` | PURE TypeScript, no React: `filters.ts` (§1), `weights.ts` (§5), `scoring.ts` (§6), `similarity.ts` (§7), `confidence.ts` (§8). Section numbers refer to `docs/scoring-spec.md`. |
| `src/components/`, `src/pages/` | UI only. |
| `scripts/sync-data.mjs` | Copies the pipeline output; refuses if `shoes.json` and `scoring_config.json` have different scoring versions. |

The constants come from `data/processed/scoring_config.json`, the JSON copy of
`pipeline/config/scoring.yaml` written by `python -m pipeline.build`, so the browser uses
exactly the numbers the pipeline used.
