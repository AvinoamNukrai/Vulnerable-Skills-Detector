"""Repository ranking: select top-N by stars from qualifying repositories.

Qualifying criteria (all must hold):
  - at least one ValidatedSkillCandidate with status==valid_standard
  - not a fork (unless config.include_forks is True)
  - not archived (unless config.include_archived is True)

Top-N is selected by descending star count.  Shortfall (fewer than top_n
qualifying repositories) is logged as a warning — the output is never padded.
"""

from __future__ import annotations

import logging

from skill_scanning_crawler.common.config import CrawlerConfig
from skill_scanning_crawler.common.enums import ValidationStatus
from skill_scanning_crawler.common.models import RepositoryRecord, ValidatedSkillCandidate

log = logging.getLogger(__name__)


def rank_repositories(
    repositories: list[RepositoryRecord],
    validated_skills: list[ValidatedSkillCandidate],
    config: CrawlerConfig,
) -> list[RepositoryRecord]:
    """Return a copy of *repositories* with ``selected_for_export`` set.

    Only the top-N qualifying repositories are selected.
    All repositories are returned (selected and unselected) so that the
    export stage can still write the full ``repositories.jsonl``.
    """
    top_n = config.github.top_n_repositories

    valid_repo_ids: set[str] = {
        sc.repository_id
        for sc in validated_skills
        if sc.validation_status == ValidationStatus.VALID_STANDARD
    }

    qualifying: list[RepositoryRecord] = []
    for repo in repositories:
        if repo.repository_id not in valid_repo_ids:
            continue
        if repo.is_fork and not config.github.include_forks:
            log.debug("Excluding fork: %s/%s", repo.owner, repo.name)
            continue
        if repo.is_archived and not config.github.include_archived:
            log.debug("Excluding archived: %s/%s", repo.owner, repo.name)
            continue
        qualifying.append(repo)

    qualifying.sort(key=lambda r: r.stars, reverse=True)
    selected = qualifying[:top_n]

    if len(qualifying) < top_n:
        log.warning(
            "Shortfall: only %d qualifying repositories (top_n=%d)",
            len(qualifying), top_n,
        )

    selected_ids = {r.repository_id for r in selected}
    updated: list[RepositoryRecord] = []
    for repo in repositories:
        if repo.repository_id in selected_ids:
            updated.append(repo.model_copy(update={"selected_for_export": True}))
        else:
            updated.append(repo)

    log.info(
        "Ranking complete: %d qualifying, %d selected (top_n=%d)",
        len(qualifying), len(selected), top_n,
    )
    return updated
