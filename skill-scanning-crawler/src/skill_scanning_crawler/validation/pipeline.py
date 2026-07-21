"""Validation pipeline: SkillCandidate → ValidatedSkillCandidate | rejected.

Fetches SKILL.md content from GitHub, then applies the pure-logic validator.
Never creates SkillRecord objects (those are created after snapshotting).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from skill_scanning_crawler.common.config import CrawlerConfig
from skill_scanning_crawler.common.enums import Platform, ValidationStatus
from skill_scanning_crawler.common.exceptions import GitHubClientError
from skill_scanning_crawler.common.models import (
    RejectedCandidateRecord,
    SkillCandidate,
    ValidatedSkillCandidate,
)
from skill_scanning_crawler.github_client.client import GitHubClient
from skill_scanning_crawler.validation.validator import classify_skill

log = logging.getLogger(__name__)


async def validate_candidates(
    candidates: list[SkillCandidate],
    client: GitHubClient,
    config: CrawlerConfig,
) -> tuple[list[ValidatedSkillCandidate], list[RejectedCandidateRecord]]:
    """Validate each SkillCandidate, fetching its SKILL.md content."""
    sem = asyncio.Semaphore(config.rate_limits.metadata_concurrency)

    async def _validate_one(
        cand: SkillCandidate,
    ) -> ValidatedSkillCandidate | RejectedCandidateRecord:
        async with sem:
            try:
                return await _fetch_and_classify(cand, client, config)
            except Exception as exc:  # noqa: BLE001 — one bad candidate must not abort the stage
                log.warning(
                    "Unexpected error validating %s/%s %s: %s",
                    cand.owner, cand.repo, cand.skill_path, exc,
                )
                return _make_rejected(
                    cand, ValidationStatus.REPOSITORY_UNAVAILABLE,
                    f"unexpected validation error: {exc}",
                    datetime.now(UTC).isoformat(),
                )

    results = await asyncio.gather(*[_validate_one(c) for c in candidates])

    validated: list[ValidatedSkillCandidate] = []
    rejected: list[RejectedCandidateRecord] = []
    for r in results:
        if isinstance(r, ValidatedSkillCandidate):
            validated.append(r)
        else:
            rejected.append(r)

    log.info(
        "Validation complete: %d validated, %d rejected",
        len(validated), len(rejected),
    )
    return validated, rejected


async def _fetch_and_classify(
    cand: SkillCandidate,
    client: GitHubClient,
    config: CrawlerConfig,
) -> ValidatedSkillCandidate | RejectedCandidateRecord:
    collected_at = datetime.now(UTC).isoformat()
    try:
        content = await client.get_file_content(
            cand.owner, cand.repo, cand.skill_md_path, cand.commit_sha
        )
    except GitHubClientError as exc:
        log.warning(
            "Cannot fetch SKILL.md for %s/%s %s: %s",
            cand.owner, cand.repo, cand.skill_md_path, exc,
        )
        return _make_rejected(
            cand, ValidationStatus.REPOSITORY_UNAVAILABLE,
            f"SKILL.md fetch failed: {exc}", collected_at,
        )

    status, reason = classify_skill(
        content,
        cand.skill_path,
        cand.tree_file_sizes,
        max_skill_directory_size_mb=getattr(config.github, "max_repository_size_mb", 100.0),
        max_file_size_mb=config.github.max_file_size_mb,
    )

    if status == ValidationStatus.VALID_STANDARD or (
        status == ValidationStatus.VALID_LENIENT
        and config.validation.include_lenient_in_export
    ):
        return ValidatedSkillCandidate(
            repository_id=cand.repository_id,
            owner=cand.owner,
            repo=cand.repo,
            skill_path=cand.skill_path,
            skill_md_path=cand.skill_md_path,
            commit_sha=cand.commit_sha,
            discovery_sources=list(cand.discovery_sources),
            discovery_queries=list(cand.discovery_queries),
            skill_md_content=content,
            validation_status=status,
            validation_reason=reason,
            validated_at=datetime.now(UTC),
        )

    return _make_rejected(cand, status, reason, collected_at)


def _make_rejected(
    cand: SkillCandidate,
    status: ValidationStatus,
    reason: str,
    collected_at: str,
) -> RejectedCandidateRecord:
    return RejectedCandidateRecord(
        candidate_id=f"{cand.repository_id}:{cand.skill_path}",
        repository_id=cand.repository_id,
        platform=Platform.GITHUB,
        owner=cand.owner,
        repo=cand.repo,
        path=cand.skill_path,
        rejection_status=status,
        rejection_reason=reason,
        discovery_sources=list(cand.discovery_sources),
        discovery_queries=list(cand.discovery_queries),
        commit_sha=cand.commit_sha,
        collected_at=collected_at,
    )
