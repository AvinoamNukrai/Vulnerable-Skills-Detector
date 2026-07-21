"""Tests for all exported Pydantic models and internal dataclasses."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from skill_scanning_crawler.common.enums import ValidationStatus
from skill_scanning_crawler.common.models import (
    CandidateRepository,
    CheckpointEnvelope,
    ExcludedFile,
    RejectedCandidateRecord,
    RepositoryRecord,
    SkillCandidate,
    SkillRecord,
    SnapshotResult,
    ValidatedSkillCandidate,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"
SCHEMA_PATH = Path(__file__).parent.parent.parent / "config" / "output_schema.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sample_repo_dict() -> dict:
    return json.loads((FIXTURES / "sample_repository_record.json").read_text())


@pytest.fixture(scope="module")
def sample_skill_dict() -> dict:
    return json.loads((FIXTURES / "sample_skill_record.json").read_text())


@pytest.fixture(scope="module")
def sample_rejected_dict() -> dict:
    return json.loads((FIXTURES / "sample_rejected_candidate_record.json").read_text())


# ---------------------------------------------------------------------------
# RepositoryRecord
# ---------------------------------------------------------------------------


def test_repository_record_from_fixture(sample_repo_dict: dict) -> None:
    rec = RepositoryRecord(**sample_repo_dict)
    assert rec.repository_id == "github__octocat__skills-demo"
    assert rec.platform == "github"
    assert rec.stars == 1234
    assert rec.selected_for_export is True


def test_repository_record_missing_required_field(sample_repo_dict: dict) -> None:
    bad = {k: v for k, v in sample_repo_dict.items() if k != "commit_sha"}
    with pytest.raises(ValidationError):
        RepositoryRecord(**bad)


def test_repository_record_extra_field_rejected(sample_repo_dict: dict) -> None:
    bad = {**sample_repo_dict, "unknown_field": "value"}
    with pytest.raises(ValidationError):
        RepositoryRecord(**bad)


def test_repository_record_json_roundtrip(sample_repo_dict: dict) -> None:
    rec = RepositoryRecord(**sample_repo_dict)
    restored = RepositoryRecord(**json.loads(rec.model_dump_json()))
    assert restored == rec


def test_repository_record_schema_valid(sample_repo_dict: dict, schema: dict) -> None:
    record_schema = {"$ref": "#/$defs/RepositoryRecord", **schema}
    jsonschema.validate(instance=sample_repo_dict, schema=record_schema)


# ---------------------------------------------------------------------------
# SkillRecord
# ---------------------------------------------------------------------------


def test_skill_record_from_fixture(sample_skill_dict: dict) -> None:
    rec = SkillRecord(**sample_skill_dict)
    assert rec.skill_id == "github__octocat__skills-demo__skills__pdf-analyzer"
    assert rec.validation_status == ValidationStatus.VALID_STANDARD
    assert rec.snapshot_complete is True
    assert rec.excluded_files == []


def test_skill_record_with_excluded_files() -> None:
    base = json.loads((FIXTURES / "sample_skill_record.json").read_text())
    base["snapshot_complete"] = False
    base["excluded_files"] = [{"path": "large_file.bin", "reason": "binary"}]
    rec = SkillRecord(**base)
    assert rec.snapshot_complete is False
    assert rec.excluded_files[0]["reason"] == "binary"


def test_skill_record_missing_required_field(sample_skill_dict: dict) -> None:
    bad = {k: v for k, v in sample_skill_dict.items() if k != "content_hash"}
    with pytest.raises(ValidationError):
        SkillRecord(**bad)


def test_skill_record_extra_field_rejected(sample_skill_dict: dict) -> None:
    bad = {**sample_skill_dict, "surprise": True}
    with pytest.raises(ValidationError):
        SkillRecord(**bad)


def test_skill_record_json_roundtrip(sample_skill_dict: dict) -> None:
    rec = SkillRecord(**sample_skill_dict)
    restored = SkillRecord(**json.loads(rec.model_dump_json()))
    assert restored == rec


def test_skill_record_schema_valid(sample_skill_dict: dict, schema: dict) -> None:
    record_schema = {"$ref": "#/$defs/SkillRecord", **schema}
    jsonschema.validate(instance=sample_skill_dict, schema=record_schema)


# ---------------------------------------------------------------------------
# RejectedCandidateRecord
# ---------------------------------------------------------------------------


def test_rejected_candidate_from_fixture(sample_rejected_dict: dict) -> None:
    rec = RejectedCandidateRecord(**sample_rejected_dict)
    assert rec.rejection_status == ValidationStatus.DOCUMENTATION_ONLY
    assert rec.commit_sha is not None


def test_rejected_candidate_null_commit_sha(sample_rejected_dict: dict) -> None:
    d = {**sample_rejected_dict, "commit_sha": None}
    rec = RejectedCandidateRecord(**d)
    assert rec.commit_sha is None


def test_rejected_candidate_missing_required_field(sample_rejected_dict: dict) -> None:
    bad = {k: v for k, v in sample_rejected_dict.items() if k != "rejection_reason"}
    with pytest.raises(ValidationError):
        RejectedCandidateRecord(**bad)


def test_rejected_candidate_extra_field_rejected(sample_rejected_dict: dict) -> None:
    bad = {**sample_rejected_dict, "extra": "oops"}
    with pytest.raises(ValidationError):
        RejectedCandidateRecord(**bad)


def test_rejected_candidate_schema_valid(sample_rejected_dict: dict, schema: dict) -> None:
    record_schema = {"$ref": "#/$defs/RejectedCandidateRecord", **schema}
    jsonschema.validate(instance=sample_rejected_dict, schema=record_schema)


# ---------------------------------------------------------------------------
# ValidationStatus enum
# ---------------------------------------------------------------------------


def test_all_validation_statuses_present() -> None:
    expected = {
        "valid_standard",
        "valid_lenient",
        "invalid_missing_skill_md",
        "invalid_missing_frontmatter",
        "invalid_malformed_frontmatter",
        "invalid_missing_name",
        "invalid_missing_description",
        "documentation_only",
        "example_only",
        "too_large",
        "binary_or_unsupported",
        "repository_unavailable",
        "undetermined",
    }
    actual = {status.value for status in ValidationStatus}
    assert actual == expected


# ---------------------------------------------------------------------------
# Internal dataclasses (smoke tests)
# ---------------------------------------------------------------------------


def test_candidate_repository_defaults() -> None:
    c = CandidateRepository(
        canonical_id="github__foo__bar",
        owner="foo",
        repo="bar",
        url="https://github.com/foo/bar",
    )
    assert c.discovery_sources == []
    assert c.discovered_at is not None


def test_skill_candidate_defaults() -> None:
    sc = SkillCandidate(
        repository_id="github__foo__bar",
        owner="foo",
        repo="bar",
        skill_path="skills/my-skill",
        skill_md_path="skills/my-skill/SKILL.md",
        commit_sha="abc123",
    )
    assert sc.tree_file_sizes == {}
    assert sc.located_at is not None


def test_validated_skill_candidate() -> None:
    vsc = ValidatedSkillCandidate(
        repository_id="github__foo__bar",
        owner="foo",
        repo="bar",
        skill_path="skills/my-skill",
        skill_md_path="skills/my-skill/SKILL.md",
        commit_sha="abc123",
        discovery_sources=["seed_list"],
        discovery_queries=[],
        skill_md_content="---\nname: my-skill\ndescription: A skill.\n---\n# My Skill\n",
        validation_status=ValidationStatus.VALID_STANDARD,
        validation_reason="Passed strict validation.",
    )
    assert vsc.validation_status == ValidationStatus.VALID_STANDARD


def test_excluded_file() -> None:
    ef = ExcludedFile(path="large_file.bin", reason="binary")
    assert ef.reason == "binary"


def test_snapshot_result_defaults(tmp_path: Path) -> None:
    vsc = ValidatedSkillCandidate(
        repository_id="github__foo__bar",
        owner="foo",
        repo="bar",
        skill_path="skills/x",
        skill_md_path="skills/x/SKILL.md",
        commit_sha="abc",
        discovery_sources=[],
        discovery_queries=[],
        skill_md_content="",
        validation_status=ValidationStatus.VALID_STANDARD,
        validation_reason="ok",
    )
    sr = SnapshotResult(candidate=vsc, local_root=tmp_path)
    assert sr.snapshot_complete is True
    assert sr.excluded_files == []


def test_checkpoint_envelope() -> None:
    env = CheckpointEnvelope(
        checkpoint_version="1",
        run_id="run-abc",
        stage="discover",
        config_hash="deadbeef",
        record_type="CandidateRepository",
        timestamp="2026-07-16T09:00:00Z",
        record_count=5,
        records=[],
    )
    assert env.checkpoint_version == "1"
    assert env.record_count == 5
