# pipeline/config/

`scoring.yaml` holds every numeric constant used by the scoring system (anchor points,
weights, thresholds, lookup tables). `docs/scoring-spec.md` explains what each one means.
Change a number here, not in code. The build step also exports this file as JSON for the
web app, so the Python pipeline and the browser always use the same values.
