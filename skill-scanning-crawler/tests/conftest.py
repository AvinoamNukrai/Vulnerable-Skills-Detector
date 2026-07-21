"""Shared test fixtures and pytest configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Marker registration (also declared in pyproject.toml [tool.pytest.ini_options])
# ---------------------------------------------------------------------------

# The integration marker is registered via pyproject.toml.
# Tests in tests/integration/ also use skipif to auto-skip when token is absent.


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "discovery.example.yaml"


@pytest.fixture()
def fixtures_dir() -> Path:
    """Absolute path to the tests/fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture()
def config_path() -> Path:
    """Absolute path to config/discovery.example.yaml."""
    return CONFIG_PATH


@pytest.fixture()
def sample_config(config_path: Path):  # type: ignore[return]
    """Loaded CrawlerConfig from the example config file."""
    from skill_scanning_crawler.common.config import load_config

    return load_config(config_path)


@pytest.fixture()
def tmp_output_dir(tmp_path: Path) -> Path:
    """Temporary output directory for a single test."""
    out = tmp_path / "data"
    out.mkdir()
    return out


@pytest.fixture()
def tmp_cache_dir(tmp_path: Path) -> Path:
    """Temporary cache directory for a single test."""
    cache = tmp_path / ".cache"
    cache.mkdir()
    return cache
