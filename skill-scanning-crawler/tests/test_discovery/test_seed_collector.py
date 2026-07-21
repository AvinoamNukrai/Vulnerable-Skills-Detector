"""Tests for seed_collector: local fixture parsing (no network)."""

from __future__ import annotations

import httpx
import pytest
import respx

from skill_scanning_crawler.common.config import SeedListConfig
from skill_scanning_crawler.discovery.seed_collector import (
    extract_github_repos_from_text,
    fetch_seed_list,
)

# ---------------------------------------------------------------------------
# extract_github_repos_from_text
# ---------------------------------------------------------------------------


def test_extract_from_markdown() -> None:
    text = """
# Awesome Skills

- [PDF Analyzer](https://github.com/alice/pdf-skill)
- [Code Helper](https://github.com/bob/code-helper)
"""
    pairs = extract_github_repos_from_text(text)
    assert ("alice", "pdf-skill") in pairs
    assert ("bob", "code-helper") in pairs


def test_extract_from_html() -> None:
    text = '<a href="https://github.com/charlie/my-skill">My Skill</a>'
    pairs = extract_github_repos_from_text(text)
    assert ("charlie", "my-skill") in pairs


def test_extract_deduplicates() -> None:
    text = "https://github.com/alice/repo https://github.com/alice/repo"
    pairs = extract_github_repos_from_text(text)
    assert pairs.count(("alice", "repo")) == 1


def test_extract_filters_excluded_owners() -> None:
    text = (
        "https://github.com/topics/agent https://github.com/search?q=skills"
        " https://github.com/alice/real-skill"
    )
    pairs = extract_github_repos_from_text(text)
    assert all(owner == "alice" for owner, _ in pairs)


def test_extract_git_suffix_stripped() -> None:
    text = "https://github.com/alice/skill.git"
    pairs = extract_github_repos_from_text(text)
    assert ("alice", "skill") in pairs


def test_extract_empty_text() -> None:
    assert extract_github_repos_from_text("") == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Deep links to skill subfolders — the dominant form in "awesome" lists.
        ("https://github.com/anthropics/skills/tree/main/document-skills", ("anthropics", "skills")),
        ("https://github.com/owner/repo/blob/main/SKILL.md", ("owner", "repo")),
        # Trailing slash.
        ("https://github.com/owner/repo/", ("owner", "repo")),
        # Markdown link wrapping a deep link.
        ("[x](https://github.com/a/b/tree/main/skills/pdf)", ("a", "b")),
    ],
)
def test_extract_captures_path_carrying_urls(text: str, expected: tuple[str, str]) -> None:
    """Regression: URLs with a path or trailing slash must still resolve to (owner, repo)."""
    assert expected in extract_github_repos_from_text(text)


def test_extract_strips_trailing_prose_dot() -> None:
    pairs = extract_github_repos_from_text("see https://github.com/alice/repo. done")
    assert ("alice", "repo") in pairs
    assert ("alice", "repo.") not in pairs


# ---------------------------------------------------------------------------
# fetch_seed_list — meta-refresh follow (moved-stub pages)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_fetch_seed_list_follows_meta_refresh() -> None:
    """A moved-stub page (HTTP 200 + <meta refresh>) must be followed to the target."""
    stub = '<html><head><meta http-equiv="refresh" content="0; url=https://x.test/final/"></head></html>'
    final = "- [Skill](https://github.com/moved/skill-repo)\n"
    respx.get("https://x.test/moved/").mock(return_value=httpx.Response(200, text=stub))
    respx.get("https://x.test/final/").mock(return_value=httpx.Response(200, text=final))

    cfg = SeedListConfig(name="moved-seed", url="https://x.test/moved/")
    candidates = await fetch_seed_list(cfg, cache=None)
    ids = {c.canonical_id for c in candidates}
    assert "github:moved/skill-repo" in ids


# ---------------------------------------------------------------------------
# fetch_seed_list — local fixture path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_seed_list_local_fixture(tmp_path: pytest.TempPathFactory) -> None:
    fixture = tmp_path / "seed.md"
    fixture.write_text(
        "https://github.com/alice/skill-a\nhttps://github.com/bob/skill-b\n"
    )
    cfg = SeedListConfig(name="test-seed", local_path=str(fixture))
    candidates = await fetch_seed_list(cfg, cache=None)
    ids = {c.canonical_id for c in candidates}
    assert "github:alice/skill-a" in ids
    assert "github:bob/skill-b" in ids


@pytest.mark.asyncio
async def test_fetch_seed_list_missing_local(tmp_path: pytest.TempPathFactory) -> None:
    cfg = SeedListConfig(name="test-seed", local_path=str(tmp_path / "nonexistent.md"))
    candidates = await fetch_seed_list(cfg, cache=None)
    assert candidates == []


@pytest.mark.asyncio
async def test_fetch_seed_list_neither_url_nor_path() -> None:
    cfg = SeedListConfig(name="empty")
    candidates = await fetch_seed_list(cfg, cache=None)
    assert candidates == []


@pytest.mark.asyncio
async def test_fetch_seed_list_provenance_recorded(tmp_path: pytest.TempPathFactory) -> None:
    fixture = tmp_path / "seed.txt"
    fixture.write_text("https://github.com/owner/repo\n")
    cfg = SeedListConfig(name="my-seed", local_path=str(fixture))
    candidates = await fetch_seed_list(cfg, cache=None)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.owner == "owner"
    assert cand.repo == "repo"
    assert "my-seed" in cand.discovery_sources
