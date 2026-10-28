"""A small robots.txt parser that understands `*` and `$` wildcards.

Python's built-in `urllib.robotparser` only does prefix matching, so it misreads rules
such as `Disallow: */listado.php*` that real sites use. This module follows the rules
published by Google (RFC 9309): the most specific (longest) matching rule wins, and
`Allow` wins a tie.
"""

import re
from dataclasses import dataclass, field


@dataclass
class _Group:
    agents: list[str] = field(default_factory=list)
    rules: list[tuple[bool, str]] = field(default_factory=list)  # (allow?, pattern)


def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    anchored = pattern.endswith("$")
    if anchored:
        pattern = pattern[:-1]
    regex = ".*".join(re.escape(part) for part in pattern.split("*"))
    return re.compile(regex + ("$" if anchored else ""))


class RobotsRules:
    """The rules of one robots.txt file, for one user-agent."""

    def __init__(self, robots_txt: str, user_agent: str) -> None:
        """Parse `robots_txt` and keep the group that applies to `user_agent`."""
        groups = self._parse(robots_txt)
        token = user_agent.split("/")[0].lower()
        specific = [g for g in groups if any(a != "*" and a in token for a in g.agents)]
        generic = [g for g in groups if "*" in g.agents]
        chosen = specific or generic
        self._rules = [rule for group in chosen for rule in group.rules]

    @staticmethod
    def _parse(text: str) -> list[_Group]:
        groups: list[_Group] = []
        current: _Group | None = None
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                # Consecutive User-agent lines share the rules that follow them.
                if current is None or current.rules:
                    current = _Group()
                    groups.append(current)
                current.agents.append(value.lower())
            elif key in ("allow", "disallow") and current is not None:
                if value:  # an empty Disallow means "allow everything"
                    current.rules.append((key == "allow", value))
        return groups

    def is_allowed(self, path_and_query: str) -> bool:
        """Return True if the URL path (with its query string) may be fetched."""
        best_length = -1
        allowed = True
        for allow, pattern in self._rules:
            if _pattern_to_regex(pattern).match(path_and_query):
                longer = len(pattern) > best_length
                if longer or (len(pattern) == best_length and allow):
                    best_length, allowed = len(pattern), allow
        return allowed
