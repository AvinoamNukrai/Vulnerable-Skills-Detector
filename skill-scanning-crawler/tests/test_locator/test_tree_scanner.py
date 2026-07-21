"""Tests for tree_scanner: SKILL.md detection in git trees."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from skill_scanning_crawler.common.models import RepositoryRecord
from skill_scanning_crawler.locator.tree_scanner import _tree_to_candidates, locate_skills


def _make_repo(owner: str = "alice", name: str = "skills", sha: str = "abc123") -> RepositoryRecord:
    return RepositoryRecord(
        repository_id=f"github:{owner.lower()}/{name.lower()}",
        platform="github",
        owner=owner,
        name=name,
        full_name=f"{owner}/{name}",
        url=f"https://github.com/{owner}/{name}",
        description=None,
        stars=10,
        forks=0,
        is_fork=False,
        is_archived=False,
        default_branch="main",
        commit_sha=sha,
        collected_at="2024-01-01T00:00:00+00:00",
    )


def _flat_tree(*paths: str) -> list[dict[str, object]]:
    return [
        {"type": "blob", "path": p, "size": 100}
        for p in paths
    ]


# ---------------------------------------------------------------------------
# _tree_to_candidates (pure function)
# ---------------------------------------------------------------------------


def test_single_skill_at_root() -> None:
    repo = _make_repo()
    tree = _flat_tree("SKILL.md", "README.md")
    candidates = _tree_to_candidates(tree, repo)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.skill_path == "."
    assert cand.skill_md_path == "SKILL.md"


def test_skill_in_subdirectory() -> None:
    repo = _make_repo()
    tree = _flat_tree("skills/pdf/SKILL.md", "skills/pdf/handler.py", "README.md")
    candidates = _tree_to_candidates(tree, repo)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.skill_path == "skills/pdf"
    assert cand.skill_md_path == "skills/pdf/SKILL.md"


def test_multiple_skills_in_repo() -> None:
    repo = _make_repo()
    tree = _flat_tree(
        "skills/pdf/SKILL.md",
        "skills/web/SKILL.md",
        "skills/pdf/handler.py",
    )
    candidates = _tree_to_candidates(tree, repo)
    assert len(candidates) == 2
    paths = {c.skill_path for c in candidates}
    assert "skills/pdf" in paths
    assert "skills/web" in paths


def test_no_skill_md_returns_empty() -> None:
    repo = _make_repo()
    tree = _flat_tree("README.md", "src/main.py")
    candidates = _tree_to_candidates(tree, repo)
    assert candidates == []


def test_max_skills_per_repo_caps_and_prefers_shallow() -> None:
    """An aggregator repo's SKILL.md files are capped, keeping shallowest paths."""
    repo = _make_repo()
    tree = _flat_tree(
        "SKILL.md",                         # depth 0
        "skills/a/SKILL.md",                # depth 2
        "skills/b/SKILL.md",                # depth 2
        "vendor/x/y/z/SKILL.md",            # depth 4 (should be dropped by cap=2)
    )
    candidates = _tree_to_candidates(tree, repo, max_skills=2)
    assert len(candidates) == 2
    kept = {c.skill_md_path for c in candidates}
    assert "SKILL.md" in kept                     # shallowest always kept
    assert "vendor/x/y/z/SKILL.md" not in kept     # deepest dropped


def test_max_skills_per_repo_unlimited_by_default() -> None:
    repo = _make_repo()
    tree = _flat_tree("a/SKILL.md", "b/SKILL.md", "c/SKILL.md")
    assert len(_tree_to_candidates(tree, repo)) == 3
    assert len(_tree_to_candidates(tree, repo, max_skills=0)) == 3


def test_tree_file_sizes_populated() -> None:
    repo = _make_repo()
    tree = [
        {"type": "blob", "path": "skills/pdf/SKILL.md", "size": 512},
        {"type": "blob", "path": "skills/pdf/helper.py", "size": 1024},
        {"type": "blob", "path": "README.md", "size": 2048},
    ]
    candidates = _tree_to_candidates(tree, repo)
    assert len(candidates) == 1
    sizes = candidates[0].tree_file_sizes
    assert sizes.get("skills/pdf/SKILL.md") == 512
    assert sizes.get("skills/pdf/helper.py") == 1024
    assert "README.md" not in sizes  # not in skill dir


def test_tree_ignores_tree_type_entries() -> None:
    repo = _make_repo()
    tree = [
        {"type": "tree", "path": "skills"},       # directory entry, ignored
        {"type": "blob", "path": "skills/SKILL.md", "size": 100},
    ]
    candidates = _tree_to_candidates(tree, repo)
    assert len(candidates) == 1


def test_provenance_inherited_from_repo() -> None:
    repo = _make_repo()
    repo = repo.model_copy(update={
        "discovery_sources": ["seed_test"],
        "discovery_queries": ["q=SKILL.md"],
    })
    tree = _flat_tree("SKILL.md")
    candidates = _tree_to_candidates(tree, repo)
    assert candidates[0].discovery_sources == ["seed_test"]


# ---------------------------------------------------------------------------
# locate_skills (integration over mocked client)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_locate_skills_uses_commit_sha() -> None:
    repo = _make_repo(sha="deadbeef")
    mock_client = AsyncMock()
    mock_client.get_tree.return_value = [
        {"type": "blob", "path": "SKILL.md", "size": 200}
    ]
    mock_cfg = MagicMock()
    mock_cfg.rate_limits.tree_concurrency = 2
    mock_cfg.github.max_skills_per_repo = 0

    candidates = await locate_skills([repo], mock_client, mock_cfg)

    mock_client.get_tree.assert_called_once_with("alice", "skills", "deadbeef")
    assert len(candidates) == 1


@pytest.mark.asyncio
async def test_locate_skills_tree_fetch_failure_returns_empty() -> None:
    from skill_scanning_crawler.common.exceptions import GitHubClientError

    repo = _make_repo()
    mock_client = AsyncMock()
    mock_client.get_tree.side_effect = GitHubClientError("Not found")
    mock_cfg = MagicMock()
    mock_cfg.rate_limits.tree_concurrency = 2
    mock_cfg.github.max_skills_per_repo = 0

    candidates = await locate_skills([repo], mock_client, mock_cfg)
    assert candidates == []
