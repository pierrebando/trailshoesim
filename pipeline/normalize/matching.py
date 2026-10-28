"""Decide which title keys are the same model: exact key match first, then fuzzy.

Every non-exact decision is a `Proposal` ("these keys are one model, called X"). A
proposal is written to needs_review.csv, and the project owner's decision (keep / split /
rename, see apply_review.py) overrides the default on the next run.

Fuzzy matching is deliberately conservative: only keys of the same brand AND the same
version are compared, with `rapidfuzz.fuzz.ratio` on the model names. We do not use
`token_set_ratio`, because it scores "prodigio" vs "prodigio pro" as 100 (subset), and
those are different shoes.
"""

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from rapidfuzz import fuzz

from pipeline.normalize.versions import version_order


@dataclass(frozen=True)
class Proposal:
    """One row of needs_review.csv."""

    review_id: str
    reason: str
    score: float | None
    proposed_key: str
    keys: tuple[str, ...]
    applied_by_default: bool


@dataclass(frozen=True)
class Decision:
    """The project owner's decision on one proposal."""

    review_id: str
    decision: str  # "keep", "split" or "rename"
    rename_to: str | None = None


def split_key(key: str) -> tuple[str, str, str]:
    """'hoka|speedgoat|6' -> ('hoka', 'speedgoat', '6')."""
    brand, model, version = key.split("|")
    return brand, model, version


def make_review_id(reason: str, keys: tuple[str, ...]) -> str:
    """Stable id, so a decision still applies after the CSV is regenerated."""
    return hashlib.sha1(f"{reason}|{'|'.join(sorted(keys))}".encode()).hexdigest()[:10]


def _proposal(reason: str, score: float | None, target: str, keys: list[str], auto: bool):
    ordered = tuple(sorted(keys))
    return Proposal(make_review_id(reason, ordered), reason, score, target, ordered, auto)


def fuzzy_proposals(
    listing_counts: dict[str, int], merge_threshold: float, review_threshold: float
) -> list[Proposal]:
    """Pairs of keys (same brand, same version) whose model names are similar."""
    by_brand_version: dict[tuple[str, str], list[str]] = defaultdict(list)
    for key in listing_counts:
        brand, _, version = split_key(key)
        by_brand_version[(brand, version)].append(key)

    proposals = []
    for keys in by_brand_version.values():
        for key_a, key_b in combinations(sorted(keys), 2):
            score = fuzz.ratio(split_key(key_a)[1], split_key(key_b)[1])
            if score < review_threshold:
                continue
            # The key with more listings is probably the usual spelling.
            target = min((key_a, key_b), key=lambda k: (-listing_counts[k], len(k)))
            auto = score >= merge_threshold
            reason = "fuzzy_merge" if auto else "possible_duplicate"
            proposals.append(_proposal(reason, round(score, 1), target, [key_a, key_b], auto))
    return proposals


def flag_proposals(listing_counts: dict[str, int], warnings: dict[str, set[str]]) -> list[Proposal]:
    """Single keys that need a human look (not merged by default)."""
    numbered: dict[tuple[str, str], list[str]] = defaultdict(list)
    for key in listing_counts:
        brand, model, version = split_key(key)
        if version:
            numbered[(brand, model)].append(key)

    proposals = []
    for key in listing_counts:
        brand, model, version = split_key(key)
        if not version and numbered.get((brand, model)):
            # "Salomon Speedcross" next to "Speedcross 6": probably an older or newer
            # version whose number the retailer left out. We cannot tell which.
            latest = max(numbered[(brand, model)], key=lambda k: version_order(split_key(k)[2]))
            proposals.append(_proposal("version_unknown", None, latest, [key], False))
        if brand == "?":
            proposals.append(_proposal("unknown_brand", None, key, [key], False))
        for warning in sorted(warnings.get(key, ())):
            if "product code" in warning:
                proposals.append(_proposal("product_code_in_title", None, key, [key], False))
    return proposals


def is_accepted(proposal: Proposal, decisions: dict[str, Decision]) -> bool:
    """A human decision wins; without one, the proposal's default applies."""
    decision = decisions.get(proposal.review_id)
    if decision is None:
        return proposal.applied_by_default
    return decision.decision in ("keep", "rename")


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, a: str, b: str) -> None:
        self.parent[self.find(a)] = self.find(b)


def resolve(
    listing_counts: dict[str, int],
    proposals: list[Proposal],
    decisions: dict[str, Decision],
) -> tuple[dict[str, str], set[str]]:
    """Map every title key to its final model key.

    Returns (final_key_of, fuzzy_final_keys): the mapping, and the final keys that were
    built from more than one title key (match_confidence "fuzzy").
    """
    union = _UnionFind()
    forced_name: dict[str, str] = {}  # member key -> rename target
    for key in listing_counts:
        union.find(key)
    for proposal in proposals:
        if not is_accepted(proposal, decisions):
            continue
        decision = decisions.get(proposal.review_id)
        target = proposal.proposed_key
        if decision and decision.decision == "rename" and decision.rename_to:
            target = decision.rename_to
            forced_name[proposal.keys[0]] = target
        for key in proposal.keys:
            union.union(key, target)

    members: dict[str, list[str]] = defaultdict(list)
    for key in listing_counts:
        members[union.find(key)].append(key)

    final_key_of: dict[str, str] = {}
    fuzzy_final: set[str] = set()
    for keys in members.values():
        renamed = sorted(forced_name[k] for k in keys if k in forced_name)
        # A rename decision wins; otherwise the most common spelling names the model.
        final = renamed[0] if renamed else min(keys, key=lambda k: (-listing_counts[k], len(k)))
        for key in keys:
            final_key_of[key] = final
        if len(keys) > 1:
            fuzzy_final.add(final)
    return final_key_of, fuzzy_final
