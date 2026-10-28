"""Turn a product page into the plain text the extractor reads.

Cells of the page are joined with " | " so that tables ("Drop | 6 mm") keep their
label/value structure. Only the text from the product title (h1) onwards is kept, and it
is cut where "related products" blocks start: navigation menus and other products'
descriptions would otherwise pollute the specs ("Imperméables" in a menu is not a spec).
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

# Headings after which the page talks about other products.
END_MARKERS = re.compile(
    r"vous aimerez aussi|vous pourriez aussi aimer|produits similaires|produits associ[ée]s"
    r"|compl[ée]tez votre|recommand[ée]s? pour vous|you may also like|related products"
    r"|derniers produits consult[ée]s|les clients ont aussi",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PageText:
    """The readable parts of one product page."""

    product_name: str  # h1 (or <title> if the page has no h1)
    text: str  # product area, cells separated by " | "


def normalise_space(text: str) -> str:
    """Collapse runs of spaces and of empty cells."""
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"(\s*\|\s*)+", " | ", text).strip(" |")


def page_text(html: str) -> PageText:
    """Extract the product name and the product-area text of a page."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    heading = soup.find("h1")
    if heading is not None:
        name = heading.get_text(" ", strip=True)
        strings = [heading.get_text(" ", strip=True)]
        strings += [s.strip() for s in heading.find_all_next(string=True) if s.strip()]
    else:
        name = soup.title.get_text(" ", strip=True) if soup.title else ""
        strings = [s.strip() for s in soup.find_all(string=True) if s.strip()]
    # Inline JSON blobs ('{"attributes":["size","width"]...') are data, not product text.
    strings = [s for s in strings if not (len(s) > 100 and s[0] in "{[")]
    text = normalise_space(" | ".join(strings))
    end = END_MARKERS.search(text)
    if end and end.start() > 200:  # a marker at the very top is a menu entry, not the end
        text = text[: end.start()]
    return PageText(product_name=normalise_space(name), text=text)


def full_page_text(html: str) -> str:
    """All visible text of a page (no h1 start, no end cut), cells separated by " | "."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    return normalise_space(" | ".join(s.strip() for s in soup.find_all(string=True) if s.strip()))
