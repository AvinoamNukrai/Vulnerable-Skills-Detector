"""GitHub search-based discovery: code search and repository search.

Queries are driven by the config's github_queries (code) and
github_repo_queries (repo search). Each result is normalised into a
CandidateRepository with full provenance.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from skill_scanning_crawler.common.enums import DiscoverySource
from skill_scanning_crawler.common.models import CandidateRepository
from skill_scanning_crawler.discovery.normalizer import (
    make_canonical_id,
    make_canonical_url,
)
from skill_scanning_crawler.github_client.client import GitHubClient

log = logging.getLogger(__name__)

_DEFAULT_CODE_QUERIES = [
    "filename:SKILL.md",
    "SKILL.md in:path name:SKILL.md",
]

_DEFAULT_REPO_QUERIES = [
    "SKILL.md in:readme topic:agent-skills",
    "cursor-skills SKILL.md",
]


async def collect_from_code_search(
    client: GitHubClient,
    queries: list[str] | None = None,
    per_page: int = 100,
    max_pages: int = 5,
) -> list[CandidateRepository]:
    """Run each code-search *query* and extract repository candidates."""
    queries = queries or _DEFAULT_CODE_QUERIES
    now = datetime.now(UTC)
    all_candidates: list[CandidateRepository] = []

    for query in queries:
        log.info("Code search: %r", query)
        try:
            items = await client.search_code(query, per_page=per_page, max_pages=max_pages)
        except Exception as exc:
            log.warning("Code search %r failed: %s", query, exc)
            continue

        for item in items:
            cand = _code_item_to_candidate(item, query, now)
            if cand:
                all_candidates.append(cand)

    log.info("Code search produced %d raw candidates", len(all_candidates))
    return all_candidates


async def collect_from_repo_search(
    client: GitHubClient,
    queries: list[str] | None = None,
    per_page: int = 100,
    max_pages: int = 5,
) -> list[CandidateRepository]:
    """Run each repo-search *query* and extract repository candidates."""
    queries = queries or _DEFAULT_REPO_QUERIES
    now = datetime.now(UTC)
    all_candidates: list[CandidateRepository] = []

    for query in queries:
        log.info("Repo search: %r", query)
        try:
            items = await client.search_repositories(query, per_page=per_page, max_pages=max_pages)
        except Exception as exc:
            log.warning("Repo search %r failed: %s", query, exc)
            continue

        for item in items:
            cand = _repo_item_to_candidate(item, query, now)
            if cand:
                all_candidates.append(cand)

    log.info("Repo search produced %d raw candidates", len(all_candidates))
    return all_candidates


def _code_item_to_candidate(
    item: dict[str, Any],
    query: str,
    now: datetime,
) -> CandidateRepository | None:
    repo_data = item.get("repository", {})
    full_name: str = repo_data.get("full_name", "")
    html_url: str = repo_data.get("html_url", "")
    if not full_name or "/" not in full_name:
        return None
    owner, repo = full_name.split("/", 1)
    cid = make_canonical_id(owner, repo)
    return CandidateRepository(
        canonical_id=cid,
        owner=owner,
        repo=repo,
        url=html_url or make_canonical_url(owner, repo),
        discovery_sources=[DiscoverySource.GITHUB_CODE_SEARCH],
        discovery_queries=[query],
        discovered_at=now,
    )


def _repo_item_to_candidate(
    item: dict[str, Any],
    query: str,
    now: datetime,
) -> CandidateRepository | None:
    full_name: str = item.get("full_name", "")
    html_url: str = item.get("html_url", "")
    if not full_name or "/" not in full_name:
        return None
    owner, repo = full_name.split("/", 1)
    cid = make_canonical_id(owner, repo)
    return CandidateRepository(
        canonical_id=cid,
        owner=owner,
        repo=repo,
        url=html_url or make_canonical_url(owner, repo),
        discovery_sources=[DiscoverySource.GITHUB_REPO_SEARCH],
        discovery_queries=[query],
        discovered_at=now,
    )
