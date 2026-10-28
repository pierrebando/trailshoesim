"""Read specs from the text of a manufacturer product page, quoting the page for each value.

The extractor looks for LABELS ("Poids", "Drop", "Profondeur des crampons", "Outsole"...)
in French and English and reads the value right after the label, up to the next label.
Every value comes with `snippet`: whole words of the page around it (max 30). Before a
value is accepted, `verify` checks that the snippet is in the page text and that the
characters the value was read from (`proof`) are in the snippet. A value that is not on
the page cannot get through.

Steps that are not plain copying are documented in models.Derivation (oz -> g, drop from
stacks, heel/forefoot order from the drop...). Implausible numbers are skipped, not fixed.
"""

import re
from dataclasses import dataclass

from pipeline.models import Derivation, FoamFamily, Plate, Width
from pipeline.normalize.brands import fold

NUM = r"\d+(?:[.,]\d+)?"
OZ_TO_G = 28.3495
MAX_SNIPPET_WORDS = 30
WINDOW = 90  # characters read after a label

LABELS = {
    "weight": r"\bpoids\b|\bweight\b",
    "drop": r"\bdrop\b|d[ée]nivel[ée] talon|heel[- ]to[- ]toe(?: drop| offset)?",
    "stack": r"hauteur (?:de (?:la )?semelle|du talon|au talon|totale)"
    r"|[ée]paisseur de (?:la )?semelle|\bstack(?: height)?\b",
    "lug": r"(?:profondeur|longueur|hauteur) des crampons|\blug depth\b|\blugs?\b|\bcrampons?\b",
    "midsole": r"semelles? interm[ée]diaires?|semelle intercalaire|\bmidsole\b",
    "cushion": r"\bamorti\b|\bmousse\b",
    "outsole": r"semelles? ext[ée]rieures?|\boutsole\b|semelle d'usure",
    # Insole labels only end windows, and stop "mousse" from naming the insole's foam.
    "insole": r"semelle de propret[ée]|semelle int[ée]rieure|assise plantaire|\binsole\b"
    r"|\bfootbed\b",
    "upper": r"\btige\b|\bupper\b",
    "width": r"largeur(?: de (?:la )?forme)?|\bwidth\b",
}
ALL_LABELS = re.compile("|".join(f"(?:{p})" for p in LABELS.values()), re.IGNORECASE)

# Plausible ranges. Above 480 g, a "weight" is almost always the weight of the PAIR
# (Mizuno shows 620 g for a shoe whose sibling page shows 321 g), so it is skipped.
PLAUSIBLE = {"weight": (120, 480), "drop": (0, 16), "stack": (5, 60), "lug": (1, 10)}
RUBBER_WORDS = re.compile(
    r"vibram|megagrip|litebase|michelin|contagrip|pomoca|grip|\btrac\b|frixion|rubber|caoutchouc|gomme",
    re.IGNORECASE,
)
COMPOUND = re.compile(
    r"vibram®?(?:\s+(?:litebase|megagrip|xs[ -]?trek|ecostep|fuga|tc5\+|traction lug|arctic grip"
    r"|idrogrip))+|(?:litebase et )?megagrip(?: pour vibram®?)?"
    r"|michelin®?(?: (?:outdoor|trail|rubber))?",
    re.IGNORECASE,
)
# A foam name: up to three capitalised words ("BOUNCE FOAM", "LOWA® DYNAEVA®", "EExpure").
FOAM_NAME = re.compile(r"(?:[A-Z][\w®™+\-]*|[a-z]*[A-Z]{2,}[\w®™+]*)(?:\s+[A-Z0-9][\w®™+\-]*){0,2}")
PLATE = re.compile(
    r"sans plaque|no plate|rock[ -]?plate|rock ?shield|plaque (?:anti[- ]?roches?|de protection"
    r"|en carbone|carbone|en tpu|tpu|de propulsion)|carbon[ -](?:fib(?:er|re) )?plate"
    r"|propulsion plate|protection plate",
    re.IGNORECASE,
)
WATERPROOF = re.compile(r"gore[- ]?tex|\bgtx\b|waterproof|imperm[ée]able|\bwp\b", re.IGNORECASE)
WIDTH_WORDS = {
    "standard": Width.STANDARD,
    "normal": Width.STANDARD,
    "moyen": Width.STANDARD,
    "moyenne": Width.STANDARD,
    "regular": Width.STANDARD,
    "medium": Width.STANDARD,
    "large": Width.WIDE,
    "wide": Width.WIDE,
    "etroit": Width.NARROW,
    "etroite": Width.NARROW,
    "narrow": Width.NARROW,
}
YEAR = re.compile(
    r"(?:collection|saison|season)\s*:?\s*(?:printemps|[ée]t[ée]|automne|hiver|spring|summer"
    r"|fall|autumn|winter|ss|fw|aw)?[\s/-]*(20[12]\d)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Found:
    """One extracted value and the page words that prove it."""

    value: object
    snippet: str
    proof: str  # the exact characters of the page the value was read from
    derivation: Derivation | None = None
    note: str | None = None


def to_float(text: str) -> float:
    """'9,5' -> 9.5."""
    return float(text.replace(",", "."))


def snippet_around(text: str, start: int, end: int, max_words: int = MAX_SNIPPET_WORDS) -> str:
    """Whole words of `text` covering [start, end), padded with context up to `max_words`."""
    while start > 0 and not text[start - 1].isspace():
        start -= 1  # never cut a word in two: the snippet must stay verbatim
    while end < len(text) and not text[end].isspace():
        end += 1
    core = text[start:end].split()
    room = max(0, max_words - len(core))
    before = text[:start].split()[len(text[:start].split()) - room // 2 :] if room else []
    after = text[end:].split()[: room - len(before)] if room else []
    return " ".join([*before, *core, *after][:max_words])


def found_at(text: str, label_start: int, start: int, end: int, value, **extra) -> Found:
    """A Found whose proof is text[start:end]; the label is included when it fits."""
    span_start = label_start if len(text[label_start:end].split()) <= 24 else start
    return Found(value, snippet_around(text, span_start, end), text[start:end], **extra)


def verify(found: Found, text: str) -> bool:
    """True if the snippet is on the page and contains the characters the value came from."""
    return bool(found.proof) and found.snippet in text and found.proof in found.snippet


def _windows(text: str, field: str) -> list[tuple[int, int, int]]:
    """(label start, label end, window end) for each label of `field`: up to the next label."""
    spans = [(m.start(), m.end(), m.group()) for m in ALL_LABELS.finditer(text)]
    windows = []
    for index, (start, end, label) in enumerate(spans):
        if not re.fullmatch(LABELS[field], label, re.IGNORECASE):
            continue
        stop = min(end + WINDOW, len(text))
        if index + 1 < len(spans):
            stop = min(stop, spans[index + 1][0])
        windows.append((start, end, max(stop, end)))
    return windows


def _plausible(field: str, value: float) -> bool:
    low, high = PLAUSIBLE[field]
    return low <= value <= high


def _millimetres(text: str, field: str) -> Found | None:
    """First plausible '<label> ... N mm' value (drop, lug depth)."""
    for start, end, stop in _windows(text, field):
        match = None
        if field == "drop":  # "Drop 4 (28 mm - 24 mm)": the number comes before the bracket
            match = re.compile(rf"\s*[:|]?\s*({NUM})\s*\(").match(text, end, stop)
        match = match or re.compile(rf"({NUM})\s*mm").search(text, end, stop)
        if match and _plausible(field, to_float(match.group(1))):
            return found_at(text, start, match.start(1), match.end(), to_float(match.group(1)))
    if field == "lug":  # inline phrase: "des crampons de 3,5 mm"
        match = re.search(rf"crampons (?:de |d'une profondeur de )({NUM})\s*mm", text, re.I)
        if match and _plausible("lug", to_float(match.group(1))):
            return found_at(
                text, match.start(), match.start(1), match.end(), to_float(match.group(1))
            )
    return None


def _grams(amount: str, unit: str, grams_in_brackets: str | None):
    """(grams, derivation) of a weight written in g or oz; brackets give grams directly."""
    if grams_in_brackets:
        return to_float(grams_in_brackets), None
    if unit.lower() == "oz":
        return round(to_float(amount) * OZ_TO_G), Derivation.OZ_TO_G
    return to_float(amount), None


def _weights(text: str, page_is_women: bool, skipped: dict[str, str]) -> dict[str, Found]:
    """weight_g / weight_women_g, with the size reference in `note` when the page gives one."""
    found: dict[str, Found] = {}
    by_gender = (("weight_g", "homme|hommes|men'?s?"), ("weight_women_g", "femme|femmes|women'?s?"))
    for start, end, stop in _windows(text, "weight"):
        # "POIDS Homme 9,5 oz (271 g) Femme 8,4 oz (239 g)"
        for key, gender in by_gender:
            pattern = rf"\b({gender})\b\D{{0,15}}?({NUM})\s*(oz|g)\b(?:\s*\(\s*({NUM})\s*g\s*\))?"
            match = re.compile(pattern, re.IGNORECASE).search(text, end, stop)
            if match and key not in found:
                grams, derivation = _grams(match.group(2), match.group(3), match.group(4))
                if _plausible("weight", grams):
                    found[key] = found_at(
                        text,
                        start,
                        match.start(2),
                        match.end(),
                        grams,
                        derivation=derivation,
                        note=f"{match.group(1)} (size not stated)",
                    )
        if found:
            return found
        match = re.compile(rf"({NUM})\s*(g|grammes?|gr|oz)\b", re.IGNORECASE).search(
            text, end, stop
        )
        derivation, unit_label = None, False
        if not match:  # "Poids (g) : | 830": the unit is in the label
            match = re.compile(r"\s*\(g\)[\s:|]*(\d{2,3})\b()", re.IGNORECASE).match(
                text, end, stop
            )
            unit_label = bool(match)
        if match:
            grams, derivation = _grams(match.group(1), match.group(2) or "g", None)
            if not _plausible("weight", grams):
                skipped["weight_g"] = f"page shows {grams:g} g: not plausible for one shoe (pair?)"
            else:
                reference = re.search(
                    r"\(([^)]{1,40})\)|taille[^-|:]{1,20}", text[end : match.start()], re.I
                )
                note = reference.group(0).strip(" ()") if reference else "size reference not stated"
                key = "weight_women_g" if page_is_women else "weight_g"
                found[key] = found_at(
                    text,
                    start,
                    match.start(1),
                    match.end(),
                    grams,
                    derivation=Derivation.UNIT_FROM_LABEL if unit_label else derivation,
                    note=note,
                )
                return found
    # Value written before its label: "290 | Poids (Taille: 42)" (Scarpa).
    match = re.search(r"\b(\d{3})\s*\|\s*Poids\s*\((Taille\s*:\s*[\w.,]+)\)", text, re.IGNORECASE)
    if match and _plausible("weight", float(match.group(1))):
        found["weight_women_g" if page_is_women else "weight_g"] = Found(
            float(match.group(1)),
            snippet_around(text, match.start(), match.end()),
            match.group(),
            Derivation.UNIT_FROM_LABEL,
            f"grams implied (number written without unit); {match.group(2)}",
        )
    return found


def _stacks(text: str, drop: Found | None) -> tuple[Found | None, Found | None]:
    """(heel, forefoot). A pair without labels is ordered by the stated drop, or skipped."""
    for start, end, stop in _windows(text, "stack") + _windows(text, "drop"):
        window = text[end:stop]
        heel = re.search(rf"talon\D{{0,10}}({NUM})\s*mm", window, re.I)
        fore = re.search(rf"(?:avant[- ]pied|forefoot)\D{{0,10}}({NUM})\s*mm", window, re.I)
        if heel and fore:
            last = end + max(heel.end(), fore.end())
            return (
                found_at(text, start, end, last, to_float(heel.group(1))),
                found_at(text, start, end, last, to_float(fore.group(1))),
            )
        pair = re.search(rf"({NUM})\s*(?:mm)?\s*[/\u2013-]\s*({NUM})\s*mm", window)
        if not pair:
            continue
        a, b = to_float(pair.group(1)), to_float(pair.group(2))
        if not (_plausible("stack", a) and _plausible("stack", b)):
            continue
        if drop is None or abs(abs(a - b) - drop.value) > 0.5:
            continue  # unlabelled and not confirmed by a stated drop: heel unknown
        note = "heel/forefoot not labelled; the larger value is the heel (matches the stated drop)"
        args = (text, start, end + pair.start(), end + pair.end())
        extra = {"derivation": Derivation.ORDER_FROM_DROP, "note": note}
        return found_at(*args, max(a, b), **extra), found_at(*args, min(a, b), **extra)
    return None, None


def _first_cell(text: str, start: int, stop: int) -> tuple[int, int] | None:
    """Position of the first non-empty ' | ' cell in text[start:stop] (brackets skipped)."""
    for match in re.finditer(r"[^|]+", text[start:stop]):
        cell = match.group().strip(" :-\u2013[]()")  # \u2013 = en dash
        if cell:
            offset = start + match.start() + match.group().index(cell)
            return offset, offset + len(cell)
    return None


def _looks_like_foam(name: str) -> bool:
    """Reject adjectives ('Faible' in a rating widget): a foam name looks like a brand name."""
    return sum(ch.isupper() for ch in name) >= 2 or bool(
        re.search(r"eva|peba|tpu|foam", name, re.I)
    )


def _foam(text: str) -> Found | None:
    """Midsole foam name: after 'semelle intermédiaire'/'midsole', else 'amorti'/'mousse'."""
    insole = re.compile(LABELS["insole"], re.IGNORECASE)
    for field in ("midsole", "cushion"):
        for start, end, stop in _windows(text, field):
            # "Semelle intérieure ... de mousse EVA" describes the insole, not the midsole.
            if field == "cushion" and insole.search(text, max(0, start - 60), start):
                continue
            lead = re.compile(
                r"[\s:|]*(?:(?:en|de|du|la|le|est|dotée|nouvelle|nouveau|mousse)\s+)*"
            )
            begin = lead.match(text, end, stop).end()
            name = FOAM_NAME.match(text, begin, stop)
            if name and _looks_like_foam(name.group()):
                return found_at(text, start, name.start(), name.end(), name.group().strip())
    match = re.search(r"\b([A-Z][\w®™+]*[A-Z][\w®™+]*)\s+midsole\b", text)  # "EExpure midsole"
    if match:
        return found_at(text, match.start(), match.start(1), match.end(1), match.group(1))
    return None


def foam_family(name: str) -> FoamFamily:
    """Family from the words of the foam name only (no outside knowledge of trade names)."""
    folded = fold(name)
    families = set()
    if re.search(r"peba|pebax|\bpb\b", folded):
        families.add(FoamFamily.PEBA)
    if re.search(r"e?tpu", folded):
        families.add(FoamFamily.TPU)
    if "eva" in folded:
        families.add(FoamFamily.EVA)
    if len(families) > 1:
        return FoamFamily.HYBRID
    return families.pop() if families else FoamFamily.OTHER


def _rubber(text: str) -> Found | None:
    """Outsole: a known compound name after the outsole label, else a short labelled cell."""
    for start, end, stop in _windows(text, "outsole"):
        compound = COMPOUND.search(text, end, min(stop + 40, len(text)))
        if compound:
            return found_at(text, start, compound.start(), compound.end(), compound.group().strip())
        cell = _first_cell(text, end, stop)
        value = text[cell[0] : cell[1]] if cell else ""
        # A short labelled cell that names the rubber ("LOWA® TRAC®"), not a sentence.
        named = sum(ch.isupper() for ch in value) >= 2
        if value and len(value) <= 40 and named and RUBBER_WORDS.search(value):
            return found_at(text, start, *cell, value)
    match = max(COMPOUND.finditer(text), key=lambda m: len(m.group()), default=None)
    if match:
        return found_at(text, match.start(), match.start(), match.end(), match.group().strip())
    return None


def _plate(text: str) -> Found | None:
    match = PLATE.search(text)
    if not match:
        return None
    words = fold(match.group())
    if "sans" in words or "no plate" in words:
        value = Plate.NONE
    elif "carbon" in words:
        value = Plate.CARBON
    elif re.search(r"rock|roche|shield|protection", words):
        value = Plate.ROCK_PLATE
    else:
        value = Plate.OTHER
    return found_at(text, match.start(), match.start(), match.end(), value)


def _upper(text: str) -> Found | None:
    """First 4-25 words after a 'tige'/'upper' label, within one cell."""
    for _, end, _ in _windows(text, "upper"):
        cell = _first_cell(text, end, min(end + 400, len(text)))
        if not cell:
            continue
        words = text[cell[0] : cell[1]].split()[:25]
        if len(words) >= 4 and not words[0][0].isdigit():
            excerpt = " ".join(words).strip(" ,;:")
            excerpt_start = text.index(excerpt, cell[0])
            return found_at(
                text, excerpt_start, excerpt_start, excerpt_start + len(excerpt), excerpt
            )
    return None


def _width(text: str) -> Found | None:
    """Width words right after a 'largeur'/'width' label; ambiguous lists are skipped."""
    for start, end, stop in _windows(text, "width"):
        words = re.findall(r"[^\W\d_]+", fold(text[end:stop]))[:6]
        values = sorted({WIDTH_WORDS[w] for w in words if w in WIDTH_WORDS})
        # "Largeur | Étroite | Large" is a review filter, not the product: skip contradictions.
        if len(values) == 1:
            word = next(w for w in words if w in WIDTH_WORDS)
            position = fold(text).index(word, end)
            return found_at(text, start, position, position + len(word), values)
    return None


def extract(
    text: str, product_name: str, page_is_women: bool = False, skipped: dict | None = None
) -> dict[str, Found]:
    """Every field we could find, keyed by ModelSpecs field name (still to be verified).

    `skipped`, if given, receives the reason for values seen on the page but not kept.
    """
    skipped = {} if skipped is None else skipped
    found: dict[str, Found] = {}
    drop = _millimetres(text, "drop")
    heel, fore = _stacks(text, drop)
    if drop:
        found["drop_mm"] = drop
    if heel and fore:
        found["stack_heel_mm"], found["stack_forefoot_mm"] = heel, fore
        if drop is None:
            found["drop_mm"] = Found(
                round(heel.value - fore.value, 1),
                heel.snippet,
                heel.proof,
                Derivation.COMPUTED_FROM_STACKS,
                "computed: heel stack - forefoot stack",
            )
    if lug := _millimetres(text, "lug"):
        found["lug_depth_mm"] = lug
    found.update(_weights(text, page_is_women, skipped))
    if foam := _foam(text):
        found["midsole_foam"] = foam
        found["midsole_foam_family"] = Found(
            foam_family(foam.value), foam.snippet, foam.proof, Derivation.FAMILY_FROM_NAME
        )
    finders = {
        "outsole_rubber": _rubber,
        "plate": _plate,
        "upper_notes": _upper,
        "width_options": _width,
    }
    for key, finder in finders.items():
        if value := finder(text):
            found[key] = value
    waterproof = WATERPROOF.search(product_name)
    if waterproof and product_name in text:
        name_start = text.index(product_name)
        found["waterproof"] = Found(
            True,
            snippet_around(text, name_start, name_start + len(product_name)),
            waterproof.group(),
        )
    if year := YEAR.search(text):
        found["release_year"] = found_at(
            text, year.start(), year.start(1), year.end(1), int(year.group(1))
        )
    return found
