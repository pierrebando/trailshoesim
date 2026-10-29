# data/manual/

Specs entered by hand by the student, for brands whose sites block automated access.

`missing_specs.csv` has one row per (model, field) to fill; regenerate it with
`python -m pipeline.specs.manual --template` (rows already filled are kept). For a row
to count, fill, from a product page read in a normal browser:

| Column | What to write |
|---|---|
| `value` | the number (`281`, `4.5`), `yes`/`no` (waterproof), `rock_plate`/`carbon`/`none`/`other` (plate), `standard;wide` (widths), or the name (foam, rubber) |
| `source_url` | the page where you read it |
| `retrieved_at` | the date you read it, `YYYY-MM-DD` |
| `raw_snippet` | the exact sentence of the page that gives the value, at most 30 words (the number must appear in it) |
| `entered_by` | your name or initials |

`python -m pipeline.specs.manual` checks the filled rows; `python -m pipeline.build`
refuses to run while a filled row is invalid. Filled values appear in the app with the
provenance "manual (student entry)".
