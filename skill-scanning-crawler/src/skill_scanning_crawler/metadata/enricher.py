"""Metadata enrichment: CandidateRepository → RepositoryRecord.

For each candidate repository, fetches the GitHub REST metadata object
and the latest commit SHA on the default branch.

Repositories that cannot be fetched (404, archived-but-excluded, etc.)
are recorded as RejectedCandidateRecord.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from skill_scanning_crawler.common.config import CrawlerConfig
from skill_scanning_crawler.common.enums import Platform, ValidationStatus
from skill_scanning_crawler.common.exceptions import GitHubClientError
from skill_scanning_crawler.common.models import (
    CandidateRepository,
    RejectedCandidateRecord,
    RepositoryRecord,
)
from skill_scanning_crawler.github_client.client import GitHubClient

log = logging.getLogger(__name__)


async def enrich_repositories(
    candidates: list[CandidateRepository],
    client: GitHubClient,
    config: CrawlerConfig,
) -> tuple[list[RepositoryRecord], list[RejectedCandidateRecord]]:
    """Enrich all candidates concurrently, bounded by metadata_concurrency."""
    sem = asyncio.Semaphore(config.rate_limits.metadata_concurrency)
    now_str = datetime.now(UTC).isoformat()

    async def _enrich_one(
        cand: CandidateRepository,
    ) -> RepositoryRecord | RejectedCandidateRecord:
        async with sem:
            try:
                return await _fetch_and_build(cand, client, config, now_str)
            except Exception as exc:  # noqa: BLE001 — one bad repo must not abort the stage
                log.warning(
                    "Unexpected error enriching %s/%s: %s", cand.owner, cand.repo, exc
                )
                return _make_rejected(
                    cand, ValidationStatus.REPOSITORY_UNAVAILABLE,
                    f"unexpected enrichment error: {exc}", now_str,
                )

    results = await asyncio.gather(*[_enrich_one(c) for c in candidates])

    repositories: list[RepositoryRecord] = []
    rejected: list[RejectedCandidateRecord] = []
    for r in results:
        if isinstance(r, RepositoryRecord):
            repositories.append(r)
        else:
            rejected.append(r)

    before = len(repositories)
    repositories = _dedupe_by_resolved_identity(repositories)
    if len(repositories) < before:
        log.info(
            "Alias dedup: %d -> %d repositories (merged redirect/rename aliases)",
            before, len(repositories),
        )

    log.info(
        "Enrichment complete: %d repositories, %d rejected",
        len(repositories), len(rejected),
    )
    return repositories, rejected


def _dedupe_by_resolved_identity(
    repositories: list[RepositoryRecord],
) -> list[RepositoryRecord]:
    """Collapse records that resolved to the same real repo after a redirect.

    Discovery deduplicates on the *discovered* owner/repo (canonical_id), so a
    repo reached via two different aliases (e.g. an old name and its renamed
    target) survives as two records with the same GitHub ``full_name``. Merge
    them on the resolved ``full_name`` (case-insensitive), keeping the first and
    unioning discovery provenance so nothing is lost.
    """
    seen: dict[str, RepositoryRecord] = {}
    for repo in repositories:
        key = repo.full_name.lower()
        existing = seen.get(key)
        if existing is None:
            seen[key] = repo
            continue
        merged_sources = list(
            dict.fromkeys([*existing.discovery_sources, *repo.discovery_sources])
        )
        merged_queries = list(
            dict.fromkeys([*existing.discovery_queries, *repo.discovery_queries])
        )
        seen[key] = existing.model_copy(
            update={
                "discovery_sources": merged_sources,
                "discovery_queries": merged_queries,
            }
        )
    return list(seen.values())


async def _fetch_and_build(
    cand: CandidateRepository,
    client: GitHubClient,
    config: CrawlerConfig,
    collected_at: str,
) -> RepositoryRecord | RejectedCandidateRecord:
    owner, repo = cand.owner, cand.repo
    try:
        meta = await client.get_repository(owner, repo)
    except GitHubClientError as exc:
        log.warning("Cannot fetch metadata for %s/%s: %s", owner, repo, exc)
        return _make_rejected(cand, ValidationStatus.REPOSITORY_UNAVAILABLE, str(exc), collected_at)

    default_branch: str = meta.get("default_branch", "main")
    try:
        sha = await client.get_default_branch_sha(owner, repo, default_branch)
    except GitHubClientError as exc:
        log.warning("Cannot resolve SHA for %s/%s@%s: %s", owner, repo, default_branch, exc)
        return _make_rejected(cand, ValidationStatus.REPOSITORY_UNAVAILABLE, str(exc), collected_at)

    license_info: dict[str, Any] | None = meta.get("license")
    license_name: str | None = license_info.get("spdx_id") if license_info else None

    return RepositoryRecord(
        repository_id=cand.canonical_id,
        platform=Platform.GITHUB,
        owner=owner,
        name=repo,
        full_name=meta.get("full_name", f"{owner}/{repo}"),
        url=meta.get("html_url", cand.url),
        description=meta.get("description"),
        stars=int(meta.get("stargazers_count", 0)),
        forks=int(meta.get("forks_count", 0)),
        is_fork=bool(meta.get("fork", False)),
        is_archived=bool(meta.get("archived", False)),
        default_branch=default_branch,
        commit_sha=sha,
        license=license_name,
        topics=list(meta.get("topics", [])),
        repository_size_kb=meta.get("size"),
        discovery_sources=list(cand.discovery_sources),
        discovery_queries=list(cand.discovery_queries),
        skill_count=0,
        selected_for_export=False,
        collected_at=collected_at,
    )


def _make_rejected(
    cand: CandidateRepository,
    status: ValidationStatus,
    reason: str,
    collected_at: str,
) -> RejectedCandidateRecord:
    return RejectedCandidateRecord(
        candidate_id=f"{cand.canonical_id}:enrich",
        repository_id=cand.canonical_id,
        platform=Platform.GITHUB,
        owner=cand.owner,
        repo=cand.repo,
        path="",
        rejection_status=status,
        rejection_reason=reason,
        discovery_sources=list(cand.discovery_sources),
        discovery_queries=list(cand.discovery_queries),
        collected_at=collected_at,
    )
