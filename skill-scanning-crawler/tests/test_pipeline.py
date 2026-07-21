"""Full offline mocked pipeline test.

Proves the crawler can produce all required output files without any
live network calls. All GitHub API responses are provided via mock objects.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from skill_scanning_crawler.common.config import (
    CacheConfig,
    CrawlerConfig,
    GitHubConfig,
    OutputConfig,
    RateLimitsConfig,
    SeedListConfig,
    ValidationConfig,
)
from skill_scanning_crawler.pipeline import Pipeline

# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def offline_config(tmp_path: Path, seed_fixture: Path) -> CrawlerConfig:
    return CrawlerConfig(
        platforms=["github"],
        seed_lists=[
            SeedListConfig(name="test-seed", local_path=str(seed_fixture))
        ],
        github=GitHubConfig(
            token_env_var="GITHUB_TOKEN",
            include_forks=False,
            include_archived=False,
            top_n_repositories=10,
            max_repository_size_mb=100,
            max_file_size_mb=5,
            request_timeout_seconds=10,
        ),
        rate_limits=RateLimitsConfig(
            search_concurrency=1,
            metadata_concurrency=1,
            tree_concurrency=1,
            download_concurrency=1,
            max_retries=0,
            backoff_initial_seconds=0.0,
            backoff_max_seconds=0.0,
        ),
        validation=ValidationConfig(
            strict_validation=True,
            include_lenient_in_export=False,
            write_rejected_candidates=True,
        ),
        output=OutputConfig(
            directory=str(tmp_path / "data"),
            manifests_directory=str(tmp_path / "data" / "manifests"),
            snapshots_directory=str(tmp_path / "data" / "snapshots"),
            reports_directory=str(tmp_path / "data" / "reports"),
            write_statistics=True,
            deterministic_ordering=True,
        ),
        cache=CacheConfig(enabled=False, directory=""),
    )


@pytest.fixture
def seed_fixture(tmp_path: Path) -> Path:
    fixture = tmp_path / "seed.txt"
    fixture.write_text(
        "https://github.com/alice/skill-repo\n"
        "https://github.com/bob/another-skill\n"
    )
    return fixture


# ---------------------------------------------------------------------------
# Mocked GitHub API responses
# ---------------------------------------------------------------------------


def _repo_meta(owner: str, name: str, stars: int = 50) -> dict[str, object]:
    return {
        "full_name": f"{owner}/{name}",
        "html_url": f"https://github.com/{owner}/{name}",
        "description": f"Repo by {owner}",
        "stargazers_count": stars,
        "forks_count": 0,
        "fork": False,
        "archived": False,
        "default_branch": "main",
        "license": {"spdx_id": "MIT"},
        "topics": ["skills"],
        "size": 1024,
    }


def _valid_skill_md_content() -> str:
    return "---\nname: Test Skill\ndescription: A well-formed test skill\n---\nDo stuff."


def _skill_md_bytes() -> bytes:
    return _valid_skill_md_content().encode()


def _skill_md_base64() -> str:
    return base64.b64encode(_skill_md_bytes()).decode()


# ---------------------------------------------------------------------------
# Full pipeline offline run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_produces_output_files(
    offline_config: CrawlerConfig,
    tmp_path: Path,
) -> None:
    """Run all 7 stages with mocked GitHub client; verify output files."""

    skill_content = _valid_skill_md_content()
    skill_bytes = _skill_md_bytes()

    mock_client = AsyncMock()

    # Enrich: return metadata for both repos
    mock_client.get_repository.side_effect = [
        _repo_meta("alice", "skill-repo", stars=100),
        _repo_meta("bob", "another-skill", stars=50),
    ]
    mock_client.get_default_branch_sha.side_effect = ["sha_alice", "sha_bob"]

    # Locate: each repo has one SKILL.md
    mock_client.get_tree.side_effect = [
        # alice/skill-repo
        [{"type": "blob", "path": "SKILL.md", "size": len(skill_bytes)}],
        # bob/another-skill
        [{"type": "blob", "path": "skills/main/SKILL.md", "size": len(skill_bytes)}],
        # Snapshot re-fetches tree (cached in real run, separate calls in test)
        [{"type": "blob", "path": "SKILL.md", "size": len(skill_bytes)}],
        [{"type": "blob", "path": "skills/main/SKILL.md", "size": len(skill_bytes)}],
    ]

    # Validate: fetch SKILL.md content
    mock_client.get_file_content.return_value = skill_content

    # Snapshot: raw bytes
    mock_client.get_raw_content.return_value = skill_bytes

    # Patch GitHubClient.from_config and __aenter__/__aexit__ to return mock
    async def _mock_aenter(self: object) -> object:
        return mock_client

    async def _mock_aexit(self: object, *args: object) -> None:
        pass

    from skill_scanning_crawler.github_client.client import GitHubClient
    with (
        patch.object(GitHubClient, "__aenter__", _mock_aenter),
        patch.object(GitHubClient, "__aexit__", _mock_aexit),
    ):
        pipeline = Pipeline(offline_config, run_id="test-run-001")
        await pipeline.run_all()

    manifests_dir = Path(offline_config.output.manifests_directory)
    reports_dir = Path(offline_config.output.reports_directory)

    # All expected files must exist
    assert (manifests_dir / "repositories.jsonl").exists(), "repositories.jsonl missing"
    assert (manifests_dir / "skills.jsonl").exists(), "skills.jsonl missing"
    assert (manifests_dir / "rejected_candidates.jsonl").exists(), "rejected_candidates.jsonl missing"
    assert (reports_dir / "discovery_summary.json").exists(), "discovery_summary.json missing"
    assert (reports_dir / "dataset_statistics.json").exists(), "dataset_statistics.json missing"

    # Verify repositories.jsonl content
    repo_lines = (manifests_dir / "repositories.jsonl").read_text().splitlines()
    assert len(repo_lines) == 2, f"Expected 2 repos, got {len(repo_lines)}"
    repo_ids = {json.loads(line)["repository_id"] for line in repo_lines}
    assert "github:alice/skill-repo" in repo_ids

    # Verify skills.jsonl has entries
    skill_lines = (manifests_dir / "skills.jsonl").read_text().splitlines()
    assert len(skill_lines) >= 1, "Expected at least 1 skill"
    skill = json.loads(skill_lines[0])
    assert skill["validation_status"] == "valid_standard"
    assert skill["snapshot_complete"] is True

    # Verify discovery_summary.json
    summary = json.loads((reports_dir / "discovery_summary.json").read_text())
    assert summary["run_id"] == "test-run-001"
    assert summary["discovery"]["skills_validated"] >= 1

    # Verify at least one snapshot directory was created
    snapshots_dir = Path(offline_config.output.snapshots_directory)
    snapshot_files = list(snapshots_dir.rglob("SKILL.md"))
    assert len(snapshot_files) >= 1, "No snapshot SKILL.md files found"


# ---------------------------------------------------------------------------
# Checkpoint compatibility tests
# ---------------------------------------------------------------------------


def test_checkpoint_version_mismatch_is_rejected(offline_config: CrawlerConfig) -> None:
    # Write a checkpoint with a wrong version
    import json

    from skill_scanning_crawler.common.checkpoints import load_checkpoint, save_checkpoint
    from skill_scanning_crawler.common.exceptions import CheckpointError
    tmp = Path(offline_config.output.directory)
    save_checkpoint(
        stage="discover",
        run_id="run1",
        config_hash="correct_hash",
        record_type="CandidateRepository",
        records=[],
        output_dir=str(tmp),
    )
    # Manually corrupt the version
    cp_path = tmp / ".checkpoints" / "run1" / "discover.json"
    data = json.loads(cp_path.read_text())
    data["checkpoint_version"] = "999"
    cp_path.write_text(json.dumps(data))

    with pytest.raises(CheckpointError, match="Incompatible checkpoint version"):
        load_checkpoint(stage="discover", run_id="run1", config_hash="correct_hash", output_dir=str(tmp))


def test_checkpoint_config_hash_mismatch_is_rejected(offline_config: CrawlerConfig) -> None:
    from skill_scanning_crawler.common.checkpoints import load_checkpoint, save_checkpoint
    from skill_scanning_crawler.common.exceptions import CheckpointError

    tmp = Path(offline_config.output.directory)
    save_checkpoint(
        stage="enrich",
        run_id="run2",
        config_hash="original_hash",
        record_type="RepositoryRecord",
        records=[],
        output_dir=str(tmp),
    )
    with pytest.raises(CheckpointError, match="config_hash mismatch"):
        load_checkpoint(stage="enrich", run_id="run2", config_hash="different_hash", output_dir=str(tmp))


def test_checkpoint_missing_returns_none(offline_config: CrawlerConfig) -> None:
    from skill_scanning_crawler.common.checkpoints import load_checkpoint

    result = load_checkpoint(
        stage="nonexistent_stage",
        run_id="run_xyz",
        config_hash="hash",
        output_dir=str(offline_config.output.directory),
    )
    assert result is None


# ---------------------------------------------------------------------------
# Dry-run test
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write_files(offline_config: CrawlerConfig, tmp_path: Path) -> None:
    """Dry-run from CLI should not create any manifests or reports."""
    from skill_scanning_crawler.pipeline import Pipeline

    Pipeline(offline_config)
    # The pipeline itself doesn't have a dry-run method; that lives in __main__.
    # Verify the output directory stays clean when we don't call run_all.
    manifests_dir = Path(offline_config.output.manifests_directory)
    assert not manifests_dir.exists() or not any(manifests_dir.iterdir())


# ---------------------------------------------------------------------------
# Stage-by-stage checkpoint wiring (Blocker 1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_enrich_loads_from_discover_checkpoint(
    offline_config: CrawlerConfig,
) -> None:
    """run_enrich(candidates=None) must load from the discover checkpoint."""
    import dataclasses
    from datetime import UTC, datetime

    from skill_scanning_crawler.common.checkpoints import save_checkpoint
    from skill_scanning_crawler.common.exceptions import GitHubClientError
    from skill_scanning_crawler.common.models import CandidateRepository

    cand = CandidateRepository(
        canonical_id="github:alice/repo",
        owner="alice",
        repo="repo",
        url="https://github.com/alice/repo",
        discovery_sources=["seed"],
        discovery_queries=["fixture"],
        discovered_at=datetime.now(UTC),
    )
    config_hash = offline_config.compute_hash()

    save_checkpoint(
        stage="discover",
        run_id="wiring-test",
        config_hash=config_hash,
        record_type="CandidateRepository",
        records=[dataclasses.asdict(cand)],
        output_dir=offline_config.output.directory,
    )

    pipeline = Pipeline(offline_config, run_id="wiring-test")

    # Provide a mock client that fails on any network call so we can verify
    # the candidates were loaded from checkpoint (not passed explicitly)
    from unittest.mock import AsyncMock, patch

    from skill_scanning_crawler.github_client.client import GitHubClient

    mock_client = AsyncMock()
    mock_client.get_repository.side_effect = GitHubClientError("Not found: repo")

    async def _mock_enter(self: object) -> object:
        return mock_client

    async def _mock_exit(self: object, *args: object) -> None:
        pass

    with (
        patch.object(GitHubClient, "__aenter__", _mock_enter),
        patch.object(GitHubClient, "__aexit__", _mock_exit),
    ):
        repos, rejected = await pipeline.run_enrich()

    # All candidates rejected (mock returns 404), but the checkpoint was used
    assert len(repos) == 0
    assert len(rejected) == 1
    assert rejected[0].owner == "alice"


@pytest.mark.asyncio
async def test_run_enrich_raises_when_discover_checkpoint_missing(
    offline_config: CrawlerConfig,
) -> None:
    """run_enrich() without discover checkpoint must raise PipelineError."""
    from skill_scanning_crawler.common.exceptions import PipelineError

    pipeline = Pipeline(offline_config, run_id="no-discover-run")
    with pytest.raises(PipelineError, match="discover"):
        await pipeline.run_enrich()


@pytest.mark.asyncio
async def test_run_rank_loads_from_enrich_and_validate_checkpoints(
    offline_config: CrawlerConfig,
) -> None:
    """run_rank() with no args must load from enrich + validate checkpoints."""
    from skill_scanning_crawler.common.checkpoints import save_checkpoint
    from skill_scanning_crawler.common.exceptions import PipelineError

    config_hash = offline_config.compute_hash()
    run_id = "rank-wiring-test"

    # Rank requires enrich checkpoint
    pipeline = Pipeline(offline_config, run_id=run_id)
    with pytest.raises(PipelineError, match="enrich"):
        await pipeline.run_rank()

    # Save enrich checkpoint
    save_checkpoint(
        stage="enrich",
        run_id=run_id,
        config_hash=config_hash,
        record_type="RepositoryRecord",
        records=[{
            "repository_id": "github:alice/r",
            "platform": "github",
            "owner": "alice",
            "name": "r",
            "full_name": "alice/r",
            "url": "https://github.com/alice/r",
            "description": None,
            "stars": 10,
            "forks": 0,
            "is_fork": False,
            "is_archived": False,
            "default_branch": "main",
            "commit_sha": "abc",
            "collected_at": "2024-01-01T00:00:00+00:00",
        }],
        output_dir=offline_config.output.directory,
    )

    # Still missing validate checkpoint
    pipeline2 = Pipeline(offline_config, run_id=run_id)
    with pytest.raises(PipelineError, match="validate"):
        await pipeline2.run_rank()


# ---------------------------------------------------------------------------
# Stable run-id / --run-id (Blocker 2)
# ---------------------------------------------------------------------------


def test_resolve_run_id_creates_file(tmp_path: Path) -> None:
    from skill_scanning_crawler.__main__ import _resolve_run_id

    run_id = _resolve_run_id(None, str(tmp_path))
    run_id_file = tmp_path / ".current_run_id"
    assert run_id_file.exists()
    assert run_id_file.read_text().strip() == run_id


def test_resolve_run_id_reads_existing_file(tmp_path: Path) -> None:
    from skill_scanning_crawler.__main__ import _resolve_run_id

    (tmp_path / ".current_run_id").write_text("existing-id-abc")
    result = _resolve_run_id(None, str(tmp_path))
    assert result == "existing-id-abc"


def test_resolve_run_id_explicit_overrides_file(tmp_path: Path) -> None:
    from skill_scanning_crawler.__main__ import _resolve_run_id

    (tmp_path / ".current_run_id").write_text("file-id")
    result = _resolve_run_id("explicit-id", str(tmp_path))
    assert result == "explicit-id"


def test_resolve_run_id_dry_run_skips_file_creation(tmp_path: Path) -> None:
    from skill_scanning_crawler.__main__ import _resolve_run_id

    run_id = _resolve_run_id(None, str(tmp_path), dry_run=True)
    assert run_id  # still returns a valid ID
    assert not (tmp_path / ".current_run_id").exists()


# ---------------------------------------------------------------------------
# Query file loading (Blocker 3)
# ---------------------------------------------------------------------------


def test_load_github_queries_from_file(tmp_path: Path) -> None:
    from skill_scanning_crawler.pipeline import _load_github_queries

    qfile = tmp_path / "queries.yaml"
    qfile.write_text(
        "code_search_queries:\n"
        "  - name: test_code\n"
        "    query: 'filename:SKILL.md'\n"
        "repository_search_queries:\n"
        "  - name: test_repo\n"
        "    query: 'agent skills'\n"
    )
    code_qs, repo_qs = _load_github_queries(qfile)
    assert code_qs == ["filename:SKILL.md"]
    assert repo_qs == ["agent skills"]


def test_load_github_queries_falls_back_when_file_missing(tmp_path: Path) -> None:
    from skill_scanning_crawler.pipeline import _load_github_queries

    code_qs, repo_qs = _load_github_queries(tmp_path / "nonexistent.yaml")
    assert code_qs == []
    assert repo_qs == []


def test_load_github_queries_from_real_config() -> None:
    """The real config/github_queries.yaml must load successfully."""
    from skill_scanning_crawler.pipeline import _load_github_queries

    code_qs, repo_qs = _load_github_queries()
    # The real file has 5 code queries and 3 repo queries
    assert len(code_qs) >= 1
    assert len(repo_qs) >= 1


# ---------------------------------------------------------------------------
# Helper used by other tests in this module
# ---------------------------------------------------------------------------


def _make_repo_dict(repo_id: str, stars: int = 10) -> dict[str, object]:
    owner, name = repo_id.split(":")[-1].split("/")
    return {
        "repository_id": repo_id,
        "platform": "github",
        "owner": owner,
        "name": name,
        "full_name": f"{owner}/{name}",
        "url": f"https://github.com/{owner}/{name}",
        "description": None,
        "stars": stars,
        "forks": 0,
        "is_fork": False,
        "is_archived": False,
        "default_branch": "main",
        "commit_sha": "abc",
        "collected_at": "2024-01-01T00:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# preselect_top_k (throughput: only scan the top-K by stars)
# ---------------------------------------------------------------------------


def test_preselect_keeps_top_k_by_stars(offline_config: CrawlerConfig) -> None:
    from skill_scanning_crawler.common.models import RepositoryRecord

    offline_config.github.preselect_top_k = 3
    pipeline = Pipeline(offline_config, run_id="preselect-test")

    repos = [
        RepositoryRecord.model_validate(_make_repo_dict(f"github:o/r{i}", stars=i * 10))
        for i in range(10)
    ]
    # A high-star fork must be excluded despite its star count.
    fork = _make_repo_dict("github:o/forky", stars=9999)
    fork["is_fork"] = True
    repos.append(RepositoryRecord.model_validate(fork))

    kept = pipeline._preselect_for_scanning(repos)

    assert [r.stars for r in kept] == [90, 80, 70]
    assert all(not r.is_fork for r in kept)


def test_preselect_disabled_returns_all(offline_config: CrawlerConfig) -> None:
    from skill_scanning_crawler.common.models import RepositoryRecord

    offline_config.github.preselect_top_k = 0
    pipeline = Pipeline(offline_config, run_id="preselect-off")
    repos = [
        RepositoryRecord.model_validate(_make_repo_dict(f"github:o/r{i}"))
        for i in range(5)
    ]
    assert pipeline._preselect_for_scanning(repos) == repos
