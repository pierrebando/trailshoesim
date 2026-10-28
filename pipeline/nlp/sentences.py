"""Stage 1: split review text into sentences (English and French).

A simple rule-based splitter is enough here: review conclusions are well-written prose.
We split after ".", "!" or "?" followed by a space and a capital letter (or a quote),
but not after common abbreviations ("e.g.", "vs.", "env.") or inside numbers ("9.5 oz").
"""

import re

ABBREVIATIONS = {
    "e.g", "i.e", "vs", "etc", "approx", "incl", "no", "mr", "mrs", "dr", "st",
    "env", "ex", "cf", "p", "m", "mme", "mlle", "n°",
}  # fmt: skip
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[\"«“A-ZÀ-ÖØ-Þ0-9])")
MIN_WORDS = 3  # shorter fragments ("SAM :") carry no opinion


def split_sentences(text: str | None) -> list[str]:
    """Sentences of `text`, in order, with whitespace normalised."""
    if not text:
        return []
    text = " ".join(text.split())
    pieces = SENTENCE_END.split(text)
    sentences: list[str] = []
    for piece in pieces:
        previous_word = sentences[-1].rstrip(".").rsplit(" ", 1)[-1].lower() if sentences else ""
        if sentences and previous_word in ABBREVIATIONS:
            sentences[-1] += " " + piece  # "vs. Speedgoat" did not end a sentence
        else:
            sentences.append(piece)
    # Remove reviewer tags ("SAM : ...") at the start of a sentence.
    sentences = [re.sub(r"^[A-Z][A-Z .'-]{1,20}\s*:\s*", "", s).strip() for s in sentences]
    return [s for s in sentences if len(s.split()) >= MIN_WORDS]


def review_sentences(conclusion: str | None, pros: list[str], cons: list[str]) -> list[str]:
    """Sentences of the conclusion, then pros and cons items (each item is a sentence).

    Pros/cons items are often 2-3 words ("Heavy", "Stable ride"), so they are kept even
    when shorter than MIN_WORDS.
    """
    sentences = split_sentences(conclusion)
    for item in [*pros, *cons]:
        if len(item.split()) > 25:  # a paragraph (Believe in the Run): split it
            sentences += split_sentences(item)
        elif item.strip():
            sentences.append(" ".join(item.split()))
    return sentences
