"""Configuration loading and typed dataclasses for the crawler."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from skill_scanning_crawler.common.exceptions import ConfigError

_KNOWN_TOP_LEVEL_KEYS = {
    "platforms",
    "seed_lists",
    "github",
    "rate_limits",
    "validation",
    "output",
    "cache",
}


@dataclass
class SeedListConfig:
    name: str
    url: str | None = None
    local_path: str | None = None


@dataclass
class GitHubConfig:
    token_env_var: str = "GITHUB_TOKEN"
    include_forks: bool = False
    include_archived: bool = False
    top_n_repositories: int = 50
    # Cap how many enriched repos (highest-starred first) are carried into the
    # expensive locate/validate/snapshot stages. 0 = no cap (scan everything).
    # Because the final output is the top-N repos by stars, tree-scanning every
    # discovered candidate is wasteful and trips GitHub's secondary rate limit;
    # scanning only the top-K by stars (K a generous multiple of N) is far
    # cheaper and preserves the ranked result. See docs/PART1_FIXES.md.
    preselect_top_k: int = 0
    # Cap SKILL.md candidates kept per repository. Aggregator/collection repos
    # can contain thousands of SKILL.md files; validating+snapshotting all of
    # them would blow the primary rate limit. 0 = unlimited. When capped, the
    # shallowest paths are kept (deterministic), which favours top-level skills.
    max_skills_per_repo: int = 0
    max_repository_size_mb: float = 100.0
    max_file_size_mb: float = 5.0
    request_timeout_seconds: int = 30


@dataclass
class RateLimitsConfig:
    search_concurrency: int = 2
    metadata_concurrency: int = 8
    tree_concurrency: int = 6
    download_concurrency: int = 4
    max_retries: int = 5
    backoff_initial_seconds: float = 1.0
    backoff_max_seconds: float = 60.0


@dataclass
class ValidationConfig:
    strict_validation: bool = True
    include_lenient_in_export: bool = False
    write_rejected_candidates: bool = True


@dataclass
class OutputConfig:
    directory: str = "data"
    manifests_directory: str = "data/manifests"
    snapshots_directory: str = "data/snapshots"
    reports_directory: str = "data/reports"
    write_statistics: bool = True
    deterministic_ordering: bool = True


@dataclass
class CacheConfig:
    enabled: bool = True
    directory: str = ".cache/skill-scanning-crawler"


@dataclass
class CrawlerConfig:
    platforms: list[str]
    seed_lists: list[SeedListConfig]
    github: GitHubConfig
    rate_limits: RateLimitsConfig
    validation: ValidationConfig
    output: OutputConfig
    cache: CacheConfig

    def compute_hash(self) -> str:
        """Return a SHA-256 hex digest of the serialised config.

        Used by checkpoint envelopes to detect config changes between runs.
        """
        serialised = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(serialised.encode()).hexdigest()


def load_config(path: Path) -> CrawlerConfig:
    """Parse a YAML config file and return a typed CrawlerConfig.

    Raises ConfigError for missing files, invalid YAML, unknown top-level
    keys, missing required sections, or invalid field types.
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"Config file {path} must be a YAML mapping, got {type(raw).__name__}")

    unknown = set(raw.keys()) - _KNOWN_TOP_LEVEL_KEYS
    if unknown:
        raise ConfigError(f"Unknown top-level config keys: {sorted(unknown)}")

    missing = _KNOWN_TOP_LEVEL_KEYS - set(raw.keys())
    if missing:
        raise ConfigError(f"Missing required config sections: {sorted(missing)}")

    try:
        return _parse(raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"Config parse error in {path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse(raw: dict[str, Any]) -> CrawlerConfig:
    return CrawlerConfig(
        platforms=_require_list(raw, "platforms", str),
        seed_lists=_parse_seed_lists(raw["seed_lists"]),
        github=_parse_github(raw["github"]),
        rate_limits=_parse_rate_limits(raw["rate_limits"]),
        validation=_parse_validation(raw["validation"]),
        output=_parse_output(raw["output"]),
        cache=_parse_cache(raw["cache"]),
    )


def _parse_seed_lists(raw: Any) -> list[SeedListConfig]:
    if not isinstance(raw, list):
        raise ValueError(f"'seed_lists' must be a list, got {type(raw).__name__}")
    result: list[SeedListConfig] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"seed_lists[{i}] must be a mapping")
        if "name" not in item:
            raise ValueError(f"seed_lists[{i}] missing required key 'name'")
        result.append(
            SeedListConfig(
                name=str(item["name"]),
                url=str(item["url"]) if "url" in item else None,
                local_path=str(item["local_path"]) if "local_path" in item else None,
            )
        )
    return result


def _parse_github(raw: Any) -> GitHubConfig:
    _require_dict(raw, "github")
    return GitHubConfig(
        token_env_var=str(raw.get("token_env_var", "GITHUB_TOKEN")),
        include_forks=bool(raw.get("include_forks", False)),
        include_archived=bool(raw.get("include_archived", False)),
        top_n_repositories=int(raw.get("top_n_repositories", 50)),
        preselect_top_k=int(raw.get("preselect_top_k", 0)),
        max_skills_per_repo=int(raw.get("max_skills_per_repo", 0)),
        max_repository_size_mb=float(raw.get("max_repository_size_mb", 100.0)),
        max_file_size_mb=float(raw.get("max_file_size_mb", 5.0)),
        request_timeout_seconds=int(raw.get("request_timeout_seconds", 30)),
    )


def _parse_rate_limits(raw: Any) -> RateLimitsConfig:
    _require_dict(raw, "rate_limits")
    return RateLimitsConfig(
        search_concurrency=int(raw.get("search_concurrency", 2)),
        metadata_concurrency=int(raw.get("metadata_concurrency", 8)),
        tree_concurrency=int(raw.get("tree_concurrency", 6)),
        download_concurrency=int(raw.get("download_concurrency", 4)),
        max_retries=int(raw.get("max_retries", 5)),
        backoff_initial_seconds=float(raw.get("backoff_initial_seconds", 1.0)),
        backoff_max_seconds=float(raw.get("backoff_max_seconds", 60.0)),
    )


def _parse_validation(raw: Any) -> ValidationConfig:
    _require_dict(raw, "validation")
    return ValidationConfig(
        strict_validation=bool(raw.get("strict_validation", True)),
        include_lenient_in_export=bool(raw.get("include_lenient_in_export", False)),
        write_rejected_candidates=bool(raw.get("write_rejected_candidates", True)),
    )


def _parse_output(raw: Any) -> OutputConfig:
    _require_dict(raw, "output")
    return OutputConfig(
        directory=str(raw.get("directory", "data")),
        manifests_directory=str(raw.get("manifests_directory", "data/manifests")),
        snapshots_directory=str(raw.get("snapshots_directory", "data/snapshots")),
        reports_directory=str(raw.get("reports_directory", "data/reports")),
        write_statistics=bool(raw.get("write_statistics", True)),
        deterministic_ordering=bool(raw.get("deterministic_ordering", True)),
    )


def _parse_cache(raw: Any) -> CacheConfig:
    _require_dict(raw, "cache")
    return CacheConfig(
        enabled=bool(raw.get("enabled", True)),
        directory=str(raw.get("directory", ".cache/skill-scanning-crawler")),
    )


def _require_dict(value: Any, section: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"'{section}' must be a mapping, got {type(value).__name__}")


def _require_list(raw: dict[str, Any], key: str, item_type: type) -> list[Any]:
    value = raw[key]
    if not isinstance(value, list):
        raise ValueError(f"'{key}' must be a list")
    for i, item in enumerate(value):
        if not isinstance(item, item_type):
            raise ValueError(f"'{key}[{i}]' must be {item_type.__name__}, got {type(item).__name__}")
    return list(value)
