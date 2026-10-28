"""Believe in the Run (believeintherun.com): letter grades and "Final thoughts".

Discovery: the sitemap, keeping written reviews (`/shoe-reviews/`). Video pages and
comparisons are not used. The page gives grades A-F for Design, Value and Performance.
No lab measurements are published (the specs block repeats the brand's figures).
"""

import re

from bs4 import BeautifulSoup

from pipeline.reviews.common import ParsedReview, json_ld_date, section_text
from pipeline.specs.locate import read_sitemap
from pipeline.specs.pagetext import full_page_text
from pipeline.utils.http import PoliteClient

SOURCE = "believe_in_the_run"
LANGUAGE = "en"
SITEMAP_URL = "https://believeintherun.com/sitemap.xml"
GRADE = r"[A-F][+-]?"


def discover(client: PoliteClient) -> list[str]:
    """Written shoe reviews listed in the sitemap."""
    return [url for url in read_sitemap(client, SITEMAP_URL, None) if "/shoe-reviews/" in url]


def parse(html: str) -> ParsedReview:
    """Title, date, grades, final thoughts and likes/dislikes of a review page."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.h1.get_text(" ", strip=True) if soup.h1 else ""
    review = ParsedReview(title=title, date=json_ld_date(soup))
    text = full_page_text(html)
    score = text.find("The Score")
    if score >= 0:
        for label, grade in re.findall(
            rf"(Design|Value|Performance) \| ({GRADE})(?= \|)", text[score : score + 200]
        ):
            review.ratings.append(
                {
                    "label": label,
                    "value": grade,
                    "scale": "A-F",
                    "raw_snippet": f"{label} | {grade}",
                }
            )
    review.conclusion_heading, review.conclusion = section_text(
        soup, r"final thoughts|verdict|conclusion|bottom line"
    )
    _, likes = section_text(soup, r"what we like")
    _, dislikes = section_text(soup, r"what we don.?t like")
    review.pros = [likes] if likes else []
    review.cons = [dislikes] if dislikes else []
    return review
