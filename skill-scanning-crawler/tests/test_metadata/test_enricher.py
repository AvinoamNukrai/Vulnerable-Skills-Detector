"""Tests for metadata enricher using mocked GitHubClient."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from skill_scanning_crawler.common.enums import ValidationStatus
from skill_scanning_crawler.common.exceptions import GitHubClientError
from skill_scanning_crawler.common.models import CandidateRepository, RepositoryRecord
from skill_scanning_crawler.discovery.normalizer import make_canonical_id, make_canonical_url
from skill_scanning_crawler.metadata.enricher import enrich_repositories


def _make_config() -> MagicMock:
    cfg = MagicMock()
    cfg.rate_limits.metadata_concurrency = 4
    return cfg


def _make_candidate(owner: str = "alice", repo: str = "skills") -> CandidateRepository:
    return CandidateRepository(
        canonical_id=make_canonical_id(owner, repo),
        owner=owner,
        repo=repo,
        url=make_canonical_url(owner, repo),
        discovery_sources=["seed_test"],
        discovery_queries=["fixture"],
        discovered_at=datetime.now(UTC),
    )


def _make_repo_meta(owner: str = "alice", repo: str = "skills") -> dict[str, object]:
    return {
        "full_name": f"{owner}/{repo}",
        "html_url": f"https://github.com/{owner}/{repo}",
        "description": "A skill repo",
        "stargazers_count": 123,
        "forks_count": 10,
        "fork": False,
        "archived": False,
        "default_branch": "main",
        "license": {"spdx_id": "MIT"},
        "topics": ["skills", "agent"],
        "size": 4096,
    }


@pytest.mark.asyncio
async def test_enrich_happy_path() -> None:
    cand = _make_candidate()
    mock_client = AsyncMock()
    mock_client.get_repository.return_value = _make_repo_meta()
    mock_client.get_default_branch_sha.return_value = "abc123"

    repos, rejected = await enrich_repositories([cand], mock_client, _make_config())

    assert len(repos) == 1
    assert len(rejected) == 0
    repo = repos[0]
    assert isinstance(repo, RepositoryRecord)
    assert repo.stars == 123
    assert repo.commit_sha == "abc123"
    assert repo.license == "MIT"
    assert "skills" in repo.topics


@pytest.mark.asyncio
async def test_enrich_404_produces_rejected() -> None:
    cand = _make_candidate()
    mock_client = AsyncMock()
    mock_client.get_repository.side_effect = GitHubClientError("Not found: /repos/alice/skills")

    repos, rejected = await enrich_repositories([cand], mock_client, _make_config())

    assert len(repos) == 0
    assert len(rejected) == 1
    assert rejected[0].rejection_status == ValidationStatus.REPOSITORY_UNAVAILABLE


@pytest.mark.asyncio
async def test_enrich_sha_failure_produces_rejected() -> None:
    cand = _make_candidate()
    mock_client = AsyncMock()
    mock_client.get_repository.return_value = _make_repo_meta()
    mock_client.get_default_branch_sha.side_effect = GitHubClientError("Network error")

    repos, rejected = await enrich_repositories([cand], mock_client, _make_config())

    assert len(repos) == 0
    assert len(rejected) == 1


@pytest.mark.asyncio
async def test_enrich_multiple_candidates() -> None:
    candidates = [_make_candidate("alice", "r1"), _make_candidate("bob", "r2")]
    mock_client = AsyncMock()
    mock_client.get_repository.side_effect = [
        _make_repo_meta("alice", "r1"),
        _make_repo_meta("bob", "r2"),
    ]
    mock_client.get_default_branch_sha.side_effect = ["sha1", "sha2"]

    repos, rejected = await enrich_repositories(candidates, mock_client, _make_config())

    assert len(repos) == 2
    assert len(rejected) == 0
    commit_shas = {r.commit_sha for r in repos}
    assert "sha1" in commit_shas
    assert "sha2" in commit_shas


@pytest.mark.asyncio
async def test_enrich_unexpected_exception_does_not_abort_stage() -> None:
    """Regression: a non-GitHubClientError on one repo must not kill the whole stage.

    The bad candidate is rejected; the good candidate still enriches successfully.
    """
    good = _make_candidate("good", "repo")
    bad = _make_candidate("bad", "repo")
    mock_client = AsyncMock()

    async def _get_repo(owner: str, repo: str) -> dict[str, object]:
        if owner == "bad":
            raise RuntimeError("boom: malformed JSON / protocol error")
        return _make_repo_meta(owner, repo)

    mock_client.get_repository.side_effect = _get_repo
    mock_client.get_default_branch_sha.return_value = "sha1"

    repos, rejected = await enrich_repositories([good, bad], mock_client, _make_config())

    assert {r.owner for r in repos} == {"good"}
    assert len(rejected) == 1
    assert rejected[0].owner == "bad"
    assert rejected[0].rejection_status == ValidationStatus.REPOSITORY_UNAVAILABLE


@pytest.mark.asyncio
async def test_enrich_dedupes_redirect_aliases() -> None:
    """Regression: two discovered names that resolve to the same repo collapse to one.

    A repo renamed on GitHub is reachable via its old and new name; both redirect
    to the same repo, so GitHub returns the same full_name. Discovery dedup keys on
    the discovered name, so both survive to enrichment and must be merged here.
    """
    cand_old = _make_candidate("affaan-m", "ECC")
    cand_new = _make_candidate("affaan-m", "everything-claude-code")
    mock_client = AsyncMock()
    # Both lookups resolve to the same full_name (the redirect target).
    mock_client.get_repository.side_effect = lambda o, r: _make_repo_meta("affaan-m", "ECC")
    mock_client.get_default_branch_sha.return_value = "sha1"

    repos, _ = await enrich_repositories([cand_old, cand_new], mock_client, _make_config())

    assert len(repos) == 1
    assert repos[0].full_name == "affaan-m/ECC"
    # Provenance from both aliases is preserved after the merge.
    assert "seed_test" in repos[0].discovery_sources


@pytest.mark.asyncio
async def test_enrich_no_license() -> None:
    cand = _make_candidate()
    meta = _make_repo_meta()
    meta["license"] = None
    mock_client = AsyncMock()
    mock_client.get_repository.return_value = meta
    mock_client.get_default_branch_sha.return_value = "sha1"

    repos, _ = await enrich_repositories([cand], mock_client, _make_config())

    assert repos[0].license is None
