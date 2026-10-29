"""The polite HTTP client and robots.txt parser enforce the scraping rules (no network)."""

from pathlib import Path

import pytest

from pipeline.utils import http
from pipeline.utils.robots import RobotsRules

ROBOTS = """
User-agent: *
Disallow: */myaccount*
Disallow: /index.php?action=*
Disallow: */cart$
Allow: /public/private/ok
Disallow: /public/private/

User-agent: SomeOtherBot
Disallow: /
"""


@pytest.mark.parametrize(
    ("path", "allowed"),
    [
        ("/runnerinn/fr/chaussures/10005/s", True),
        ("/runnerinn/fr/myaccount/data", False),  # leading * wildcard
        ("/index.php?action=login", False),  # query strings are matched too
        ("/runnerinn/fr/cart", False),  # $ anchors the end
        ("/runnerinn/fr/cart/items", True),
        ("/public/private/secret", False),
        ("/public/private/ok", True),  # longer Allow beats shorter Disallow
    ],
)
def test_robots_wildcards_and_precedence(path: str, allowed: bool) -> None:
    assert RobotsRules(ROBOTS, "TrailShoeFinder/0.1").is_allowed(path) is allowed


def test_robots_group_for_a_named_agent_replaces_the_generic_one() -> None:
    assert RobotsRules(ROBOTS, "SomeOtherBot/2.0").is_allowed("/anything") is False


class FakeResponse:
    def __init__(self, status: int, text: str, headers: dict | None = None) -> None:
        self.status_code = status
        self.text = text
        self.headers = headers or {}


class FakeSession:
    """Stands in for requests.Session and records which URLs were requested."""

    def __init__(self, pages: dict[str, FakeResponse]) -> None:
        self.pages = pages
        self.requested: list[str] = []
        self.headers: dict[str, str] = {}

    def get(self, url: str, timeout: int) -> FakeResponse:
        self.requested.append(url)
        return self.pages[url]


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> http.PoliteClient:
    monkeypatch.setattr(http, "MIN_SECONDS_BETWEEN_REQUESTS", 0)
    polite = http.PoliteClient("example", raw_dir=tmp_path)
    polite.session = FakeSession(
        {
            "https://shop.example/robots.txt": FakeResponse(
                200, "User-agent: *\nDisallow: /private"
            ),
            "https://shop.example/page": FakeResponse(200, "<html>page</html>"),
            "https://shop.example/blocked": FakeResponse(403, "<title>Just a moment...</title>"),
        }
    )
    return polite


def test_second_fetch_comes_from_the_cache(client: http.PoliteClient) -> None:
    first = client.get("https://shop.example/page")
    second = client.get("https://shop.example/page")
    assert first.text == second.text == "<html>page</html>"
    assert not first.from_cache and second.from_cache
    assert client.session.requested == [
        "https://shop.example/robots.txt",
        "https://shop.example/page",
    ]


def test_robots_disallowed_url_is_never_requested(client: http.PoliteClient) -> None:
    with pytest.raises(http.DisallowedByRobotsError):
        client.get("https://shop.example/private/x")
    assert "https://shop.example/private/x" not in client.session.requested


def test_bot_challenge_stops_instead_of_retrying(client: http.PoliteClient) -> None:
    with pytest.raises(http.AccessBlockedError):
        client.get("https://shop.example/blocked")
    assert client.session.requested.count("https://shop.example/blocked") == 1


def test_user_agent_identifies_the_project_without_hardcoded_contact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TSF_CONTACT", raising=False)
    assert http.user_agent().startswith("TrailShoeFinder/")
    assert "student project" in http.user_agent()
    assert http.PLACEHOLDER_CONTACT in http.user_agent()
    monkeypatch.setenv("TSF_CONTACT", "team@example.org")
    assert "team@example.org" in http.user_agent()
