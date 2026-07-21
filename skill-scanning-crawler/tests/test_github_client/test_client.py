"""Tests for GitHubClient using respx to mock httpx."""

from __future__ import annotations

import httpx
import pytest
import respx

from skill_scanning_crawler.common.exceptions import GitHubClientError
from skill_scanning_crawler.github_client.cache import GitHubCache
from skill_scanning_crawler.github_client.client import GitHubClient
from skill_scanning_crawler.github_client.rate_limiter import RateLimiter


def _make_client(token: str = "test-token", cache: GitHubCache | None = None) -> GitHubClient:
    rl = RateLimiter(
        search_concurrency=1,
        metadata_concurrency=1,
        tree_concurrency=1,
        download_concurrency=1,
        max_retries=1,
        backoff_initial=0.0,
        backoff_max=0.0,
    )
    return GitHubClient(token=token, cache=cache, rate_limiter=rl, timeout=5)


def _make_disabled_cache() -> GitHubCache:
    cache = GitHubCache.__new__(GitHubCache)
    cache._enabled = False
    cache._cache = None
    return cache


# ---------------------------------------------------------------------------
# Token handling
# ---------------------------------------------------------------------------


def test_token_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Token value must never appear in any log record."""
    import logging
    with caplog.at_level(logging.DEBUG):
        _make_client(token="super-secret-abc123")
    assert "super-secret-abc123" not in caplog.text


def test_missing_token_still_creates_client() -> None:
    """Client can be created with no token; it will send unauthenticated requests."""
    client = GitHubClient(token=None)
    assert client._token is None  # noqa: SLF001


# ---------------------------------------------------------------------------
# Repository metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_repository_success() -> None:
    respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
        return_value=httpx.Response(
            200,
            json={
                "full_name": "octocat/Hello-World",
                "stargazers_count": 100,
                "forks_count": 20,
                "fork": False,
                "archived": False,
                "default_branch": "main",
                "html_url": "https://github.com/octocat/Hello-World",
            },
        )
    )
    async with _make_client() as client:
        data = await client.get_repository("octocat", "Hello-World")
    assert data["full_name"] == "octocat/Hello-World"
    assert data["stargazers_count"] == 100


@pytest.mark.asyncio
@respx.mock
async def test_get_repository_404_raises() -> None:
    respx.get("https://api.github.com/repos/no/exist").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    async with _make_client() as client:
        with pytest.raises(GitHubClientError, match="Not found"):
            await client.get_repository("no", "exist")


@pytest.mark.asyncio
@respx.mock
async def test_get_default_branch_sha() -> None:
    respx.get("https://api.github.com/repos/octocat/Hello-World/commits/main").mock(
        return_value=httpx.Response(200, json={"sha": "abc123def456"})
    )
    async with _make_client() as client:
        sha = await client.get_default_branch_sha("octocat", "Hello-World", "main")
    assert sha == "abc123def456"


# ---------------------------------------------------------------------------
# Tree
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_tree_returns_items() -> None:
    tree_data = {
        "tree": [
            {"path": "skills/pdf/SKILL.md", "type": "blob", "size": 512},
            {"path": "README.md", "type": "blob", "size": 1024},
        ]
    }
    respx.get(
        "https://api.github.com/repos/octocat/repo/git/trees/abc123",
    ).mock(return_value=httpx.Response(200, json=tree_data))
    async with _make_client() as client:
        tree = await client.get_tree("octocat", "repo", "abc123")
    assert len(tree) == 2
    assert tree[0]["path"] == "skills/pdf/SKILL.md"


# ---------------------------------------------------------------------------
# File content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_file_content_base64() -> None:
    import base64
    raw = "---\nname: My Skill\ndescription: A skill\n---\nBody"
    encoded = base64.b64encode(raw.encode()).decode()
    respx.get("https://api.github.com/repos/octocat/repo/contents/SKILL.md").mock(
        return_value=httpx.Response(
            200,
            json={"encoding": "base64", "content": encoded},
        )
    )
    async with _make_client() as client:
        content = await client.get_file_content("octocat", "repo", "SKILL.md", "main")
    assert content == raw


# ---------------------------------------------------------------------------
# Cache integration
# ---------------------------------------------------------------------------


class _InMemCache(GitHubCache):
    """Cache that stores to a plain dict (no disk)."""

    def __init__(self) -> None:
        self._enabled = True
        self._store: dict[str, object] = {}

    def _get_store_key(self, category: str, *parts: str) -> str:
        import hashlib
        import json
        raw = json.dumps([category, *parts], sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, category: str, *parts: str) -> object | None:
        return self._store.get(self._get_store_key(category, *parts))

    def set(self, value: object, category: str, *parts: str, ttl: int | None = None) -> None:
        self._store[self._get_store_key(category, *parts)] = value

    def close(self) -> None:
        pass


@pytest.mark.asyncio
@respx.mock
async def test_cache_hit_skips_network() -> None:
    """When cache has a hit, no HTTP request should be made."""
    cache = _InMemCache()
    cached_data = {"full_name": "from/cache", "stargazers_count": 99}
    cache.set(cached_data, "repo_meta", "octocat", "repo")

    # If a real request were made, respx would raise an error (no mock set up).
    async with _make_client(cache=cache) as client:
        data = await client.get_repository("octocat", "repo")
    assert data["full_name"] == "from/cache"


# ---------------------------------------------------------------------------
# Retry on 429
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_rate_limited_raises_after_retries() -> None:
    respx.get("https://api.github.com/repos/octocat/repo").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(429, headers={"retry-after": "0"}),
        ]
    )
    async with _make_client() as client:
        with pytest.raises(GitHubClientError, match="retries exhausted"):
            await client.get_repository("octocat", "repo")


@pytest.mark.asyncio
@respx.mock
async def test_retry_after_header_respected() -> None:
    """Client uses Retry-After value when present (0 in tests for speed)."""
    respx.get("https://api.github.com/repos/octocat/repo").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(200, json={"full_name": "octocat/repo", "stargazers_count": 5,
                                      "forks_count": 0, "fork": False, "archived": False,
                                      "default_branch": "main", "html_url": "https://github.com/octocat/repo"}),
        ]
    )
    # Allow 2 retries
    rl = RateLimiter(max_retries=2, backoff_initial=0.0, backoff_max=0.0)
    client = GitHubClient(token="t", rate_limiter=rl)
    async with client:
        data = await client.get_repository("octocat", "repo")
    assert data["full_name"] == "octocat/repo"
