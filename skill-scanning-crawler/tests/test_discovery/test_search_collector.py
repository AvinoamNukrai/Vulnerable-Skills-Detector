"""Tests for search_collector normalization (no network)."""

from __future__ import annotations

from datetime import UTC, datetime

from skill_scanning_crawler.discovery.search_collector import (
    _code_item_to_candidate,
    _repo_item_to_candidate,
)

_NOW = datetime.now(UTC)


def test_code_item_to_candidate_valid() -> None:
    item = {
        "repository": {
            "full_name": "alice/skill-repo",
            "html_url": "https://github.com/alice/skill-repo",
        }
    }
    cand = _code_item_to_candidate(item, "filename:SKILL.md", _NOW)
    assert cand is not None
    assert cand.owner == "alice"
    assert cand.repo == "skill-repo"
    assert cand.canonical_id == "github:alice/skill-repo"
    assert "filename:SKILL.md" in cand.discovery_queries


def test_code_item_to_candidate_missing_full_name() -> None:
    item = {"repository": {"html_url": "https://github.com/"}}
    cand = _code_item_to_candidate(item, "q", _NOW)
    assert cand is None


def test_code_item_to_candidate_missing_repository() -> None:
    item: dict[str, object] = {}
    cand = _code_item_to_candidate(item, "q", _NOW)
    assert cand is None


def test_repo_item_to_candidate_valid() -> None:
    item = {
        "full_name": "bob/my-skills",
        "html_url": "https://github.com/bob/my-skills",
    }
    cand = _repo_item_to_candidate(item, "SKILL.md in:path", _NOW)
    assert cand is not None
    assert cand.owner == "bob"
    assert cand.repo == "my-skills"


def test_repo_item_to_candidate_missing_full_name() -> None:
    item: dict[str, object] = {"html_url": "https://github.com/bob/my-skills"}
    cand = _repo_item_to_candidate(item, "q", _NOW)
    assert cand is None


def test_discovery_source_code_search() -> None:
    from skill_scanning_crawler.common.enums import DiscoverySource

    item = {
        "repository": {
            "full_name": "alice/repo",
            "html_url": "https://github.com/alice/repo",
        }
    }
    cand = _code_item_to_candidate(item, "q", _NOW)
    assert cand is not None
    assert DiscoverySource.GITHUB_CODE_SEARCH in cand.discovery_sources


def test_discovery_source_repo_search() -> None:
    from skill_scanning_crawler.common.enums import DiscoverySource

    item = {"full_name": "alice/repo", "html_url": "https://github.com/alice/repo"}
    cand = _repo_item_to_candidate(item, "q", _NOW)
    assert cand is not None
    assert DiscoverySource.GITHUB_REPO_SEARCH in cand.discovery_sources
