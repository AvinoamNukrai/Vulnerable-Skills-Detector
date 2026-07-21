"""JSON report generator.

Produces:
  data/reports/discovery_summary.json   — high-level run metadata
  data/reports/dataset_statistics.json  — counts, distributions, quality metrics
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from skill_scanning_crawler.common.config import CrawlerConfig
from skill_scanning_crawler.common.models import (
    RejectedCandidateRecord,
    RepositoryRecord,
    SkillRecord,
)

log = logging.getLogger(__name__)


def write_reports(
    repositories: list[RepositoryRecord],
    skills: list[SkillRecord],
    rejected: list[RejectedCandidateRecord],
    config: CrawlerConfig,
    run_id: str,
) -> dict[str, Path]:
    """Write discovery_summary.json and dataset_statistics.json."""
    reports_dir = Path(config.output.reports_directory)
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary = _build_summary(repositories, skills, rejected, config, run_id)
    stats = _build_statistics(repositories, skills, rejected)

    summary_path = reports_dir / "discovery_summary.json"
    stats_path = reports_dir / "dataset_statistics.json"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    log.info("Reports written to %s", reports_dir)
    return {"discovery_summary": summary_path, "dataset_statistics": stats_path}


def _build_summary(
    repositories: list[RepositoryRecord],
    skills: list[SkillRecord],
    rejected: list[RejectedCandidateRecord],
    config: CrawlerConfig,
    run_id: str,
) -> dict[str, Any]:
    selected = [r for r in repositories if r.selected_for_export]
    return {
        "run_id": run_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "config": {
            "top_n_repositories": config.github.top_n_repositories,
            "include_forks": config.github.include_forks,
            "include_archived": config.github.include_archived,
            "strict_validation": config.validation.strict_validation,
        },
        "discovery": {
            "total_candidates": len(repositories) + len(rejected),
            "repositories_enriched": len(repositories),
            "repositories_selected": len(selected),
            "skills_validated": len(skills),
            "total_rejected": len(rejected),
        },
    }


def _build_statistics(
    repositories: list[RepositoryRecord],
    skills: list[SkillRecord],
    rejected: list[RejectedCandidateRecord],
) -> dict[str, Any]:
    selected = [r for r in repositories if r.selected_for_export]
    star_counts = [r.stars for r in selected]
    rejection_reasons = Counter(r.rejection_reason for r in rejected)
    incomplete_snapshots = sum(1 for s in skills if not s.snapshot_complete)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "repositories": {
            "total": len(repositories),
            "selected": len(selected),
            "forks": sum(1 for r in repositories if r.is_fork),
            "archived": sum(1 for r in repositories if r.is_archived),
        },
        "skills": {
            "total": len(skills),
            "complete_snapshots": len(skills) - incomplete_snapshots,
            "incomplete_snapshots": incomplete_snapshots,
            "total_files": sum(s.file_count for s in skills),
            "total_size_bytes": sum(s.total_size_bytes for s in skills),
        },
        "rejected": {
            "total": len(rejected),
            "by_reason": dict(rejection_reasons.most_common()),
        },
        "stars_distribution": {
            "min": min(star_counts, default=0),
            "max": max(star_counts, default=0),
            "mean": (sum(star_counts) / len(star_counts)) if star_counts else 0,
        },
    }
