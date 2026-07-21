"""Tests for JSONL manifest writer and report generator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from skill_scanning_crawler.common.enums import ValidationStatus
from skill_scanning_crawler.common.models import (
    RejectedCandidateRecord,
    RepositoryRecord,
    SkillRecord,
)
from skill_scanning_crawler.export.reports import write_reports
from skill_scanning_crawler.export.writer import write_manifests


def _make_config(tmp_path: Path) -> MagicMock:
    cfg = MagicMock()
    cfg.output.manifests_directory = str(tmp_path / "manifests")
    cfg.output.reports_directory = str(tmp_path / "reports")
    cfg.output.deterministic_ordering = True
    cfg.github.top_n_repositories = 50
    cfg.github.include_forks = False
    cfg.github.include_archived = False
    cfg.validation.strict_validation = True
    return cfg


def _make_repo(repo_id: str = "github:alice/r", stars: int = 10) -> RepositoryRecord:
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
        is_fork=False,
        is_archived=False,
        default_branch="main",
        commit_sha="abc",
        selected_for_export=True,
        collected_at="2024-01-01T00:00:00+00:00",
    )


def _make_skill(skill_id: str = "github:alice/r:skills/pdf") -> SkillRecord:
    return SkillRecord(
        skill_id=skill_id,
        repository_id="github:alice/r",
        platform="github",
        owner="alice",
        repo="r",
        repository_url="https://github.com/alice/r",
        skill_path="skills/pdf",
        skill_name="PDF Skill",
        description="Handles PDFs",
        validation_status=ValidationStatus.VALID_STANDARD,
        commit_sha="abc",
        content_hash="0" * 64,
        file_count=2,
        total_size_bytes=1024,
        files=["SKILL.md", "handler.py"],
        snapshot_path="/snapshots/alice/r/skills-pdf/abc12345",
        snapshot_complete=True,
        excluded_files=[],
        collected_at="2024-01-01T00:00:00+00:00",
    )


def _make_rejected(candidate_id: str = "github:alice/r:docs:validate") -> RejectedCandidateRecord:
    return RejectedCandidateRecord(
        candidate_id=candidate_id,
        repository_id="github:alice/r",
        platform="github",
        owner="alice",
        repo="r",
        path="docs",
        rejection_status=ValidationStatus.DOCUMENTATION_ONLY,
        rejection_reason="Path contains 'docs'",
        discovery_sources=["seed"],
    )


# ---------------------------------------------------------------------------
# write_manifests
# ---------------------------------------------------------------------------


def test_write_manifests_creates_three_files(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    write_manifests([_make_repo()], [_make_skill()], [_make_rejected()], cfg)
    manifests = tmp_path / "manifests"
    assert (manifests / "repositories.jsonl").exists()
    assert (manifests / "skills.jsonl").exists()
    assert (manifests / "rejected_candidates.jsonl").exists()


def test_write_manifests_valid_jsonl(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    write_manifests([_make_repo()], [_make_skill()], [], cfg)
    repos_path = tmp_path / "manifests" / "repositories.jsonl"
    lines = repos_path.read_text().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["repository_id"] == "github:alice/r"


def test_write_manifests_deterministic_ordering(tmp_path: Path) -> None:
    repos = [_make_repo(f"github:z/r{i}", stars=i) for i in range(5)]
    cfg = _make_config(tmp_path)
    write_manifests(repos, [], [], cfg)
    lines = (tmp_path / "manifests" / "repositories.jsonl").read_text().splitlines()
    ids = [json.loads(line)["repository_id"] for line in lines]
    assert ids == sorted(ids)


def test_write_manifests_empty_lists(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    write_manifests([], [], [], cfg)
    for name in ("repositories.jsonl", "skills.jsonl", "rejected_candidates.jsonl"):
        assert (tmp_path / "manifests" / name).read_text() == ""


def test_write_manifests_populates_skill_count(tmp_path: Path) -> None:
    """Regression: skill_count must reflect the exported skills, not the 0 placeholder."""
    cfg = _make_config(tmp_path)
    repo_with = _make_repo("github:alice/r")          # two skills below map to this repo
    repo_without = _make_repo("github:zzz/none")      # no skills
    skills = [_make_skill("github:alice/r:s1"), _make_skill("github:alice/r:s2")]
    write_manifests([repo_with, repo_without], skills, [], cfg)

    lines = (tmp_path / "manifests" / "repositories.jsonl").read_text().splitlines()
    counts = {json.loads(x)["repository_id"]: json.loads(x)["skill_count"] for x in lines}
    assert counts["github:alice/r"] == 2
    assert counts["github:zzz/none"] == 0


# ---------------------------------------------------------------------------
# write_reports
# ---------------------------------------------------------------------------


def test_write_reports_creates_files(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    write_reports([_make_repo()], [_make_skill()], [_make_rejected()], cfg, run_id="run-123")
    reports = tmp_path / "reports"
    assert (reports / "discovery_summary.json").exists()
    assert (reports / "dataset_statistics.json").exists()


def test_write_reports_summary_has_run_id(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    write_reports([], [], [], cfg, run_id="my-run-id")
    summary = json.loads((tmp_path / "reports" / "discovery_summary.json").read_text())
    assert summary["run_id"] == "my-run-id"


def test_write_reports_statistics_counts(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    repos = [_make_repo("github:alice/r1", stars=100), _make_repo("github:bob/r2", stars=50)]
    skills = [_make_skill("github:alice/r1:s"), _make_skill("github:bob/r2:s")]
    write_reports(repos, skills, [_make_rejected()], cfg, run_id="r")
    stats = json.loads((tmp_path / "reports" / "dataset_statistics.json").read_text())
    assert stats["repositories"]["total"] == 2
    assert stats["skills"]["total"] == 2
    assert stats["rejected"]["total"] == 1
