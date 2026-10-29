"""Try again the manufacturer sites that failed for a TECHNICAL reason.

    python -m pipeline.recheck

A TLS certificate error or a timeout is not a refusal: the site may simply have been
fixed since. Each `status: unreachable` brand of pipeline/config/manufacturers.yaml gets
one fresh request to its homepage (robots.txt first, as always with PoliteClient), and the
command prints what happened. It changes nothing by itself: when a site answers, a person
reads its robots.txt and terms (docs/sources.md) and only then sets `status: allowed`.

Sites that REFUSED us (bot protection, robots.txt, terms) are `status: blocked` and are
never tried again here: a refusal is the owner's decision, not a glitch.
"""

import sys
from pathlib import Path

import requests
import yaml

from pipeline.utils.http import AccessBlockedError, DisallowedByRobotsError, PoliteClient

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "pipeline" / "config" / "manufacturers.yaml"


def unreachable_brands(config_path: Path = CONFIG_PATH) -> dict[str, str]:
    """{brand: homepage} of every brand whose site failed for a technical reason."""
    brands = yaml.safe_load(config_path.read_text(encoding="utf-8"))["brands"]
    return {
        str(name): entry["homepage"]
        for name, entry in brands.items()
        if entry.get("status") == "unreachable"
    }


def recheck(homepage: str, client: PoliteClient) -> str:
    """One-line verdict for one site; the next step is always a person's."""
    try:
        response = client.get(homepage)
    except AccessBlockedError:
        return "now REFUSES access (bot protection): set status blocked"
    except DisallowedByRobotsError:
        return "now answers, but robots.txt disallows us: set status blocked"
    except requests.RequestException as error:
        return f"still unreachable ({type(error).__name__}): keep status unreachable"
    if response.status != 200:
        return f"answers HTTP {response.status}: keep status unreachable"
    return "answers: read its robots.txt and terms, then decide (docs/sources.md)"


def main() -> int:
    """Re-check every unreachable site once, without the cache, and print the verdicts."""
    sites = unreachable_brands()
    if not sites:
        print("no site has status unreachable")
        return 0
    # refresh=True: an old cached failure or page must not hide today's answer.
    client = PoliteClient("recheck", refresh=True)
    for brand, homepage in sites.items():
        print(f"{brand:<12} {homepage:<35} {recheck(homepage, client)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
