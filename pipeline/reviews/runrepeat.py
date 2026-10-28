"""RunRepeat (runrepeat.com): score, verdict, pros/cons and LAB MEASUREMENTS.

Discovery: the trail catalogue `/catalog/trail-running-shoes?page=N` (the sitemap
declared in robots.txt answers 404). Review pages are `runrepeat.com/<slug>`.

RunRepeat measures shoes in its own lab ("Heel stack | 31.7 mm | 33.0 mm" = this shoe |
average). Those values are stored as the SOURCE's measurements, never as manufacturer
data. Note: RunRepeat sells licences for its data; check before publishing them.
"""

import re

from bs4 import BeautifulSoup

from pipeline.reviews.common import ParsedReview
from pipeline.specs.pagetext import full_page_text
from pipeline.utils.http import PoliteClient

SOURCE = "runrepeat"
LANGUAGE = "en"
CATALOGUE_URL = "https://runrepeat.com/catalog/trail-running-shoes"
MAX_PAGES = 30
NOT_SHOES = ("catalog", "footwear", "guides", "about", "partner", "data-", "media", "legal")

# Lab table label -> (our key, unit). Only measurements useful to the scoring are kept.
LAB_LABELS = {
    "Heel stack": ("stack_heel_mm", "mm"),
    "Forefoot stack": ("stack_forefoot_mm", "mm"),
    "Drop": ("drop_mm", "mm"),
    "Lug depth": ("lug_depth_mm", "mm"),
    "Weight": ("weight_g", "g"),
    "Midsole softness": ("midsole_softness_ac", "AC"),
    "Energy return heel": ("energy_return_heel_pct", "%"),
    "Energy return forefoot": ("energy_return_forefoot_pct", "%"),
    "Shock absorption heel": ("shock_absorption_heel_sa", "SA"),
    "Midsole width - forefoot": ("midsole_width_forefoot_mm", "mm"),
    "Midsole width - heel": ("midsole_width_heel_mm", "mm"),
    "Toebox width": ("toebox_width_mm", "mm"),
    "Torsional rigidity": ("torsional_rigidity_nm", "Nm"),
    "Flexibility / Stiffness": ("stiffness_n", "N"),
    "Outsole durability": ("outsole_wear_mm", "mm"),
    "Outsole thickness": ("outsole_thickness_mm", "mm"),
}


def discover(client: PoliteClient) -> list[str]:
    """Review URLs of every shoe listed in the trail catalogue."""
    slugs: list[str] = []
    for page in range(1, MAX_PAGES + 1):
        url = CATALOGUE_URL if page == 1 else f"{CATALOGUE_URL}?page={page}"
        html = client.get(url).text
        found = re.findall(r'href="(?:https://runrepeat\.com)?/([a-z0-9]+(?:-[a-z0-9]+)+)"', html)
        new = [s for s in dict.fromkeys(found) if not s.startswith(NOT_SHOES) and s not in slugs]
        slugs += new
        if not new or f"page={page + 1}" not in html:
            break
    return [f"https://runrepeat.com/{slug}" for slug in slugs]


def _lab_values(text: str) -> dict[str, dict]:
    start = text.find("Lab test results")
    end = text.find("Specs (brand)", start)
    table = text[start:end] if start >= 0 else ""
    values: dict[str, dict] = {}
    for label, (key, unit) in LAB_LABELS.items():
        # A section header can carry the same label ("Weight | [ | Weight | 9.8 oz..."):
        # take the first occurrence that is followed by a number.
        # Lookahead: matches must not consume the next label ("| Weight | [ | Weight |").
        pattern = rf"(?=\| {re.escape(label)} \| ([^|]+?) \| ([^|]+?) \|)"
        for match in re.finditer(pattern, table):
            this_shoe, average = match.group(1).strip(), match.group(2).strip()
            if unit == "g":  # "9.8 oz (278g)": keep the grams the page prints
                number = re.search(r"\((\d+(?:\.\d+)?)\s*g\)", this_shoe)
            else:
                number = re.match(r"(\d+(?:\.\d+)?)", this_shoe)
            if number:
                break
        else:
            continue
        values[key] = {
            "value": float(number.group(1)),
            "source_name": "RunRepeat lab measurement (not manufacturer data)",
            "raw_snippet": f"{label} | {this_shoe} | {average}",
            "note": f"measured by RunRepeat; unit {unit}; average of tested shoes: {average}",
        }
    return values


def _list_after(text: str, heading: str) -> list[str]:
    match = re.search(rf"\| {heading} \| \[ \| (.*?) \| \]", text)
    return [item.strip() for item in match.group(1).split(" | ")] if match else []


def parse(html: str) -> ParsedReview:
    """Title, date, scores, verdict, pros/cons and lab values of a review page."""
    soup = BeautifulSoup(html, "html.parser")
    text = full_page_text(html)
    title = soup.h1.get_text(" ", strip=True) if soup.h1 else ""
    time_tag = soup.find("time", attrs={"datetime": True})
    review = ParsedReview(title=title, date=time_tag["datetime"][:10] if time_tag else None)

    verdict = re.search(
        r"Our verdict \| (\d{1,3}) \| ([^|]+?) \| (?:\[ \| (.*?) \| \] \| )?(.*?) \| Pros", text
    )
    if verdict:
        score, word, subscores, paragraph = verdict.groups()
        review.ratings.append(
            {
                "label": "Our verdict",
                "value": score,
                "scale": "0-100",
                "raw_snippet": f"Our verdict | {score} | {word}",
            }
        )
        for label, value in re.findall(
            r"([A-Za-z][\w /-]*?) \| (\d{1,3})(?= \||$)", subscores or ""
        ):
            review.ratings.append(
                {
                    "label": label,
                    "value": value,
                    "scale": "0-100",
                    "raw_snippet": f"{label} | {value}",
                }
            )
        review.conclusion = paragraph.strip()
        review.conclusion_heading = "Our verdict"
    review.pros = _list_after(text, "Pros")
    review.cons = _list_after(text, "Cons")
    review.lab_values = _lab_values(text)
    return review
