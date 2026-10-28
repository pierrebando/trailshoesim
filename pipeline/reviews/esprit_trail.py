"""Esprit Trail (esprit-trail.com), French: tests with a "le verdict" section.

Discovery: the post sitemaps, keeping test articles (`/test-...`). No numeric rating
and no lab measurements are published.
"""

from bs4 import BeautifulSoup

from pipeline.reviews.common import ParsedReview, json_ld_date, section_text
from pipeline.specs.locate import read_sitemap
from pipeline.utils.http import PoliteClient

SOURCE = "esprit_trail"
LANGUAGE = "fr"
SITEMAP_URL = "https://www.esprit-trail.com/sitemap_index.xml"


def discover(client: PoliteClient) -> list[str]:
    """Test articles listed in the post sitemaps."""
    pages = read_sitemap(client, SITEMAP_URL, r"post-sitemap")
    return [url for url in pages if "/test-" in url]


def parse(html: str) -> ParsedReview:
    """Title, date and verdict of a test article."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.h1.get_text(" ", strip=True) if soup.h1 else ""
    review = ParsedReview(title=title, date=json_ld_date(soup))
    review.conclusion_heading, review.conclusion = section_text(
        soup, r"verdict|conclusion|bilan|en r[ée]sum[ée]|notre avis"
    )
    return review
