# Trail Shoe Finder

A static web app that recommends trail running shoes from a runner profile and explains
every recommendation.

- The **data** (shoes on sale at three French retailers, manufacturer specs, expert review
  excerpts) is collected and scored **offline** by a Python pipeline (`pipeline/`).
- The **web app** (`web/`, GitHub Pages) reads one JSON file and does the ranking in the browser.

Where to start reading:

1. `CLAUDE.md` — project summary, decisions, rules, commands.
2. `docs/scoring-spec.md` — how shoes are scored and ranked.
3. `pipeline/models.py` — the data model of a shoe.

Quickstart (Python 3.11+):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
