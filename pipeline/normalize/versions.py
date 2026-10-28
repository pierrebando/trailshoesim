"""Compare versions of the same model line ("Speedgoat 5" vs "Speedgoat 6")."""

import re


def version_order(version: str | None) -> tuple[float, int]:
    """Sortable value of a version: '6' < '6.5' < '9' < '9+'. Unknown sorts first."""
    if not version:
        return (-1.0, 0)
    match = re.match(r"^(\d+(?:\.\d+)?)(\+)?$", version)
    if not match:
        return (-1.0, 0)
    return (float(match.group(1)), 1 if match.group(2) else 0)


def line_key(key: str) -> str:
    """The model line of a key, without its version: 'hoka|speedgoat|6' -> 'hoka|speedgoat'."""
    return key.rsplit("|", 1)[0]
