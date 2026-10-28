"""Human review of uncertain matches: data/interim/needs_review.csv.

Each row is a PROPOSAL: "these title keys are one model, called `proposed_key`".
Fill the `decision` column, then re-run `python -m pipeline.normalize` (or this module):

    keep    accept the proposal (merge the titles under proposed_key)
    split   reject it (keep the titles as separate models)
    rename  accept it, but use the key written in `rename_to` (format brand|model|version)
    (empty) default: rows with merged_by_default = yes are merged, the others are not

Decisions are matched by `review_id`, which stays the same between runs, so they survive
when the file is regenerated.

    python -m pipeline.normalize.apply_review
"""

import csv
import sys
from collections.abc import Iterable
from pathlib import Path

from pipeline.normalize.matching import Decision, Proposal

VALID_DECISIONS = {"keep", "split", "rename"}
COLUMNS = [
    "review_id",
    "reason",
    "score",
    "merged_by_default",
    "proposed_key",
    "keys",
    "raw_titles",
    "retailer_urls",
    "decision",
    "rename_to",
    "notes",
]


def load_decisions(path: Path) -> dict[str, Decision]:
    """Read the decisions already written in needs_review.csv (missing file = none)."""
    if not path.exists():
        return {}
    decisions = {}
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            choice = (row.get("decision") or "").strip().lower()
            if not choice:
                continue
            if choice not in VALID_DECISIONS:
                raise ValueError(f"review {row['review_id']}: unknown decision {choice!r}")
            rename_to = (row.get("rename_to") or "").strip() or None
            if choice == "rename" and (rename_to is None or rename_to.count("|") != 2):
                raise ValueError(
                    f"review {row['review_id']}: rename_to must look like brand|model|version"
                )
            decisions[row["review_id"]] = Decision(row["review_id"], choice, rename_to)
    return decisions


def write_review_csv(
    path: Path,
    proposals: Iterable[Proposal],
    titles_of_key: dict[str, list[str]],
    urls_of_key: dict[str, list[str]],
    decisions: dict[str, Decision],
) -> int:
    """Write one row per proposal, carrying over existing decisions. Returns the row count."""
    rows = []
    for proposal in proposals:
        decision = decisions.get(proposal.review_id)
        titles = sorted({t for key in proposal.keys for t in titles_of_key.get(key, [])})
        urls = sorted({u for key in proposal.keys for u in urls_of_key.get(key, [])})
        rows.append(
            {
                "review_id": proposal.review_id,
                "reason": proposal.reason,
                "score": "" if proposal.score is None else proposal.score,
                "merged_by_default": "yes" if proposal.applied_by_default else "no",
                "proposed_key": proposal.proposed_key,
                "keys": " || ".join(proposal.keys),
                "raw_titles": " || ".join(titles),
                "retailer_urls": " ".join(urls),
                "decision": decision.decision if decision else "",
                "rename_to": (decision.rename_to or "") if decision else "",
                "notes": "",
            }
        )
    rows.sort(key=lambda row: (row["reason"], row["proposed_key"]))
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    """Re-run phase 2 so that the decisions in needs_review.csv are applied."""
    from pipeline.normalize.__main__ import main as normalize_main

    return normalize_main()


if __name__ == "__main__":
    sys.exit(main())
