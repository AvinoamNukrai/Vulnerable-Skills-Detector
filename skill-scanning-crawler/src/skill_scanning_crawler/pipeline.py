"""Top-level Pipeline class: one real async method per stage.

Each stage:
  1. If resume=True, tries to load its own output checkpoint first.
  2. Otherwise loads the required previous-stage checkpoint (auto-wired).
  3. Executes its logic.
  4. Saves its own output checkpoint (and a separate rejected checkpoint).

This makes every stage command usable standalone:
  python -m skill_scanning_crawler enrich --config ...
  → automatically loads 'discover' checkpoint, enriches, saves 'enrich' checkpoint.
"""

from __future__ import annotations

import dataclasses
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from skill_scanning_crawler.common.checkpoints import load_checkpoint, save_checkpoint
from skill_scanning_crawler.common.config import CrawlerConfig
from skill_scanning_crawler.common.exceptions import CheckpointError, PipelineError
from skill_scanning_crawler.common.models import (
    CandidateRepository,
    RejectedCandidateRecord,
    RepositoryRecord,
    SkillCandidate,
    SkillRecord,
    ValidatedSkillCandidate,
)
from skill_scanning_crawler.discovery.normalizer import deduplicate
from skill_scanning_crawler.discovery.search_collector import (
    collect_from_code_search,
    collect_from_repo_search,
)
from skill_scanning_crawler.discovery.seed_collector import fetch_seed_list
from skill_scanning_crawler.download.snapshot import download_snapshots
from skill_scanning_crawler.export.reports import write_reports
from skill_scanning_crawler.export.writer import write_manifests
from skill_scanning_crawler.github_client.cache import GitHubCache
from skill_scanning_crawler.github_client.client import GitHubClient
from skill_scanning_crawler.locator.tree_scanner import locate_skills
from skill_scanning_crawler.metadata.enricher import enrich_repositories
from skill_scanning_crawler.ranking.ranker import rank_repositories
from skill_scanning_crawler.validation.pipeline import validate_candidates

log = logging.getLogger(__name__)

_DEFAULT_QUERIES_PATH = Path("config/github_queries.yaml")


def _load_github_queries(
    queries_path: Path = _DEFAULT_QUERIES_PATH,
) -> tuple[list[str], list[str]]:
    """Load code-search and repo-search query strings from YAML.

    Falls back to empty lists (caller uses built-in defaults) when the
    file is absent or has no relevant sections.
    """
    if not queries_path.exists():
        log.debug("Query file not found at %s; using built-in defaults", queries_path)
        return [], []
    try:
        raw: Any = yaml.safe_load(queries_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        log.warning("Cannot parse %s: %s; using built-in defaults", queries_path, exc)
        return [], []

    if not isinstance(raw, dict):
        return [], []

    code_queries = [
        str(item["query"])
        for item in raw.get("code_search_queries", [])
        if isinstance(item, dict) and "query" in item
    ]
    repo_queries = [
        str(item["query"])
        for item in raw.get("repository_search_queries", [])
        if isinstance(item, dict) and "query" in item
    ]
    log.info(
        "Loaded %d code-search and %d repo-search queries from %s",
        len(code_queries), len(repo_queries), queries_path,
    )
    return code_queries, repo_queries


def _parse_dt(value: str | datetime) -> datetime:
    """Convert ISO string → datetime, pass through if already datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _deserialize_candidate_repos(records: list[Any]) -> list[CandidateRepository]:
    result = []
    for r in records:
        d: dict[str, Any] = dict(r)
        d["discovered_at"] = _parse_dt(d.get("discovered_at", datetime.now(UTC).isoformat()))
        result.append(CandidateRepository(**d))
    return result


def _deserialize_skill_candidates(records: list[Any]) -> list[SkillCandidate]:
    result = []
    for r in records:
        d: dict[str, Any] = dict(r)
        d["located_at"] = _parse_dt(d.get("located_at", datetime.now(UTC).isoformat()))
        result.append(SkillCandidate(**d))
    return result


def _deserialize_validated_skills(records: list[Any]) -> list[ValidatedSkillCandidate]:
    result = []
    for r in records:
        d: dict[str, Any] = dict(r)
        d["validated_at"] = _parse_dt(d.get("validated_at", datetime.now(UTC).isoformat()))
        result.append(ValidatedSkillCandidate(**d))
    return result


class Pipeline:
    """Orchestrates the 7-stage crawler pipeline."""

    def __init__(
        self,
        config: CrawlerConfig,
        run_id: str | None = None,
        resume: bool = False,
    ) -> None:
        self.config = config
        self.run_id: str = run_id if run_id is not None else str(uuid.uuid4())
        self.resume = resume
        self._config_hash = config.compute_hash()

    # ------------------------------------------------------------------
    # Stage 1 — Discover
    # ------------------------------------------------------------------

    async def run_discover(self) -> list[CandidateRepository]:
        """Collect CandidateRepository objects from seed lists and GitHub search."""
        stage = "discover"
        if self.resume:
            cached = self._load_checkpoint(stage)
            if cached is not None:
                log.info("Resuming discover from checkpoint (%d records)", len(cached))
                return _deserialize_candidate_repos(cached)

        cache = self._open_cache()
        all_candidates: list[CandidateRepository] = []

        for seed_cfg in self.config.seed_lists:
            try:
                candidates = await fetch_seed_list(seed_cfg, cache=cache)
                all_candidates.extend(candidates)
            except Exception as exc:  # noqa: BLE001
                log.warning("Seed list %r failed: %s", seed_cfg.name, exc)

        # Load queries from config/github_queries.yaml
        code_queries, repo_queries = _load_github_queries()

        async with GitHubClient.from_config(self.config, cache) as client:
            if client._token:  # noqa: SLF001
                code_results = await collect_from_code_search(
                    client,
                    queries=code_queries or None,   # None → use built-in defaults
                )
                all_candidates.extend(code_results)
                repo_results = await collect_from_repo_search(
                    client,
                    queries=repo_queries or None,
                )
                all_candidates.extend(repo_results)
            else:
                log.warning(
                    "GITHUB_TOKEN not set; skipping GitHub search (seed lists only)"
                )

        deduplicated = deduplicate(all_candidates)
        log.info(
            "Discovery: %d raw → %d after deduplication",
            len(all_candidates), len(deduplicated),
        )
        self._save_checkpoint(stage, "CandidateRepository",
                              [dataclasses.asdict(c) for c in deduplicated])
        return deduplicated

    # ------------------------------------------------------------------
    # Stage 2 — Enrich
    # ------------------------------------------------------------------

    async def run_enrich(
        self,
        candidates: list[CandidateRepository] | None = None,
    ) -> tuple[list[RepositoryRecord], list[RejectedCandidateRecord]]:
        """Fetch GitHub metadata → RepositoryRecord list.

        If *candidates* is omitted, loads from the 'discover' checkpoint.
        """
        stage = "enrich"
        if self.resume:
            cached = self._load_checkpoint(stage)
            if cached is not None:
                log.info("Resuming enrich from checkpoint (%d records)", len(cached))
                repos = [RepositoryRecord.model_validate(r) for r in cached]
                rej_cached = self._load_checkpoint("enrich_rejected") or []
                rejected = [RejectedCandidateRecord.model_validate(r) for r in rej_cached]
                return repos, rejected

        if candidates is None:
            raw = self._require_checkpoint(
                "discover", "Run 'discover' before 'enrich'."
            )
            candidates = _deserialize_candidate_repos(raw)
            log.info("Loaded %d candidates from discover checkpoint", len(candidates))

        cache = self._open_cache()
        async with GitHubClient.from_config(self.config, cache) as client:
            repos, rejected = await enrich_repositories(candidates, client, self.config)

        self._save_checkpoint(stage, "RepositoryRecord",
                              [r.model_dump(mode="json") for r in repos])
        self._save_checkpoint("enrich_rejected", "RejectedCandidateRecord",
                              [r.model_dump(mode="json") for r in rejected])
        return repos, rejected

    # ------------------------------------------------------------------
    # Stage 3 — Locate skills
    # ------------------------------------------------------------------

    async def run_locate_skills(
        self,
        repos: list[RepositoryRecord] | None = None,
    ) -> list[SkillCandidate]:
        """Scan repository trees → SkillCandidate list.

        If *repos* is omitted, loads from the 'enrich' checkpoint.
        """
        stage = "locate"
        if self.resume:
            cached = self._load_checkpoint(stage)
            if cached is not None:
                log.info("Resuming locate from checkpoint (%d records)", len(cached))
                return _deserialize_skill_candidates(cached)

        if repos is None:
            raw = self._require_checkpoint(
                "enrich", "Run 'enrich' before 'locate'."
            )
            repos = [RepositoryRecord.model_validate(r) for r in raw]
            log.info("Loaded %d repositories from enrich checkpoint", len(repos))

        repos = self._preselect_for_scanning(repos)

        cache = self._open_cache()
        async with GitHubClient.from_config(self.config, cache) as client:
            skill_candidates = await locate_skills(repos, client, self.config)

        self._save_checkpoint(stage, "SkillCandidate",
                              [dataclasses.asdict(c) for c in skill_candidates])
        return skill_candidates

    # ------------------------------------------------------------------
    # Stage 4 — Validate
    # ------------------------------------------------------------------

    async def run_validate(
        self,
        candidates: list[SkillCandidate] | None = None,
    ) -> tuple[list[ValidatedSkillCandidate], list[RejectedCandidateRecord]]:
        """Fetch SKILL.md content and classify each candidate.

        If *candidates* is omitted, loads from the 'locate' checkpoint.
        """
        stage = "validate"
        if self.resume:
            cached = self._load_checkpoint(stage)
            if cached is not None:
                log.info("Resuming validate from checkpoint (%d records)", len(cached))
                validated = _deserialize_validated_skills(cached)
                rej_cached = self._load_checkpoint("validate_rejected") or []
                rejected = [RejectedCandidateRecord.model_validate(r) for r in rej_cached]
                return validated, rejected

        if candidates is None:
            raw = self._require_checkpoint(
                "locate", "Run 'locate' before 'validate'."
            )
            candidates = _deserialize_skill_candidates(raw)
            log.info("Loaded %d skill candidates from locate checkpoint", len(candidates))

        cache = self._open_cache()
        async with GitHubClient.from_config(self.config, cache) as client:
            validated, rejected = await validate_candidates(candidates, client, self.config)

        self._save_checkpoint(stage, "ValidatedSkillCandidate",
                              [dataclasses.asdict(v) for v in validated])
        self._save_checkpoint("validate_rejected", "RejectedCandidateRecord",
                              [r.model_dump(mode="json") for r in rejected])
        return validated, rejected

    # ------------------------------------------------------------------
    # Stage 5 — Rank
    # ------------------------------------------------------------------

    async def run_rank(
        self,
        repos: list[RepositoryRecord] | None = None,
        validated: list[ValidatedSkillCandidate] | None = None,
    ) -> list[RepositoryRecord]:
        """Rank and select top-N repositories.

        If inputs are omitted, loads repos from 'enrich' and validated
        skills from 'validate' checkpoints.
        """
        stage = "rank"
        if self.resume:
            cached = self._load_checkpoint(stage)
            if cached is not None:
                log.info("Resuming rank from checkpoint (%d records)", len(cached))
                return [RepositoryRecord.model_validate(r) for r in cached]

        if repos is None:
            raw = self._require_checkpoint(
                "enrich", "Run 'enrich' before 'rank'."
            )
            repos = [RepositoryRecord.model_validate(r) for r in raw]
            log.info("Loaded %d repositories from enrich checkpoint", len(repos))

        if validated is None:
            raw_v = self._require_checkpoint(
                "validate", "Run 'validate' before 'rank'."
            )
            validated = _deserialize_validated_skills(raw_v)
            log.info("Loaded %d validated skills from validate checkpoint", len(validated))

        ranked = rank_repositories(repos, validated, self.config)
        self._save_checkpoint(stage, "RepositoryRecord",
                              [r.model_dump(mode="json") for r in ranked])
        return ranked

    # ------------------------------------------------------------------
    # Stage 6 — Snapshot
    # ------------------------------------------------------------------

    async def run_snapshot(
        self,
        repos: list[RepositoryRecord] | None = None,
        validated: list[ValidatedSkillCandidate] | None = None,
    ) -> tuple[list[SkillRecord], list[RejectedCandidateRecord]]:
        """Download selected skill directories at pinned commit SHA.

        If inputs are omitted, loads repos from 'rank' and validated
        skills from 'validate' checkpoints.
        """
        stage = "snapshot"
        if self.resume:
            cached = self._load_checkpoint(stage)
            if cached is not None:
                log.info("Resuming snapshot from checkpoint (%d records)", len(cached))
                skill_records = [SkillRecord.model_validate(r) for r in cached]
                rej_cached = self._load_checkpoint("snapshot_rejected") or []
                rejected = [RejectedCandidateRecord.model_validate(r) for r in rej_cached]
                return skill_records, rejected

        if repos is None:
            raw = self._require_checkpoint(
                "rank", "Run 'rank' before 'snapshot'."
            )
            repos = [RepositoryRecord.model_validate(r) for r in raw]
            log.info("Loaded %d ranked repos from rank checkpoint", len(repos))

        if validated is None:
            raw_v = self._require_checkpoint(
                "validate", "Run 'validate' before 'snapshot'."
            )
            validated = _deserialize_validated_skills(raw_v)
            log.info("Loaded %d validated skills from validate checkpoint", len(validated))

        cache = self._open_cache()
        async with GitHubClient.from_config(self.config, cache) as client:
            skill_records, rejected = await download_snapshots(
                repos, validated, client, self.config
            )

        self._save_checkpoint(stage, "SkillRecord",
                              [r.model_dump(mode="json") for r in skill_records])
        self._save_checkpoint("snapshot_rejected", "RejectedCandidateRecord",
                              [r.model_dump(mode="json") for r in rejected])
        return skill_records, rejected

    # ------------------------------------------------------------------
    # Stage 7 — Export
    # ------------------------------------------------------------------

    async def run_export(
        self,
        repos: list[RepositoryRecord] | None = None,
        skills: list[SkillRecord] | None = None,
        rejected: list[RejectedCandidateRecord] | None = None,
    ) -> None:
        """Write JSONL manifests and JSON reports.

        If inputs are omitted, loads from 'rank', 'snapshot', and all
        rejected checkpoints.
        """
        if repos is None:
            raw = self._require_checkpoint(
                "rank", "Run 'rank' before 'export'."
            )
            repos = [RepositoryRecord.model_validate(r) for r in raw]
            log.info("Loaded %d ranked repos from rank checkpoint", len(repos))

        if skills is None:
            raw_s = self._require_checkpoint(
                "snapshot", "Run 'snapshot' before 'export'."
            )
            skills = [SkillRecord.model_validate(r) for r in raw_s]
            log.info("Loaded %d skill records from snapshot checkpoint", len(skills))

        if rejected is None:
            rejected = []
            for rej_stage in ("enrich_rejected", "validate_rejected", "snapshot_rejected"):
                raw_r = self._load_checkpoint(rej_stage) or []
                rejected.extend(
                    RejectedCandidateRecord.model_validate(r) for r in raw_r
                )
            log.info("Loaded %d total rejected records from checkpoints", len(rejected))

        write_manifests(repos, skills, rejected, self.config)
        write_reports(repos, skills, rejected, self.config, run_id=self.run_id)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    async def run_all(self) -> None:
        """Chain all 7 stages end-to-end with checkpoint save/load."""
        log.info("Pipeline run_id=%s starting", self.run_id)

        candidates = await self.run_discover()
        repos, enrich_rejected = await self.run_enrich(candidates)
        skill_candidates = await self.run_locate_skills(repos)
        validated, validate_rejected = await self.run_validate(skill_candidates)
        # rank needs ALL repos (from enrich), not just the ones with skills
        ranked_repos = await self.run_rank(repos, validated)
        skill_records, snapshot_rejected = await self.run_snapshot(ranked_repos, validated)

        all_rejected = enrich_rejected + validate_rejected + snapshot_rejected
        await self.run_export(ranked_repos, skill_records, all_rejected)

        selected = sum(1 for r in ranked_repos if r.selected_for_export)
        log.info(
            "Pipeline complete: repos=%d selected=%d skills=%d rejected=%d",
            len(ranked_repos), selected, len(skill_records), len(all_rejected),
        )

    def _preselect_for_scanning(
        self, repos: list[RepositoryRecord]
    ) -> list[RepositoryRecord]:
        """Cap the repos carried into locate/validate/snapshot to the top-K by stars.

        The final export is the top-N repos by stars, so tree-scanning every
        discovered candidate is wasteful and trips GitHub's secondary rate limit.
        When ``github.preselect_top_k`` is set (>0), keep only the K
        highest-starred qualifying repos (respecting the fork/archived filters).
        K should be a generous multiple of ``top_n_repositories`` so that repos
        which turn out to have no valid skill don't starve the final top-N.
        """
        k = self.config.github.preselect_top_k
        if k <= 0 or len(repos) <= k:
            return repos
        eligible = [
            r for r in repos
            if (self.config.github.include_forks or not r.is_fork)
            and (self.config.github.include_archived or not r.is_archived)
        ]
        eligible.sort(key=lambda r: r.stars, reverse=True)
        selected = eligible[:k]
        log.info(
            "Preselect: scanning top %d of %d repos by stars "
            "(preselect_top_k=%d, min stars in slice=%d)",
            len(selected), len(repos), k,
            selected[-1].stars if selected else 0,
        )
        return selected

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------

    def _open_cache(self) -> GitHubCache | None:
        cfg = self.config.cache
        if not cfg.enabled:
            return None
        return GitHubCache(directory=cfg.directory, enabled=True)

    def _save_checkpoint(
        self, stage: str, record_type: str, records: list[Any]
    ) -> None:
        try:
            save_checkpoint(
                stage=stage,
                run_id=self.run_id,
                config_hash=self._config_hash,
                record_type=record_type,
                records=records,
                output_dir=self.config.output.directory,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to save checkpoint for stage=%s: %s", stage, exc)

    def _load_checkpoint(self, stage: str) -> list[Any] | None:
        try:
            return load_checkpoint(
                stage=stage,
                run_id=self.run_id,
                config_hash=self._config_hash,
                output_dir=self.config.output.directory,
            )
        except CheckpointError as exc:
            log.warning("Cannot load checkpoint stage=%s: %s", stage, exc)
            return None

    def _require_checkpoint(self, stage: str, hint: str) -> list[Any]:
        """Load a checkpoint or raise PipelineError if absent."""
        records = self._load_checkpoint(stage)
        if records is None:
            raise PipelineError(
                f"No compatible checkpoint found for stage '{stage}'. {hint} "
                f"(run_id={self.run_id})"
            )
        return records
