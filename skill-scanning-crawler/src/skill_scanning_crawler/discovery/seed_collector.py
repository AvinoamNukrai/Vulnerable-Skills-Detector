"""Seed-list collector: fetches curated lists and extracts GitHub repository URLs.

Supports:
  - Live HTTP fetch (with persistent cache via GitHubCache)
  - Local fixture files (for tests and offline mode)

Extracts GitHub repo URLs from HTML, Markdown, YAML, and plain text using
a broad regex. Every candidate preserves its seed source name, URL/path,
and extraction timestamp.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from skill_scanning_crawler.common.config import SeedListConfig
from skill_scanning_crawler.common.models import CandidateRepository
from skill_scanning_crawler.discovery.normalizer import (
    make_canonical_id,
    make_canonical_url,
)
from skill_scanning_crawler.github_client.cache import GitHubCache

log = logging.getLogger(__name__)

# The trailing lookahead intentionally treats "/" as a terminator so that
# deep links (…/owner/repo/tree/main/skills/foo, …/owner/repo/blob/…) and
# trailing-slash URLs (…/owner/repo/) still resolve to (owner, repo). The
# previous version kept "/" *inside* the negated class, which silently
# dropped every path-carrying GitHub URL — the dominant citation form in
# curated "awesome" lists.
_GH_URL_BROAD_RE = re.compile(
    r'https?://github\.com/([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+?)(?:\.git)?(?=[^\w.\-]|$)',
    re.IGNORECASE,
)
_EXCLUDE_OWNERS = frozenset({
    "topics", "search", "explore", "marketplace", "sponsors", "orgs",
    "features", "about", "pricing", "settings", "notifications", "login",
    "join", "apps", "collections", "contact", "site", "users", "blog",
})

# <meta http-equiv="refresh" content="0; url=https://…">. httpx follows only
# HTTP 3xx redirects, not HTML meta-refresh, so a moved-stub page (HTTP 200 +
# meta-refresh) would otherwise yield zero candidates silently.
_META_REFRESH_RE = re.compile(
    r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]*content=["\'][^"\']*url=([^"\'>\s]+)',
    re.IGNORECASE,
)
_MAX_META_REFRESH_HOPS = 3


def _extract_meta_refresh_target(html: str, base_url: str) -> str | None:
    """Return the absolute URL of an HTML meta-refresh redirect, if any."""
    m = _META_REFRESH_RE.search(html)
    if not m:
        return None
    return str(urljoin(base_url, m.group(1).strip()))


def extract_github_repos_from_text(text: str) -> list[tuple[str, str]]:
    """Extract (owner, repo) pairs from arbitrary text using regex.

    Filters out well-known non-repository paths.
    """
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in _GH_URL_BROAD_RE.finditer(text):
        owner, repo = m.group(1), m.group(2)
        # A trailing "." can be captured from prose punctuation ("see …/repo.")
        # since "." is a legal repo-name char; GitHub forbids trailing dots.
        repo = repo.rstrip(".")
        if not repo or owner.lower() in _EXCLUDE_OWNERS:
            continue
        key = f"{owner.lower()}/{repo.lower()}"
        if key not in seen:
            seen.add(key)
            results.append((owner, repo))
    return results


async def fetch_seed_list(
    seed_cfg: SeedListConfig,
    cache: GitHubCache | None = None,
    timeout: int = 30,
) -> list[CandidateRepository]:
    """Fetch one seed list and return extracted CandidateRepository list.

    Priority:
      1. ``local_path`` (fixture file — no network, no cache)
      2. ``url`` (live HTTP fetch, cached in GitHubCache)
    """
    source_name = seed_cfg.name

    if seed_cfg.local_path:
        return _from_local_file(seed_cfg.local_path, source_name)

    if seed_cfg.url:
        return await _from_url(seed_cfg.url, source_name, cache, timeout)

    log.warning("Seed list %r has neither url nor local_path; skipped", source_name)
    return []


def _from_local_file(local_path: str, source_name: str) -> list[CandidateRepository]:
    path = Path(local_path)
    if not path.exists():
        log.warning("Seed fixture not found: %s", path)
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    log.debug("Seed local file %s: %d bytes", path, len(text))
    return _text_to_candidates(text, source_name, str(path))


async def _from_url(
    url: str,
    source_name: str,
    cache: GitHubCache | None,
    timeout: int,
) -> list[CandidateRepository]:
    cache_key = ("seed_raw", url)
    if cache:
        cached_text: Any = cache.get(*cache_key)
        if cached_text is not None:
            log.debug("Seed cache HIT url=%s", url)
            return _text_to_candidates(str(cached_text), source_name, url)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
            current_url = url
            text = ""
            for _hop in range(_MAX_META_REFRESH_HOPS + 1):
                resp = await http.get(current_url)
                resp.raise_for_status()
                text = resp.text
                target = _extract_meta_refresh_target(text, current_url)
                if not target or target == current_url:
                    break
                log.info("Seed %r meta-refresh: %s -> %s", source_name, current_url, target)
                current_url = target
            else:
                log.warning(
                    "Seed %r exceeded %d meta-refresh hops; using last page",
                    source_name, _MAX_META_REFRESH_HOPS,
                )
    except httpx.HTTPError as exc:
        log.warning("Could not fetch seed list %r: %s", url, exc)
        return []

    log.debug("Seed fetch url=%s bytes=%d", url, len(text))
    if cache:
        cache.set(text, *cache_key, ttl=86400)  # 24 h
    return _text_to_candidates(text, source_name, url)


def _text_to_candidates(
    text: str, source_name: str, provenance: str
) -> list[CandidateRepository]:
    pairs = extract_github_repos_from_text(text)
    candidates: list[CandidateRepository] = []
    now = datetime.now(UTC)
    for owner, repo in pairs:
        cid = make_canonical_id(owner, repo)
        candidates.append(
            CandidateRepository(
                canonical_id=cid,
                owner=owner,
                repo=repo,
                url=make_canonical_url(owner, repo),
                discovery_sources=[source_name],
                discovery_queries=[provenance],
                discovered_at=now,
            )
        )
    if candidates:
        log.info("Seed %r extracted %d candidates from %s", source_name, len(candidates), provenance)
    else:
        # A configured seed that yields nothing is almost always a problem
        # (dead/moved URL, JS-rendered page, or changed markup) — surface it.
        log.warning(
            "Seed %r extracted 0 GitHub repositories from %s "
            "(dead/moved URL or JS-rendered page?)",
            source_name, provenance,
        )
    return candidates
