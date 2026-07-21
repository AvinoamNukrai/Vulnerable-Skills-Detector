"""Tests for URL normalization and deduplication."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from skill_scanning_crawler.common.models import CandidateRepository
from skill_scanning_crawler.discovery.normalizer import (
    deduplicate,
    make_canonical_id,
    make_canonical_url,
    normalize_github_url,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/owner/repo", ("owner", "repo")),
        ("https://github.com/owner/repo.git", ("owner", "repo")),
        ("https://github.com/owner/repo/tree/main", ("owner", "repo")),
        ("https://github.com/owner/repo?tab=readme", ("owner", "repo")),
        ("https://github.com/owner/repo#readme", ("owner", "repo")),
        ("http://github.com/owner/repo", ("owner", "repo")),
    ],
)
def test_normalize_github_url_valid(url: str, expected: tuple[str, str]) -> None:
    assert normalize_github_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/owner/repo",
        "https://github.com/",
        "https://github.com/owner",
        "not-a-url",
        "",
    ],
)
def test_normalize_github_url_invalid(url: str) -> None:
    assert normalize_github_url(url) is None


def test_make_canonical_id_lowercases() -> None:
    assert make_canonical_id("Owner", "Repo") == "github:owner/repo"


def test_make_canonical_url() -> None:
    assert make_canonical_url("octocat", "Hello-World") == "https://github.com/octocat/Hello-World"


def _cand(owner: str, repo: str, source: str = "seed") -> CandidateRepository:
    return CandidateRepository(
        canonical_id=make_canonical_id(owner, repo),
        owner=owner,
        repo=repo,
        url=make_canonical_url(owner, repo),
        discovery_sources=[source],
        discovery_queries=[f"from:{source}"],
        discovered_at=datetime.now(UTC),
    )


def test_deduplicate_removes_exact_duplicates() -> None:
    c1 = _cand("owner", "repo", "seed_a")
    c2 = _cand("owner", "repo", "seed_a")
    result = deduplicate([c1, c2])
    assert len(result) == 1


def test_deduplicate_merges_sources() -> None:
    c1 = _cand("owner", "repo", "seed_a")
    c2 = _cand("Owner", "Repo", "seed_b")  # same repo, different case
    result = deduplicate([c1, c2])
    assert len(result) == 1
    assert "seed_a" in result[0].discovery_sources
    assert "seed_b" in result[0].discovery_sources


def test_deduplicate_merges_queries() -> None:
    c1 = _cand("owner", "repo", "seed_a")
    c2 = _cand("owner", "repo", "seed_b")
    result = deduplicate([c1, c2])
    assert len(result[0].discovery_queries) == 2


def test_deduplicate_preserves_distinct_repos() -> None:
    candidates = [_cand("a", "repo1"), _cand("a", "repo2"), _cand("b", "repo1")]
    result = deduplicate(candidates)
    assert len(result) == 3


def test_deduplicate_no_source_duplication() -> None:
    c1 = _cand("owner", "repo", "seed_a")
    c2 = _cand("owner", "repo", "seed_a")
    result = deduplicate([c1, c2])
    assert result[0].discovery_sources.count("seed_a") == 1
