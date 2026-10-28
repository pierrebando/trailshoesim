"""Brand alias table: recognise a brand however a retailer spells it."""

import re
import unicodedata
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

BRANDS_PATH = Path(__file__).resolve().parents[1] / "config" / "brands.yaml"


def fold(text: str) -> str:
    """Lower-case and remove accents, so 'Garoé', 'GAROE' and 'garoe' compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


@dataclass(frozen=True)
class Brand:
    """One canonical brand and its brand-specific cleaning rules."""

    name: str
    key: str  # used in model keys, e.g. "la sportiva"
    aliases: tuple[str, ...]  # folded, longest first
    strip_phrases: tuple[str, ...] = ()
    token_rewrites: tuple[tuple[re.Pattern[str], str], ...] = ()
    style_code: re.Pattern[str] | None = None
    name_numbers: tuple[str, ...] = ()  # e.g. "ultra 50": the 50 is not a version


class BrandTable:
    """All brands of brands.yaml, with lookups by alias."""

    def __init__(self, config: dict) -> None:
        """Build the table from the parsed brands.yaml."""
        self.brands: list[Brand] = []
        for name, spec in config["brands"].items():
            aliases = sorted({fold(a) for a in [name, *spec.get("aliases", [])]}, key=len)
            self.brands.append(
                Brand(
                    name=name,
                    key=fold(name).replace("-", " "),
                    aliases=tuple(reversed(aliases)),
                    strip_phrases=tuple(fold(p) for p in spec.get("strip_phrases", [])),
                    token_rewrites=tuple(
                        (re.compile(r["pattern"]), r["replace"])
                        for r in spec.get("token_rewrites", [])
                    ),
                    style_code=re.compile(spec["style_code"]) if spec.get("style_code") else None,
                    name_numbers=tuple(fold(n) for n in spec.get("name_numbers", [])),
                )
            )
        # Longest aliases first, so "hoka one one" wins over "hoka" and "on running" over "on".
        self._by_alias = sorted(
            ((alias, brand) for brand in self.brands for alias in brand.aliases),
            key=lambda pair: -len(pair[0]),
        )

    def canonical(self, raw: str | None) -> Brand | None:
        """Brand whose alias equals `raw` (e.g. a retailer's brand field), if any."""
        if not raw:
            return None
        folded = fold(raw).strip()
        return next((brand for alias, brand in self._by_alias if alias == folded), None)

    def find_in(self, folded_text: str) -> tuple[Brand, str] | None:
        """First brand alias found in a folded title: at the start, else anywhere.

        Short aliases (under 4 letters, like "on" or "ua") only count at the start,
        because as plain words they appear in ordinary text.
        """
        for alias, brand in self._by_alias:
            if re.match(rf"{re.escape(alias)}\b", folded_text):
                return brand, alias
        for alias, brand in self._by_alias:
            if len(alias) >= 4 and re.search(rf"\b{re.escape(alias)}\b", folded_text):
                return brand, alias
        return None


@cache
def load_brand_table(path: Path = BRANDS_PATH) -> BrandTable:
    """Load brands.yaml once."""
    return BrandTable(yaml.safe_load(path.read_text(encoding="utf-8")))
