"""Skill-directory snapshot downloader.

For each ValidatedSkillCandidate belonging to a selected repository:
  1. Resolve all files in the skill directory from the cached tree.
  2. For each file:
       - Reject path traversal (``..`` segments or outside root).
       - Enforce per-file size limit from config.
       - Detect binary content and record/exclude rather than silently omit.
       - Download file bytes.
  3. Compute a stable SHA-256 content hash (sorted relative paths + SHA-256 of bytes).
  4. Build a SnapshotResult, which is then converted to a SkillRecord.

SKILL.md itself must be downloadable; if it fails, the whole skill is rejected.
Other per-file failures reduce ``snapshot_complete`` to False but do not reject.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from skill_scanning_crawler.common.config import CrawlerConfig
from skill_scanning_crawler.common.enums import Platform, ValidationStatus
from skill_scanning_crawler.common.exceptions import GitHubClientError
from skill_scanning_crawler.common.models import (
    ExcludedFile,
    RejectedCandidateRecord,
    RepositoryRecord,
    SkillRecord,
    ValidatedSkillCandidate,
)
from skill_scanning_crawler.github_client.client import GitHubClient

log = logging.getLogger(__name__)

_BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pyc", ".pyo",
})

# Heuristic: if >30% of first 512 bytes are outside printable ASCII
_BINARY_RATIO = 0.30
_BINARY_SAMPLE = 512


def _is_binary_path(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in _BINARY_EXTENSIONS


def _is_binary_bytes(data: bytes) -> bool:
    sample = data[:_BINARY_SAMPLE]
    if not sample:
        return False
    non_printable = sum(1 for b in sample if b < 9 or (13 < b < 32) or b == 127)
    return non_printable / len(sample) > _BINARY_RATIO


def _safe_relative_path(base_root: Path, raw_path: str) -> Path | None:
    """Resolve *raw_path* relative to *base_root*, rejecting traversal."""
    try:
        resolved = (base_root / raw_path).resolve()
        resolved.relative_to(base_root.resolve())
        return base_root / raw_path
    except (ValueError, OSError):
        return None


def _content_hash(files: dict[str, bytes]) -> str:
    """Deterministic SHA-256 over sorted (relative_path, file_sha256) pairs."""
    h = hashlib.sha256()
    for rel_path in sorted(files.keys()):
        file_hash = hashlib.sha256(files[rel_path]).hexdigest()
        h.update(f"{rel_path}\x00{file_hash}\n".encode())
    return h.hexdigest()


async def download_snapshots(
    selected_repositories: list[RepositoryRecord],
    validated_skills: list[ValidatedSkillCandidate],
    client: GitHubClient,
    config: CrawlerConfig,
) -> tuple[list[SkillRecord], list[RejectedCandidateRecord]]:
    """Download all valid skills for selected repositories."""
    selected_ids = {r.repository_id for r in selected_repositories if r.selected_for_export}
    skills_to_download = [s for s in validated_skills if s.repository_id in selected_ids]

    sem = asyncio.Semaphore(config.rate_limits.download_concurrency)
    snapshots_dir = Path(config.output.snapshots_directory)
    max_file_mb = config.github.max_file_size_mb
    collected_at = datetime.now(UTC).isoformat()

    async def _download_one(
        skill: ValidatedSkillCandidate,
        repo_record: RepositoryRecord,
    ) -> SkillRecord | RejectedCandidateRecord:
        async with sem:
            try:
                return await _snapshot_skill(
                    skill, repo_record, client, snapshots_dir,
                    max_file_mb, collected_at,
                )
            except Exception as exc:  # noqa: BLE001 — one bad skill must not abort the stage
                log.warning(
                    "Unexpected error snapshotting %s/%s %s: %s",
                    skill.owner, skill.repo, skill.skill_path, exc,
                )
                return _make_rejected_skill(
                    skill, ValidationStatus.REPOSITORY_UNAVAILABLE,
                    f"unexpected snapshot error: {exc}", collected_at,
                )

    repo_map = {r.repository_id: r for r in selected_repositories}

    tasks = [
        _download_one(skill, repo_map[skill.repository_id])
        for skill in skills_to_download
        if skill.repository_id in repo_map
    ]
    if not tasks:
        return [], []

    results = await asyncio.gather(*tasks)

    skill_records: list[SkillRecord] = []
    rejected: list[RejectedCandidateRecord] = []
    for r in results:
        if isinstance(r, SkillRecord):
            skill_records.append(r)
        else:
            rejected.append(r)

    log.info(
        "Snapshot complete: %d skill records, %d rejected",
        len(skill_records), len(rejected),
    )
    return skill_records, rejected


async def _snapshot_skill(
    skill: ValidatedSkillCandidate,
    repo: RepositoryRecord,
    client: GitHubClient,
    snapshots_dir: Path,
    max_file_mb: float,
    collected_at: str,
) -> SkillRecord | RejectedCandidateRecord:
    owner, repo_name = skill.owner, skill.repo
    skill_path = skill.skill_path
    commit_sha = skill.commit_sha

    # Local snapshot root: snapshots/<owner>/<repo>/<safe_skill_path>/<sha[:8]>
    safe_skill_dir = re.sub(r"[^\w/.\-]", "_", skill_path) if skill_path != "." else "_root"
    local_root = snapshots_dir / owner / repo_name / safe_skill_dir / commit_sha[:8]
    local_root.mkdir(parents=True, exist_ok=True)

    # Re-fetch the tree (already cached from the locate stage) to get the
    # complete list of files under this skill directory.
    try:
        tree = await client.get_tree(owner, repo_name, commit_sha)
    except GitHubClientError as exc:
        log.warning("Cannot fetch tree for snapshot %s/%s: %s", owner, repo_name, exc)
        return _make_rejected_skill(skill, ValidationStatus.REPOSITORY_UNAVAILABLE,
                                    f"tree fetch failed: {exc}", collected_at)

    skill_dir_prefix = "" if skill_path == "." else skill_path + "/"

    files_in_dir: list[str] = []
    for entry in tree:
        if entry.get("type") != "blob":
            continue
        p: str = entry.get("path", "")
        if p == skill.skill_md_path or p.startswith(skill_dir_prefix):
            files_in_dir.append(p)

    # Download each file
    downloaded_bytes: dict[str, bytes] = {}
    excluded: list[ExcludedFile] = []
    skill_md_ok = False

    max_bytes = int(max_file_mb * 1024 * 1024)

    for file_path in sorted(files_in_dir):
        # Derive relative path within the skill directory
        if skill_path == "." or skill_path == "":
            rel = file_path
        else:
            rel = file_path[len(skill_dir_prefix):]

        # Path safety
        safe_local = _safe_relative_path(local_root, rel)
        if safe_local is None:
            log.warning("Unsafe path rejected: %s in %s/%s", file_path, owner, repo_name)
            excluded.append(ExcludedFile(path=rel, reason="unsafe_path"))
            continue

        # Binary extension check (pre-download)
        if _is_binary_path(file_path):
            excluded.append(ExcludedFile(path=rel, reason="binary"))
            if file_path == skill.skill_md_path:
                return _make_rejected_skill(
                    skill, ValidationStatus.BINARY_OR_UNSUPPORTED,
                    "SKILL.md is binary", collected_at,
                )
            continue

        # Download
        try:
            raw_bytes = await client.get_raw_content(owner, repo_name, file_path, commit_sha)
        except GitHubClientError as exc:
            log.warning("Download failed %s/%s %s: %s", owner, repo_name, file_path, exc)
            if file_path == skill.skill_md_path:
                return _make_rejected_skill(
                    skill, ValidationStatus.REPOSITORY_UNAVAILABLE,
                    f"SKILL.md download failed: {exc}", collected_at,
                )
            excluded.append(ExcludedFile(path=rel, reason="download_failed"))
            continue

        # Binary content check (post-download)
        if _is_binary_bytes(raw_bytes):
            excluded.append(ExcludedFile(path=rel, reason="binary"))
            if file_path == skill.skill_md_path:
                return _make_rejected_skill(
                    skill, ValidationStatus.BINARY_OR_UNSUPPORTED,
                    "SKILL.md is binary", collected_at,
                )
            continue

        # File size check
        if len(raw_bytes) > max_bytes:
            excluded.append(ExcludedFile(path=rel, reason="oversized"))
            if file_path == skill.skill_md_path:
                return _make_rejected_skill(
                    skill, ValidationStatus.TOO_LARGE,
                    f"SKILL.md exceeds {max_file_mb} MB", collected_at,
                )
            continue

        # Write to disk
        safe_local.parent.mkdir(parents=True, exist_ok=True)
        safe_local.write_bytes(raw_bytes)
        downloaded_bytes[rel] = raw_bytes
        if file_path == skill.skill_md_path:
            skill_md_ok = True

    if not skill_md_ok:
        return _make_rejected_skill(
            skill, ValidationStatus.REPOSITORY_UNAVAILABLE,
            "SKILL.md could not be downloaded", collected_at,
        )

    total_size = sum(len(b) for b in downloaded_bytes.values())
    hash_val = _content_hash(downloaded_bytes)
    snapshot_complete = len(excluded) == 0

    # Parse skill name/description from already-validated content
    from skill_scanning_crawler.validation.frontmatter import parse_frontmatter  # noqa: PLC0415
    fm = parse_frontmatter(skill.skill_md_content) or {}
    skill_name: str = str(fm.get("name", skill_path or repo_name))
    description: str | None = str(fm.get("description")) if fm.get("description") else None

    skill_id = f"{skill.repository_id}:{skill_path}"

    return SkillRecord(
        skill_id=skill_id,
        repository_id=skill.repository_id,
        platform=Platform.GITHUB,
        owner=owner,
        repo=repo_name,
        repository_url=repo.url,
        skill_path=skill_path,
        skill_name=skill_name,
        description=description,
        validation_status=skill.validation_status,
        commit_sha=commit_sha,
        content_hash=hash_val,
        file_count=len(downloaded_bytes),
        total_size_bytes=total_size,
        files=sorted(downloaded_bytes.keys()),
        snapshot_path=str(local_root),
        snapshot_complete=snapshot_complete,
        excluded_files=[{"path": e.path, "reason": e.reason} for e in excluded],
        collected_at=collected_at,
    )


def _make_rejected_skill(
    skill: ValidatedSkillCandidate,
    status: ValidationStatus,
    reason: str,
    collected_at: str,
) -> RejectedCandidateRecord:
    return RejectedCandidateRecord(
        candidate_id=f"{skill.repository_id}:{skill.skill_path}:snapshot",
        repository_id=skill.repository_id,
        platform=Platform.GITHUB,
        owner=skill.owner,
        repo=skill.repo,
        path=skill.skill_path,
        rejection_status=status,
        rejection_reason=reason,
        discovery_sources=list(skill.discovery_sources),
        discovery_queries=list(skill.discovery_queries),
        commit_sha=skill.commit_sha,
        collected_at=collected_at,
    )
