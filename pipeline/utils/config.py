"""Load the scoring configuration (pipeline/config/scoring.yaml)."""

from pathlib import Path
from typing import Any

import yaml

SCORING_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "scoring.yaml"


def load_scoring_config(path: Path = SCORING_CONFIG_PATH) -> dict[str, Any]:
    """Return scoring.yaml as a plain dictionary.

    A typed model of the config will be added in phase 6, when the scoring code that
    consumes it is written; until then the tests check its internal consistency.
    """
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)
