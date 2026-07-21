"""Repository tree scanner: finds SKILL.md files and builds SkillCandidates.

For each RepositoryRecord, fetches the recursive git tree at commit_sha and
produces one SkillCandidate per directory that contains a ``SKILL.md`` file.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from skill_scanning_crawler.common.config import CrawlerConfig
from skill_scanning_crawler.common.exceptions import GitHubClientError
from skill_scanning_crawler.common.models import RepositoryRecord, SkillCandidate
from skill_scanning_crawler.github_client.client import GitHubClient

log = logging.getLogger(__name__)

_SKILL_FILENAME = "SKILL.md"


async def locate_skills(
    repositories: list[RepositoryRecord],
    client: GitHubClient,
    config: CrawlerConfig,
) -> list[SkillCandidate]:
    """Scan each repository's tree and return SkillCandidate objects."""
    sem = asyncio.Semaphore(config.rate_limits.tree_concurrency)

    max_skills = config.github.max_skills_per_repo

    async def _scan_one(repo: RepositoryRecord) -> list[SkillCandidate]:
        async with sem:
            try:
                return await _scan_repo(repo, client, max_skills)
            except Exception as exc:  # noqa: BLE001 — one bad repo must not abort the stage
                log.warning(
                    "Unexpected error scanning tree for %s/%s: %s",
                    repo.owner, repo.name, exc,
                )
                return []

    results = await asyncio.gather(*[_scan_one(r) for r in repositories])

    all_candidates: list[SkillCandidate] = []
    for repo_candidates in results:
        all_candidates.extend(repo_candidates)

    log.info("Tree scan complete: %d skill candidates across %d repos",
             len(all_candidates), len(repositories))
    return all_candidates


async def _scan_repo(
    repo: RepositoryRecord,
    client: GitHubClient,
    max_skills: int = 0,
) -> list[SkillCandidate]:
    try:
        tree = await client.get_tree(repo.owner, repo.name, repo.commit_sha)
    except GitHubClientError as exc:
        log.warning("Cannot fetch tree for %s/%s: %s", repo.owner, repo.name, exc)
        return []

    return _tree_to_candidates(tree, repo, max_skills)


def _tree_to_candidates(
    tree: list[dict[str, Any]],
    repo: RepositoryRecord,
    max_skills: int = 0,
) -> list[SkillCandidate]:
    """Extract SkillCandidates from a flat git tree."""
    now = datetime.now(UTC)
    # Map path → size for all blob entries
    file_sizes: dict[str, int] = {}
    skill_md_paths: list[str] = []

    for entry in tree:
        entry_type = entry.get("type")
        path: str = entry.get("path", "")
        if entry_type == "blob":
            size = entry.get("size") or 0
            file_sizes[path] = int(size)
            if PurePosixPath(path).name == _SKILL_FILENAME:
                skill_md_paths.append(path)

    # Cap per-repo skills for aggregator/collection repos. Keep the shallowest
    # paths (fewest directory segments, then lexicographic) so top-level, most
    # representative skills are retained deterministically.
    if max_skills > 0 and len(skill_md_paths) > max_skills:
        skill_md_paths.sort(key=lambda p: (p.count("/"), p))
        log.info(
            "Repo %s/%s: capping %d SKILL.md files to %d (max_skills_per_repo)",
            repo.owner, repo.name, len(skill_md_paths), max_skills,
        )
        skill_md_paths = skill_md_paths[:max_skills]

    candidates: list[SkillCandidate] = []
    for skill_md_path in skill_md_paths:
        # Skill directory = parent of SKILL.md
        skill_dir = str(PurePosixPath(skill_md_path).parent)

        # Collect sizes for all files under the skill directory
        dir_prefix = "" if skill_dir == "." else skill_dir + "/"
        tree_sizes: dict[str, int] = {
            p: s
            for p, s in file_sizes.items()
            if p == skill_md_path or p.startswith(dir_prefix)
        }

        candidates.append(
            SkillCandidate(
                repository_id=repo.repository_id,
                owner=repo.owner,
                repo=repo.name,
                skill_path=skill_dir,
                skill_md_path=skill_md_path,
                commit_sha=repo.commit_sha,
                discovery_sources=list(repo.discovery_sources),
                discovery_queries=list(repo.discovery_queries),
                tree_file_sizes=tree_sizes,
                located_at=now,
            )
        )

    log.debug(
        "Repo %s/%s: found %d SKILL.md files",
        repo.owner, repo.name, len(candidates),
    )
    return candidates
