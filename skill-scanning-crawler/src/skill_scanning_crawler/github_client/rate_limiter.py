"""Bounded concurrency and GitHub rate-limit utilities.

Provides per-category asyncio semaphores and full-jitter exponential
backoff, following the GitHub guidance on handling secondary rate limits.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import time

import httpx

log = logging.getLogger(__name__)


class RateLimiter:
    """Per-category semaphore pool with full-jitter exponential back-off.

    Categories: ``search``, ``metadata``, ``tree``, ``download``.
    Any unknown category falls back to the ``metadata`` semaphore.
    """

    def __init__(
        self,
        search_concurrency: int = 2,
        metadata_concurrency: int = 8,
        tree_concurrency: int = 6,
        download_concurrency: int = 4,
        max_retries: int = 5,
        backoff_initial: float = 1.0,
        backoff_max: float = 60.0,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_initial = backoff_initial
        self.backoff_max = backoff_max
        # Semaphores are created on first access so the object can be
        # instantiated outside an async context.
        self._concurrency = {
            "search": search_concurrency,
            "metadata": metadata_concurrency,
            "tree": tree_concurrency,
            "download": download_concurrency,
        }
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    def semaphore(self, category: str) -> asyncio.Semaphore:
        key = category if category in self._concurrency else "metadata"
        if key not in self._semaphores:
            self._semaphores[key] = asyncio.Semaphore(self._concurrency[key])
        return self._semaphores[key]

    def backoff_delay(self, attempt: int) -> float:
        """Full-jitter delay for *attempt* (0-indexed)."""
        cap = min(self.backoff_max, self.backoff_initial * (2**attempt))
        return random.uniform(0.0, cap)  # noqa: S311

    def log_rate_limit_headers(self, response: httpx.Response) -> None:
        """Log ``X-RateLimit-*`` headers at DEBUG without leaking auth info."""
        h = response.headers
        remaining = h.get("x-ratelimit-remaining")
        limit = h.get("x-ratelimit-limit")
        used = h.get("x-ratelimit-used")
        reset_ts = h.get("x-ratelimit-reset")
        reset_in: float | None = None
        if reset_ts:
            with contextlib.suppress(ValueError):
                reset_in = float(reset_ts) - time.time()
        log.debug(
            "rate_limit remaining=%s/%s used=%s reset_in_s=%s",
            remaining,
            limit,
            used,
            f"{reset_in:.0f}" if reset_in is not None else "?",
        )
