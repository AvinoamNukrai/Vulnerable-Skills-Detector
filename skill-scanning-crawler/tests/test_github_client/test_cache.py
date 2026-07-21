"""Tests for GitHubCache (no network, no disk — uses in-memory mock)."""

from __future__ import annotations

from skill_scanning_crawler.github_client.cache import GitHubCache


class _FakeDiskcache:
    """Minimal in-memory stand-in for diskcache.Cache."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        return self._store.get(key)

    def set(self, key: str, value: object, *, expire: int | None = None) -> None:
        self._store[key] = value

    def close(self) -> None:
        pass


def _make_cache() -> GitHubCache:
    cache = GitHubCache.__new__(GitHubCache)
    cache._enabled = True
    cache._cache = _FakeDiskcache()
    return cache


def test_cache_miss_returns_none() -> None:
    cache = _make_cache()
    assert cache.get("search_code", "q=SKILL.md") is None


def test_cache_set_then_get() -> None:
    cache = _make_cache()
    cache.set([{"full_name": "owner/repo"}], "search_code", "q=SKILL.md", ttl=60)
    result = cache.get("search_code", "q=SKILL.md")
    assert result is not None
    assert result[0]["full_name"] == "owner/repo"  # type: ignore[index]


def test_cache_different_keys_isolated() -> None:
    cache = _make_cache()
    cache.set("value_a", "cat_a", "key")
    cache.set("value_b", "cat_b", "key")
    assert cache.get("cat_a", "key") == "value_a"
    assert cache.get("cat_b", "key") == "value_b"


def test_cache_disabled_get_returns_none() -> None:
    cache = GitHubCache.__new__(GitHubCache)
    cache._enabled = False
    cache._cache = None
    assert cache.get("search_code", "q=anything") is None


def test_cache_disabled_set_is_noop() -> None:
    cache = GitHubCache.__new__(GitHubCache)
    cache._enabled = False
    cache._cache = None
    cache.set("value", "category", "key")  # should not raise
    assert cache.get("category", "key") is None


def test_cache_close_clears_cache() -> None:
    cache = _make_cache()
    cache.close()
    assert cache._cache is None


def test_cache_context_manager() -> None:
    cache = _make_cache()
    with cache as c:
        c.set("hello", "greet", "world")
        assert c.get("greet", "world") == "hello"
    assert cache._cache is None
