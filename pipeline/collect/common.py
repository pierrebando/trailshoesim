"""Things every collector shares."""

from dataclasses import dataclass, field

from pipeline.models import RetailerListing


@dataclass
class CollectResult:
    """Everything one collection run produced, for the output file and the report."""

    listings: list[RetailerListing] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    truncated_pages: list[str] = field(default_factory=list)
    excluded_not_trail: list[str] = field(default_factory=list)
    category_pages: int = 0
    brands_seen: set[str] = field(default_factory=set)
