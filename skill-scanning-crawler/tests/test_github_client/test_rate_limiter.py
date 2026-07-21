"""Tests for RateLimiter (backoff math and semaphore categories)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from skill_scanning_crawler.github_client.rate_limiter import RateLimiter


def test_semaphore_search_category() -> None:
    rl = RateLimiter(search_concurrency=3)
    sem = rl.semaphore("search")
    # Lazy creation — just verify it's an asyncio.Semaphore
    assert isinstance(sem, asyncio.Semaphore)


def test_semaphore_fallback_to_metadata_for_unknown() -> None:
    rl = RateLimiter(metadata_concurrency=5)
    sem = rl.semaphore("unknown_category")
    assert isinstance(sem, asyncio.Semaphore)


def test_semaphore_same_instance_on_repeated_call() -> None:
    rl = RateLimiter()
    sem1 = rl.semaphore("download")
    sem2 = rl.semaphore("download")
    assert sem1 is sem2


def test_backoff_delay_within_bounds() -> None:
    rl = RateLimiter(backoff_initial=1.0, backoff_max=30.0)
    for attempt in range(6):
        delay = rl.backoff_delay(attempt)
        assert 0.0 <= delay <= 30.0


def test_backoff_delay_caps_at_max() -> None:
    rl = RateLimiter(backoff_initial=100.0, backoff_max=5.0)
    for attempt in range(10):
        delay = rl.backoff_delay(attempt)
        assert delay <= 5.0


def test_log_rate_limit_headers_safe(caplog: pytest.LogCaptureFixture) -> None:
    rl = RateLimiter()
    mock_resp = MagicMock()
    mock_resp.headers = {
        "x-ratelimit-remaining": "42",
        "x-ratelimit-limit": "5000",
        "x-ratelimit-used": "58",
        "x-ratelimit-reset": "9999999999",
    }
    import logging
    with caplog.at_level(logging.DEBUG):
        rl.log_rate_limit_headers(mock_resp)
    # Verify no token value appears in any log message
    assert "Authorization" not in caplog.text
    assert "Bearer" not in caplog.text
    assert "token" not in caplog.text.lower().replace("rate_limit", "")


def test_log_rate_limit_headers_missing_headers(caplog: pytest.LogCaptureFixture) -> None:
    rl = RateLimiter()
    mock_resp = MagicMock()
    mock_resp.headers = {}  # empty headers — should not crash
    rl.log_rate_limit_headers(mock_resp)
