"""Re-check of the sites that failed for a technical reason (pipeline/recheck.py)."""

from pathlib import Path

import pytest
import requests

from pipeline import recheck
from pipeline.utils import http
from tests.test_http import FakeResponse, FakeSession

CONFIG = """
brands:
  Fictional:
    status: allowed
  "+8000": {status: unreachable, homepage: "https://plus.example", reason: "TLS error"}
  Refuser: {status: blocked, reason: "HTTP 403"}
"""


class BrokenSession(FakeSession):
    """A site whose TLS certificate is still broken."""

    def get(self, url: str, timeout: float) -> FakeResponse:
        raise requests.exceptions.SSLError("certificate verify failed")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> http.PoliteClient:
    monkeypatch.setattr(http, "MIN_SECONDS_BETWEEN_REQUESTS", 0)
    return http.PoliteClient("recheck", refresh=True, raw_dir=tmp_path)


def test_only_technical_failures_are_rechecked(tmp_path: Path) -> None:
    path = tmp_path / "manufacturers.yaml"
    path.write_text(CONFIG, encoding="utf-8")
    # A site that refused us ("Refuser") is never tried again; "+8000" stays a string.
    assert recheck.unreachable_brands(path) == {"+8000": "https://plus.example"}


def test_a_site_that_answers_is_left_to_a_person(client: http.PoliteClient) -> None:
    client.session = FakeSession(
        {
            "https://plus.example/robots.txt": FakeResponse(404, ""),
            "https://plus.example": FakeResponse(200, "<html>home</html>"),
        }
    )
    assert "read its robots.txt and terms" in recheck.recheck("https://plus.example", client)


def test_a_site_still_broken_stays_unreachable(client: http.PoliteClient) -> None:
    client.session = BrokenSession({})
    assert "still unreachable (SSLError)" in recheck.recheck("https://plus.example", client)
