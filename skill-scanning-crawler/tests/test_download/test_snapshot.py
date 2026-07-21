"""Tests for snapshot downloader: path safety, hashing, binary detection."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from skill_scanning_crawler.common.enums import ValidationStatus
from skill_scanning_crawler.common.models import (
    RepositoryRecord,
    SkillRecord,
    ValidatedSkillCandidate,
)
from skill_scanning_crawler.download.snapshot import (
    _content_hash,
    _is_binary_bytes,
    _is_binary_path,
    _safe_relative_path,
    download_snapshots,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_is_binary_path_png() -> None:
    assert _is_binary_path("icon.png") is True


def test_is_binary_path_md_is_not_binary() -> None:
    assert _is_binary_path("SKILL.md") is False


def test_is_binary_path_py_is_not_binary() -> None:
    assert _is_binary_path("handler.py") is False


def test_is_binary_bytes_text() -> None:
    assert _is_binary_bytes(b"Hello, world! This is plain text.\n") is False


def test_is_binary_bytes_null_bytes() -> None:
    assert _is_binary_bytes(b"\x00\x01\x02" * 100) is True


def test_is_binary_bytes_empty() -> None:
    assert _is_binary_bytes(b"") is False


def test_safe_relative_path_valid(tmp_path: Path) -> None:
    result = _safe_relative_path(tmp_path, "subdir/file.txt")
    assert result == tmp_path / "subdir/file.txt"


def test_safe_relative_path_traversal_rejected(tmp_path: Path) -> None:
    result = _safe_relative_path(tmp_path, "../outside.txt")
    assert result is None


def test_content_hash_deterministic() -> None:
    files = {"a.txt": b"hello", "b.txt": b"world"}
    h1 = _content_hash(files)
    h2 = _content_hash(files)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_content_hash_order_independent() -> None:
    files_a = {"z.txt": b"z", "a.txt": b"a"}
    files_b = {"a.txt": b"a", "z.txt": b"z"}
    assert _content_hash(files_a) == _content_hash(files_b)


def test_content_hash_changes_with_content() -> None:
    h1 = _content_hash({"f.txt": b"content_a"})
    h2 = _content_hash({"f.txt": b"content_b"})
    assert h1 != h2


# ---------------------------------------------------------------------------
# Helpers for integration-style tests
# ---------------------------------------------------------------------------


def _make_repo(repo_id: str = "github:alice/skills") -> RepositoryRecord:
    owner, name = repo_id.split(":")[-1].split("/")
    return RepositoryRecord(
        repository_id=repo_id,
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
        commit_sha="deadbeef",
        selected_for_export=True,
        collected_at="2024-01-01T00:00:00+00:00",
    )


def _make_validated_skill(
    repo_id: str = "github:alice/skills",
    skill_path: str = "skills/pdf",
    commit_sha: str = "deadbeef",
) -> ValidatedSkillCandidate:
    owner, name = repo_id.split(":")[-1].split("/")
    return ValidatedSkillCandidate(
        repository_id=repo_id,
        owner=owner,
        repo=name,
        skill_path=skill_path,
        skill_md_path=f"{skill_path}/SKILL.md",
        commit_sha=commit_sha,
        discovery_sources=["seed"],
        discovery_queries=["q"],
        skill_md_content="---\nname: PDF Skill\ndescription: Processes PDFs\n---\nBody",
        validation_status=ValidationStatus.VALID_STANDARD,
        validation_reason="ok",
        validated_at=datetime.now(UTC),
    )


def _make_config(tmp_path: Path, max_file_mb: float = 5.0) -> MagicMock:
    cfg = MagicMock()
    cfg.output.snapshots_directory = str(tmp_path / "snapshots")
    cfg.github.max_file_size_mb = max_file_mb
    cfg.rate_limits.download_concurrency = 2
    return cfg


# ---------------------------------------------------------------------------
# download_snapshots
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_happy_path(tmp_path: Path) -> None:
    repo = _make_repo()
    skill = _make_validated_skill()
    cfg = _make_config(tmp_path)

    skill_md_bytes = b"---\nname: PDF Skill\ndescription: Processes PDFs\n---\nBody"
    helper_bytes = b"def handle(): pass"

    mock_client = AsyncMock()
    mock_client.get_tree.return_value = [
        {"type": "blob", "path": "skills/pdf/SKILL.md", "size": len(skill_md_bytes)},
        {"type": "blob", "path": "skills/pdf/helper.py", "size": len(helper_bytes)},
    ]
    mock_client.get_raw_content.side_effect = [skill_md_bytes, helper_bytes]

    skill_records, rejected = await download_snapshots([repo], [skill], mock_client, cfg)

    assert len(skill_records) == 1
    assert len(rejected) == 0
    sr = skill_records[0]
    assert isinstance(sr, SkillRecord)
    assert sr.file_count == 2
    assert sr.snapshot_complete is True
    assert sr.content_hash != ""


@pytest.mark.asyncio
async def test_download_binary_file_excluded(tmp_path: Path) -> None:
    repo = _make_repo()
    skill = _make_validated_skill()
    cfg = _make_config(tmp_path)

    skill_md_bytes = b"---\nname: PDF Skill\ndescription: Processes PDFs\n---\nBody"

    mock_client = AsyncMock()
    mock_client.get_tree.return_value = [
        {"type": "blob", "path": "skills/pdf/SKILL.md", "size": 100},
        {"type": "blob", "path": "skills/pdf/icon.png", "size": 200},
    ]
    mock_client.get_raw_content.return_value = skill_md_bytes

    skill_records, rejected = await download_snapshots([repo], [skill], mock_client, cfg)

    assert len(skill_records) == 1
    sr = skill_records[0]
    # PNG is excluded
    assert any(e["reason"] == "binary" for e in sr.excluded_files)
    assert sr.snapshot_complete is False


@pytest.mark.asyncio
async def test_download_oversized_file_excluded(tmp_path: Path) -> None:
    repo = _make_repo()
    skill = _make_validated_skill()
    cfg = _make_config(tmp_path, max_file_mb=0.0001)  # 100 bytes max

    skill_md_bytes = b"---\nname: PDF Skill\ndescription: Processes PDFs\n---\nBody"
    big_file = b"X" * 1000  # exceeds 100 bytes

    mock_client = AsyncMock()
    mock_client.get_tree.return_value = [
        {"type": "blob", "path": "skills/pdf/SKILL.md", "size": len(skill_md_bytes)},
        {"type": "blob", "path": "skills/pdf/big.txt", "size": len(big_file)},
    ]
    mock_client.get_raw_content.side_effect = [skill_md_bytes, big_file]

    skill_records, rejected = await download_snapshots([repo], [skill], mock_client, cfg)

    assert len(skill_records) == 1
    sr = skill_records[0]
    assert any(e["reason"] == "oversized" for e in sr.excluded_files)


@pytest.mark.asyncio
async def test_download_skill_md_failure_produces_rejected(tmp_path: Path) -> None:
    from skill_scanning_crawler.common.exceptions import GitHubClientError

    repo = _make_repo()
    skill = _make_validated_skill()
    cfg = _make_config(tmp_path)

    mock_client = AsyncMock()
    mock_client.get_tree.return_value = [
        {"type": "blob", "path": "skills/pdf/SKILL.md", "size": 100},
    ]
    mock_client.get_raw_content.side_effect = GitHubClientError("Network error")

    skill_records, rejected = await download_snapshots([repo], [skill], mock_client, cfg)

    assert len(skill_records) == 0
    assert len(rejected) == 1


@pytest.mark.asyncio
async def test_download_skips_unselected_repos(tmp_path: Path) -> None:
    repo = _make_repo()
    repo = repo.model_copy(update={"selected_for_export": False})
    skill = _make_validated_skill()
    cfg = _make_config(tmp_path)
    mock_client = AsyncMock()

    skill_records, rejected = await download_snapshots([repo], [skill], mock_client, cfg)

    assert skill_records == []
    assert rejected == []
    mock_client.get_tree.assert_not_called()
