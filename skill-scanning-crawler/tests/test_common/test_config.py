"""Tests for config loading and CrawlerConfig."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from skill_scanning_crawler.common.config import (
    CrawlerConfig,
    load_config,
)
from skill_scanning_crawler.common.exceptions import ConfigError

# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_load_example_config(config_path: Path) -> None:
    """Round-trip: load the canonical example config without error."""
    cfg = load_config(config_path)
    assert isinstance(cfg, CrawlerConfig)


def test_example_config_platforms(config_path: Path) -> None:
    cfg = load_config(config_path)
    assert cfg.platforms == ["github"]


def test_example_config_seed_lists(config_path: Path) -> None:
    cfg = load_config(config_path)
    assert len(cfg.seed_lists) >= 1
    assert cfg.seed_lists[0].name  # non-empty name


def test_example_config_github_section(config_path: Path) -> None:
    cfg = load_config(config_path)
    assert cfg.github.top_n_repositories == 50
    assert cfg.github.include_forks is False
    assert cfg.github.include_archived is False
    assert cfg.github.token_env_var == "GITHUB_TOKEN"


def test_example_config_rate_limits(config_path: Path) -> None:
    cfg = load_config(config_path)
    # Gentle concurrency + a preselect cap keep the crawl under GitHub's
    # secondary rate limit (see PART1_FIXES.md).
    assert cfg.rate_limits.search_concurrency == 1
    assert cfg.rate_limits.metadata_concurrency == 5
    assert cfg.rate_limits.tree_concurrency == 3
    assert cfg.github.preselect_top_k == 250
    assert cfg.github.max_skills_per_repo == 25


def test_example_config_output(config_path: Path) -> None:
    cfg = load_config(config_path)
    assert cfg.output.manifests_directory == "data/manifests"
    assert cfg.output.snapshots_directory == "data/snapshots"


def test_compute_hash_is_stable(config_path: Path) -> None:
    """Same config parsed twice must produce the same hash."""
    cfg1 = load_config(config_path)
    cfg2 = load_config(config_path)
    assert cfg1.compute_hash() == cfg2.compute_hash()


def test_compute_hash_is_hex_string(config_path: Path) -> None:
    cfg = load_config(config_path)
    h = cfg.compute_hash()
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nonexistent.yaml")


def test_invalid_yaml_raises_config_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("key: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(bad)


def test_non_mapping_yaml_raises_config_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(bad)


def test_unknown_top_level_key_raises(tmp_path: Path, config_path: Path) -> None:
    raw = yaml.safe_load(config_path.read_text())
    raw["unexpected_key"] = "value"
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError, match="Unknown top-level"):
        load_config(bad)


def test_missing_required_section_raises(tmp_path: Path, config_path: Path) -> None:
    raw = yaml.safe_load(config_path.read_text())
    del raw["github"]
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError, match="Missing required"):
        load_config(bad)


def test_seed_list_missing_name_raises(tmp_path: Path, config_path: Path) -> None:
    raw = yaml.safe_load(config_path.read_text())
    raw["seed_lists"] = [{"url": "https://example.com/"}]
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError, match="name"):
        load_config(bad)


def test_local_path_seed_list_accepted(tmp_path: Path, config_path: Path) -> None:
    """Seed list entries with local_path (no url) are valid."""
    raw = yaml.safe_load(config_path.read_text())
    raw["seed_lists"] = [{"name": "local-seeds", "local_path": "/some/path.yaml"}]
    good = tmp_path / "good.yaml"
    good.write_text(yaml.dump(raw), encoding="utf-8")
    cfg = load_config(good)
    assert cfg.seed_lists[0].local_path == "/some/path.yaml"
    assert cfg.seed_lists[0].url is None
