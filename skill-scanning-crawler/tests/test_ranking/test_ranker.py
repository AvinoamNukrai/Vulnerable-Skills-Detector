"""Tests for repository ranking logic."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from skill_scanning_crawler.common.enums import ValidationStatus
from skill_scanning_crawler.common.models import RepositoryRecord, ValidatedSkillCandidate
from skill_scanning_crawler.ranking.ranker import rank_repositories


def _repo(
    repo_id: str,
    stars: int = 0,
    is_fork: bool = False,
    is_archived: bool = False,
) -> RepositoryRecord:
    owner, name = repo_id.split(":")[-1].split("/")
    return RepositoryRecord(
        repository_id=repo_id,
        platform="github",
        owner=owner,
        name=name,
        full_name=f"{owner}/{name}",
        url=f"https://github.com/{owner}/{name}",
        description=None,
        stars=stars,
        forks=0,
        is_fork=is_fork,
        is_archived=is_archived,
        default_branch="main",
        commit_sha="abc",
        collected_at="2024-01-01T00:00:00+00:00",
    )


def _valid_skill(repo_id: str) -> ValidatedSkillCandidate:
    owner, name = repo_id.split(":")[-1].split("/")
    from datetime import UTC, datetime
    return ValidatedSkillCandidate(
        repository_id=repo_id,
        owner=owner,
        repo=name,
        skill_path="skills/test",
        skill_md_path="skills/test/SKILL.md",
        commit_sha="abc",
        discovery_sources=["seed"],
        discovery_queries=["q"],
        skill_md_content="---\nname: Test\ndescription: A test skill\n---\n",
        validation_status=ValidationStatus.VALID_STANDARD,
        validation_reason="ok",
        validated_at=datetime.now(UTC),
    )


def _make_config(top_n: int = 3, include_forks: bool = False, include_archived: bool = False) -> MagicMock:
    cfg = MagicMock()
    cfg.github.top_n_repositories = top_n
    cfg.github.include_forks = include_forks
    cfg.github.include_archived = include_archived
    return cfg


# ---------------------------------------------------------------------------


def test_selects_top_n_by_stars() -> None:
    repos = [
        _repo("github:a/r", stars=10),
        _repo("github:b/r", stars=50),
        _repo("github:c/r", stars=30),
    ]
    skills = [_valid_skill(r.repository_id) for r in repos]
    result = rank_repositories(repos, skills, _make_config(top_n=2))
    selected = [r for r in result if r.selected_for_export]
    assert len(selected) == 2
    stars = {r.stars for r in selected}
    assert 50 in stars
    assert 30 in stars


def test_excludes_forks_by_default() -> None:
    fork_repo = _repo("github:a/fork", stars=999, is_fork=True)
    good_repo = _repo("github:b/good", stars=10)
    skills = [_valid_skill(fork_repo.repository_id), _valid_skill(good_repo.repository_id)]
    result = rank_repositories([fork_repo, good_repo], skills, _make_config(top_n=5))
    selected = [r for r in result if r.selected_for_export]
    assert all(not r.is_fork for r in selected)


def test_includes_forks_when_configured() -> None:
    fork_repo = _repo("github:a/fork", stars=999, is_fork=True)
    skills = [_valid_skill(fork_repo.repository_id)]
    result = rank_repositories([fork_repo], skills, _make_config(top_n=5, include_forks=True))
    selected = [r for r in result if r.selected_for_export]
    assert len(selected) == 1


def test_excludes_archived_by_default() -> None:
    arch_repo = _repo("github:a/arch", stars=999, is_archived=True)
    skills = [_valid_skill(arch_repo.repository_id)]
    result = rank_repositories([arch_repo], skills, _make_config(top_n=5))
    selected = [r for r in result if r.selected_for_export]
    assert len(selected) == 0


def test_requires_at_least_one_valid_skill() -> None:
    repo = _repo("github:a/repo", stars=100)
    # No valid skills for this repo
    result = rank_repositories([repo], [], _make_config(top_n=5))
    selected = [r for r in result if r.selected_for_export]
    assert len(selected) == 0


def test_shortfall_does_not_pad(caplog: pytest.LogCaptureFixture) -> None:
    repos = [_repo("github:a/r", stars=10)]
    skills = [_valid_skill("github:a/r")]
    result = rank_repositories(repos, skills, _make_config(top_n=50))
    selected = [r for r in result if r.selected_for_export]
    assert len(selected) == 1  # only 1 available, not padded


def test_all_repos_returned_unselected_when_none_qualify() -> None:
    repos = [_repo("github:a/r", stars=10)]
    result = rank_repositories(repos, [], _make_config())
    # All repos returned, but none selected
    assert len(result) == 1
    assert not result[0].selected_for_export


def test_deterministic_ordering() -> None:
    repos = [_repo(f"github:owner/r{i}", stars=i * 10) for i in range(5)]
    skills = [_valid_skill(r.repository_id) for r in repos]
    result1 = rank_repositories(repos, skills, _make_config(top_n=3))
    result2 = rank_repositories(repos, skills, _make_config(top_n=3))
    sel1 = [r.repository_id for r in result1 if r.selected_for_export]
    sel2 = [r.repository_id for r in result2 if r.selected_for_export]
    assert sel1 == sel2
