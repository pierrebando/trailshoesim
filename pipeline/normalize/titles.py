"""Parse a raw retailer title into brand, model, version, gender and variant flags.

Example: "Hoka One One Speedgoat 6 GTX Men's Trail Running Shoes - Black"
         -> brand HOKA, model "Speedgoat", version "6", gender men, variants {gore_tex,
            waterproof}, key "hoka|speedgoat|6".

How it works: the title is split into tokens. Each cleaning step (brand, category,
generic words, variants, gender, colours...) marks some tokens as removed; what is left
is the model name, and its last version-like token is the version. Keeping tokens
(rather than editing a string) lets us show the original spelling of the model name
while building the key from a normalised spelling.
"""

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

from pipeline.models import Gender
from pipeline.normalize.brands import Brand, BrandTable, fold, load_brand_table

TITLES_PATH = Path(__file__).resolve().parents[1] / "config" / "titles.yaml"

ROMAN = {"ii": 2, "iii": 3, "iv": 4, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
VERSION_RE = re.compile(r"^(?:v?(\d{1,2})(?:\.(\d))?(\+)?|(ii|iii|iv|vi|vii|viii|ix|x))$")
# "410v9" (New Balance) or "tr2" (Saucony "Ride TR2"): a name part glued to a version.
# The "v" is required after digits, otherwise "410" would be read as "41" version "0".
GLUED_VERSION_RE = re.compile(r"^(?:([a-z]*\d{2,4})v|(tr))(\d{1,2})$")


@dataclass
class _Token:
    word: int  # index of the original whitespace-separated word
    norm: str  # folded, normalised spelling used for the key
    display: str | None = None  # spelling to show, when it differs from the original word
    removed: str | None = None  # why the token was removed, None if still part of the name


@dataclass
class ParsedTitle:
    """Everything we could read from one title."""

    raw_title: str
    brand: str | None
    brand_key: str | None
    model: str
    model_key: str
    version: str | None
    gender: Gender | None
    category: str  # "trail", "gravel" or "kids"
    variants: frozenset[str]
    removed_words: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        """Canonical model key, e.g. 'hoka|speedgoat|6'. Gender is deliberately not in it."""
        return f"{self.brand_key or '?'}|{self.model_key}|{self.version or ''}"


@dataclass(frozen=True)
class TitleVocabulary:
    """The compiled contents of titles.yaml."""

    categories: dict[str, list[re.Pattern[str]]]
    generic: list[re.Pattern[str]]
    variants: dict[str, list[re.Pattern[str]]]
    genders: dict[Gender, list[re.Pattern[str]]]
    colours: frozenset[str]
    protected: frozenset[str]
    synonyms: dict[str, str]
    version_suffixes: frozenset[str]
    sku_min_length: int


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern) for pattern in patterns]


@cache
def load_vocabulary(path: Path = TITLES_PATH) -> TitleVocabulary:
    """Load titles.yaml once."""
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TitleVocabulary(
        categories={name: _compile(p) for name, p in config["categories"].items()},
        generic=_compile(config["generic_phrases"]),
        variants={name: _compile(p) for name, p in config["variants"].items()},
        genders={Gender(name): _compile(p) for name, p in config["genders"].items()},
        colours=frozenset(config["colours"]),
        protected=frozenset(config["protected_phrases"]),
        synonyms=config["token_synonyms"],
        version_suffixes=frozenset(config["version_suffix_tokens"]),
        sku_min_length=config["matching"]["sku_min_length"],
    )


def repair_encoding(text: str) -> str:
    """Fix text that was UTF-8 decoded as Latin-1 ('GORE-TEXÂ®' -> 'GORE-TEX®')."""
    if "Ã" in text or "Â" in text:
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text.replace("Â", "")
    return text


def _tokenise(title: str) -> tuple[list[str], list[_Token]]:
    words = re.sub(r"[®™©]", "", repair_encoding(title)).split()
    tokens = []
    for index, word in enumerate(words):
        # Hyphens and slashes separate parts ("Gel-Trabuco", "Black/White"); dots and "+"
        # stay because they belong to versions ("2.0", "9+") and names ("Rain.Rdy").
        for part in re.split(r"[-/,()|]+", fold(word)):
            part = part.strip(".:;'\"")
            if part:
                tokens.append(_Token(word=index, norm=part))
    return words, tokens


def _active(tokens: list[_Token]) -> list[_Token]:
    return [token for token in tokens if token.removed is None]


def _remove_pattern(
    tokens: list[_Token], pattern: re.Pattern[str], reason: str, first_only: bool = False
) -> bool:
    """Mark the tokens covered by `pattern` as removed. Returns True if it matched."""
    active = _active(tokens)
    text, spans, position = "", [], 0
    for token in active:
        spans.append((position, position + len(token.norm)))
        text += token.norm + " "
        position += len(token.norm) + 1
    matched = False
    for match in pattern.finditer(text):
        for token, (start, end) in zip(active, spans, strict=True):
            if start >= match.start() and end <= match.end():
                token.removed = reason
                matched = True
        if first_only and matched:
            break
    return matched


def _remove_brand(tokens: list[_Token], brand: Brand) -> None:
    for alias in brand.aliases:
        # Only the first occurrence: a short alias ("on") can also be an ordinary word.
        if _remove_pattern(tokens, re.compile(rf"\b{re.escape(alias)}\b"), "brand", True):
            return


def _original_part(word: str, norm: str) -> str:
    """The part of `word` spelling `norm`, in its original case ("TR-6", "tr" -> "TR")."""
    start = fold(word).find(norm)
    if start < 0 or len(fold(word)) != len(word):
        return norm
    return word[start : start + len(norm)]


def version_value(token: str) -> str | None:
    """'v9' -> '9', 'III' -> '3', '2.0' -> '2', '02' -> '2', '9+' -> '9+'; None if not a version."""
    match = VERSION_RE.match(token)
    if not match:
        return None
    number, decimal, plus, roman = match.groups()
    if roman:
        return str(ROMAN[roman])
    value = str(int(number))
    if decimal and decimal != "0":
        value += f".{decimal}"
    return value + (plus or "")


def _normalise_tokens(
    tokens: list[_Token], words: list[str], brand: Brand | None, vocab: TitleVocabulary
) -> None:
    """Split glued versions, apply brand rewrites and synonyms, drop codes."""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.removed is None:
            glued = GLUED_VERSION_RE.match(token.norm)
            if glued and not VERSION_RE.match(token.norm):
                digits_part, tr_part, version_part = glued.groups()
                name_part = digits_part or tr_part
                original = words[token.word]
                # Show the name part with its original case: "MT410v5" -> "MT410".
                token.display = (
                    original[: len(name_part)] if fold(original).startswith(name_part) else None
                )
                token.norm = name_part
                tokens.insert(index + 1, _Token(word=token.word, norm="v" + version_part))
            if brand:
                for pattern, replacement in brand.token_rewrites:
                    token.norm = pattern.sub(replacement, token.norm)
                if brand.style_code and brand.style_code.match(token.norm):
                    token.removed = "style code"
            has_letter = re.search(r"[a-z]", token.norm)
            has_digit = re.search(r"\d", token.norm)
            if len(token.norm) >= vocab.sku_min_length and has_letter and has_digit:
                token.removed = "product code"
        index += 1


def _find_version(tokens: list[_Token], vocab: TitleVocabulary, brand: Brand | None) -> str | None:
    """The version is the last version-like token, optionally followed by a suffix ('TR')."""
    active = _active(tokens)
    position = len(active) - 1
    while position > 0 and active[position].norm in vocab.version_suffixes:
        position -= 1
    if brand and position > 0:
        tail = f"{active[position - 1].norm} {active[position].norm}"
        if tail in brand.name_numbers:
            return None
    # position > 0: a version needs at least one name token before it ("Joma TR-6" ok).
    if position > 0:
        value = version_value(active[position].norm)
        if value is not None:
            active[position].removed = "version"
            return value
    return None


def parse_title(
    raw_title: str,
    retailer_brand: str | None = None,
    brands: BrandTable | None = None,
    vocab: TitleVocabulary | None = None,
) -> ParsedTitle:
    """Parse one title. `retailer_brand` (the retailer's own brand field) is preferred."""
    brands = brands or load_brand_table()
    vocab = vocab or load_vocabulary()
    words, tokens = _tokenise(raw_title)
    warnings: list[str] = []

    brand = brands.canonical(retailer_brand)
    found = brands.find_in(" ".join(t.norm for t in tokens))
    if brand is None and found:
        brand = found[0]
    if brand is None and retailer_brand and retailer_brand.strip():
        # The retailer states the brand; trust it even if brands.yaml does not know it yet.
        name = retailer_brand.strip()
        brand = Brand(name=name, key=fold(name).replace("-", " "), aliases=(fold(name),))
        warnings.append(f"brand {name!r} is not in brands.yaml")
    if brand:
        _remove_brand(tokens, brand)
    else:
        warnings.append(f"unknown brand (retailer brand field: {retailer_brand!r})")

    category = "trail"
    for name, patterns in vocab.categories.items():
        for pattern in patterns:
            if _remove_pattern(tokens, pattern, name) and category == "trail":
                category = name
    for pattern in vocab.generic:
        _remove_pattern(tokens, pattern, "generic")

    variants: set[str] = set()
    for name, patterns in vocab.variants.items():
        for pattern in patterns:
            if _remove_pattern(tokens, pattern, name):
                variants.add(name)
    if "gore_tex" in variants:
        variants.add("waterproof")
    if "extra_wide" in variants:
        variants.discard("wide")

    gender = None
    for candidate, patterns in vocab.genders.items():
        for pattern in patterns:
            if _remove_pattern(tokens, pattern, "gender"):
                gender = gender or candidate

    # Colours only at the end of the title, and never inside a protected name ("Mont Blanc").
    active = _active(tokens)
    for position in range(len(active) - 1, -1, -1):
        token = active[position]
        previous = active[position - 1].norm if position > 0 else ""
        if token.norm not in vocab.colours or f"{previous} {token.norm}" in vocab.protected:
            break
        token.removed = "colour"

    if brand:
        for phrase in brand.strip_phrases:
            _remove_pattern(tokens, re.compile(rf"\b{re.escape(phrase)}\b"), "marketing")
    _normalise_tokens(tokens, words, brand, vocab)
    version = _find_version(tokens, vocab, brand)

    model_tokens = _active(tokens)
    # Synonyms only for the LAST word of the name: "Charged Bandit Trail" = "Charged Bandit
    # TR", but "Trail Glove" must stay "trail glove".
    if model_tokens:
        last = model_tokens[-1]
        last.norm = vocab.synonyms.get(last.norm, last.norm)
    if not model_tokens:
        warnings.append("no model name left after cleaning")
    if any(t.removed == "product code" for t in tokens):
        warnings.append("title contains a product code")

    display_words: list[str] = []
    for word_index in sorted({token.word for token in model_tokens}):
        parts = [t for t in tokens if t.word == word_index]
        kept = [t for t in parts if t.removed is None]
        if len(kept) == len(parts) and kept[0].display is None:
            display_words.append(words[word_index])  # whole word kept: original spelling
        else:
            display_words.append(
                "-".join(t.display or _original_part(words[word_index], t.norm) for t in kept)
            )

    return ParsedTitle(
        raw_title=raw_title,
        brand=brand.name if brand else None,
        brand_key=brand.key if brand else None,
        model=" ".join(display_words),
        model_key=" ".join(token.norm for token in model_tokens),
        version=version,
        gender=gender,
        category=category,
        variants=frozenset(variants),
        removed_words=sorted({f"{t.norm} ({t.removed})" for t in tokens if t.removed}),
        warnings=warnings,
    )
