"""Persistent disk cache wrapper for GitHub API responses.

Uses *diskcache* for thread-safe, process-safe, TTL-aware caching.
Cache keys are stable SHA-256 digests of (category, *parts).
Cache can be disabled globally for tests or offline mode.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

log = logging.getLogger(__name__)


class GitHubCache:
    """Thin, testable wrapper around diskcache.Cache."""

    def __init__(self, directory: str, enabled: bool = True) -> None:
        self._enabled = enabled
        self._cache: Any = None  # diskcache.Cache — import lazily to stay mockable
        if enabled:
            import diskcache  # noqa: PLC0415

            self._cache = diskcache.Cache(directory)
            log.debug("Cache opened at %s", directory)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _key(self, category: str, *parts: str) -> str:
        raw = json.dumps([category, *parts], sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, category: str, *parts: str) -> Any | None:
        if not self._enabled or self._cache is None:
            return None
        key = self._key(category, *parts)
        value: Any = self._cache.get(key)
        if value is not None:
            log.debug("Cache HIT  category=%s", category)
        return value

    def set(
        self,
        value: Any,
        category: str,
        *parts: str,
        ttl: int | None = None,
    ) -> None:
        if not self._enabled or self._cache is None:
            return
        key = self._key(category, *parts)
        self._cache.set(key, value, expire=ttl)
        log.debug("Cache SET  category=%s ttl=%s", category, ttl)

    def close(self) -> None:
        if self._cache is not None:
            self._cache.close()
            self._cache = None

    def __enter__(self) -> GitHubCache:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
