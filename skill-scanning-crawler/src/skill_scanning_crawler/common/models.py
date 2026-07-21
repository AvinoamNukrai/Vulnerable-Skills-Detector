"""Data models for the skill-scanning-crawler pipeline.

Exported Pydantic models (written to data/manifests/):
  - RepositoryRecord
  - SkillRecord
  - RejectedCandidateRecord

Internal dataclasses (never written to manifests):
  - CandidateRepository
  - SkillCandidate
  - ValidatedSkillCandidate
  - ExcludedFile
  - SnapshotResult
  - CheckpointEnvelope
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField

from skill_scanning_crawler.common.enums import ValidationStatus

# ---------------------------------------------------------------------------
# Exported Pydantic models (manifest records)
# ---------------------------------------------------------------------------


class RepositoryRecord(BaseModel):
    """GitHub repository with enriched metadata and selection status.

    Written to data/manifests/repositories.jsonl.
    """

    model_config = ConfigDict(extra="forbid")

    repository_id: str
    platform: str
    owner: str
    name: str
    full_name: str
    url: str
    description: str | None
    stars: int
    forks: int
    is_fork: bool
    is_archived: bool
    default_branch: str
    commit_sha: str
    license: str | None = None
    topics: list[str] = PydanticField(default_factory=list)
    repository_size_kb: int | None = None
    discovery_sources: list[str] = PydanticField(default_factory=list)
    discovery_queries: list[str] = PydanticField(default_factory=list)
    skill_count: int = 0
    selected_for_export: bool = False
    collected_at: str = ""


class SkillRecord(BaseModel):
    """One validated, downloaded skill directory.

    Written to data/manifests/skills.jsonl.
    """

    model_config = ConfigDict(extra="forbid")

    skill_id: str
    repository_id: str
    platform: str
    owner: str
    repo: str
    repository_url: str
    skill_path: str
    skill_name: str
    description: str | None = None
    validation_status: ValidationStatus
    commit_sha: str
    content_hash: str
    file_count: int
    total_size_bytes: int
    files: list[str]
    snapshot_path: str
    snapshot_complete: bool
    excluded_files: list[dict[str, str]]
    collected_at: str


class RejectedCandidateRecord(BaseModel):
    """Candidate that was rejected at any pipeline stage.

    Written to data/manifests/rejected_candidates.jsonl.
    Never silently discarded.
    """

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    repository_id: str
    platform: str
    owner: str
    repo: str
    path: str
    rejection_status: ValidationStatus
    rejection_reason: str
    discovery_sources: list[str]
    discovery_queries: list[str] = PydanticField(default_factory=list)
    commit_sha: str | None = None
    collected_at: str = ""


# ---------------------------------------------------------------------------
# Internal dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CandidateRepository:
    """Repository discovered by seed list or GitHub search.

    Deduplication by canonical_id occurs during discovery normalization.
    """

    canonical_id: str
    owner: str
    repo: str
    url: str
    discovery_sources: list[str] = field(default_factory=list)
    discovery_queries: list[str] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SkillCandidate:
    """One potential skill directory found by tree scanning.

    Produced by run_locate_skills. Has no SKILL.md content yet.
    """

    repository_id: str
    owner: str
    repo: str
    skill_path: str
    skill_md_path: str
    commit_sha: str
    discovery_sources: list[str] = field(default_factory=list)
    discovery_queries: list[str] = field(default_factory=list)
    tree_file_sizes: dict[str, int] = field(default_factory=dict)
    located_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ValidatedSkillCandidate:
    """Skill candidate that has been classified by the strict validator.

    Produced by run_validate. Only candidates with validation_status==valid_standard
    proceed to run_snapshot.
    """

    repository_id: str
    owner: str
    repo: str
    skill_path: str
    skill_md_path: str
    commit_sha: str
    discovery_sources: list[str]
    discovery_queries: list[str]
    skill_md_content: str
    validation_status: ValidationStatus
    validation_reason: str
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExcludedFile:
    """A file that was excluded from a snapshot with its reason."""

    path: str
    reason: str  # "binary" | "oversized" | "unsafe_path" | "download_failed"


@dataclass
class SnapshotResult:
    """Intermediate result produced during run_snapshot for one skill.

    Converted to SkillRecord on success, or triggers a RejectedCandidateRecord
    if SKILL.md itself could not be downloaded.
    """

    candidate: ValidatedSkillCandidate
    local_root: Path
    downloaded_files: list[str] = field(default_factory=list)
    excluded_files: list[ExcludedFile] = field(default_factory=list)
    total_size_bytes: int = 0
    content_hash: str = ""
    snapshot_complete: bool = True


@dataclass
class CheckpointEnvelope:
    """Versioned wrapper written around every checkpoint file.

    --resume loads a checkpoint only when checkpoint_version and config_hash
    both match the currently active code and configuration.
    """

    checkpoint_version: str
    run_id: str
    stage: str
    config_hash: str
    record_type: str
    timestamp: str
    record_count: int
    records: list[Any] = field(default_factory=list)

    CURRENT_VERSION: ClassVar[str] = "1"
