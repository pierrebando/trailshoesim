"""A polite HTTP client: robots.txt check, rate limit, explicit User-Agent, disk cache.

Every collector goes through `PoliteClient`, so the scraping rules of CLAUDE.md are
enforced in one place instead of being repeated in each site module.
"""

import datetime as dt
import gzip
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import requests

from pipeline.utils.robots import RobotsRules

log = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
MIN_SECONDS_BETWEEN_REQUESTS = 1.1  # rule: at most 1 request per second per site
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3


def user_agent() -> str:
    """User-Agent identifying the project.

    The contact is read from the TSF_CONTACT environment variable so that no personal
    address is hard-coded in the repository.
    """
    contact = os.environ.get("TSF_CONTACT", "contact via the project repository")
    return f"TrailShoeFinder/0.1 (non-commercial school project; 1 req/s; {contact})"


class AccessBlockedError(RuntimeError):
    """The site refuses automated access (bot challenge, 401/403). We must stop, not retry."""


class DisallowedByRobotsError(RuntimeError):
    """robots.txt disallows this URL."""


@dataclass
class CachedResponse:
    """A response read from the network or from the cache."""

    url: str
    status: int
    text: str
    retrieved_at: dt.date
    from_cache: bool


def _looks_like_bot_challenge(response: requests.Response) -> bool:
    body_start = response.text[:3000]
    return (
        response.headers.get("cf-mitigated") == "challenge"
        or "Just a moment..." in body_start
        or "cf_chl_opt" in body_start
    )


class PoliteClient:
    """Fetch pages of one site politely, caching every response under data/raw/<site>/."""

    def __init__(self, site: str, refresh: bool = False, raw_dir: Path = RAW_DIR) -> None:
        """Create a client for `site`; `refresh=True` ignores (and overwrites) the cache."""
        self.site = site
        self.refresh = refresh
        self.cache_dir = raw_dir / site
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent(),
                # Some sites (Glisshop) return an empty page without a browser-like Accept.
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "fr-FR,fr;q=0.9",
            }
        )
        self._last_request_at = 0.0
        self._robots: dict[str, RobotsRules] = {}
        self.network_requests = 0
        self.cache_hits = 0

    # -- cache -------------------------------------------------------------

    def _cache_paths(self, url: str) -> tuple[Path, Path]:
        key = hashlib.sha256(url.encode()).hexdigest()[:24]
        return self.cache_dir / f"{key}.body.gz", self.cache_dir / f"{key}.meta.json"

    def _read_cache(self, url: str) -> CachedResponse | None:
        body_path, meta_path = self._cache_paths(url)
        if self.refresh or not (body_path.exists() and meta_path.exists()):
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        text = gzip.decompress(body_path.read_bytes()).decode("utf-8")
        self.cache_hits += 1
        return CachedResponse(
            url, meta["status"], text, dt.date.fromisoformat(meta["retrieved_at"]), True
        )

    def read_cached(self, url: str) -> CachedResponse | None:
        """The cached response for `url`, or None. Never touches the network."""
        refresh, self.refresh = self.refresh, False
        try:
            return self._read_cache(url)
        finally:
            self.refresh = refresh

    def _write_cache(self, response: CachedResponse) -> None:
        body_path, meta_path = self._cache_paths(response.url)
        # Gzip because product pages are ~600 kB each and this folder may sync to the cloud.
        body_path.write_bytes(gzip.compress(response.text.encode("utf-8")))
        meta = {
            "url": response.url,
            "status": response.status,
            "retrieved_at": response.retrieved_at.isoformat(),
        }
        meta_path.write_text(json.dumps(meta), encoding="utf-8")

    # -- network -----------------------------------------------------------

    def _wait_turn(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < MIN_SECONDS_BETWEEN_REQUESTS:
            time.sleep(MIN_SECONDS_BETWEEN_REQUESTS - elapsed)
        self._last_request_at = time.monotonic()

    def _http_get(self, url: str) -> requests.Response:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._wait_turn()
            self.network_requests += 1
            response = self.session.get(url, timeout=TIMEOUT_SECONDS)
            if response.status_code in (401, 403) or _looks_like_bot_challenge(response):
                raise AccessBlockedError(f"{url} answered {response.status_code} (access refused)")
            if response.status_code == 429 or response.status_code >= 500:
                # Back off more each time: the server is telling us to slow down.
                pause = 10 * attempt
                log.warning("%s answered %s, retrying in %ss", url, response.status_code, pause)
                time.sleep(pause)
                continue
            return response
        return response

    def _robots_for(self, url: str) -> RobotsRules:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            robots_url = f"{origin}/robots.txt"
            cached = self._read_cache(robots_url)
            if cached is None:
                response = self._http_get(robots_url)
                cached = CachedResponse(
                    robots_url, response.status_code, response.text, dt.date.today(), False
                )
                self._write_cache(cached)
            # A missing robots.txt (404) means no restriction.
            text = cached.text if cached.status == 200 else ""
            self._robots[origin] = RobotsRules(text, user_agent())
        return self._robots[origin]

    def get(self, url: str) -> CachedResponse:
        """Return the page at `url`, from the cache when possible."""
        cached = self._read_cache(url)
        if cached is not None:
            return cached
        parts = urlsplit(url)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        if not self._robots_for(url).is_allowed(path):
            raise DisallowedByRobotsError(url)
        response = self._http_get(url)
        result = CachedResponse(url, response.status_code, response.text, dt.date.today(), False)
        if response.status_code == 200:
            self._write_cache(result)
        return result
