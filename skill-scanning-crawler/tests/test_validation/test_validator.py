"""Tests for the pure classify_skill function and size checker."""

from __future__ import annotations

from pathlib import Path

from skill_scanning_crawler.common.enums import ValidationStatus
from skill_scanning_crawler.validation.size_checker import preliminary_size_check
from skill_scanning_crawler.validation.validator import classify_skill

FIXTURES = Path(__file__).parent.parent / "fixtures" / "skills"
_MB = 1_048_576


def _read(name: str) -> str:
    return (FIXTURES / name / "SKILL.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# classify_skill happy path
# ---------------------------------------------------------------------------


def test_valid_standard_skill() -> None:
    status, reason = classify_skill(_read("valid_standard"), "skills/pdf-analyzer")
    assert status == ValidationStatus.VALID_STANDARD
    assert reason  # non-empty


def test_valid_skill_with_tree_sizes_within_limit() -> None:
    sizes = {"SKILL.md": 1024, "scripts/run.py": 2048}
    status, _ = classify_skill(
        _read("valid_standard"),
        "skills/pdf-analyzer",
        tree_file_sizes=sizes,
        max_skill_directory_size_mb=25.0,
        max_file_size_mb=5.0,
    )
    assert status == ValidationStatus.VALID_STANDARD


# ---------------------------------------------------------------------------
# classify_skill rejection paths
# ---------------------------------------------------------------------------


def test_missing_frontmatter() -> None:
    status, reason = classify_skill(_read("missing_frontmatter"), "skills/x")
    assert status == ValidationStatus.INVALID_MISSING_FRONTMATTER
    assert "frontmatter" in reason.lower()


def test_malformed_yaml() -> None:
    status, reason = classify_skill(_read("malformed_yaml"), "skills/x")
    assert status == ValidationStatus.INVALID_MALFORMED_FRONTMATTER


def test_missing_name() -> None:
    status, reason = classify_skill(_read("missing_name"), "skills/x")
    assert status == ValidationStatus.INVALID_MISSING_NAME
    assert "name" in reason.lower()


def test_missing_description() -> None:
    status, reason = classify_skill(_read("missing_description"), "skills/x")
    assert status == ValidationStatus.INVALID_MISSING_DESCRIPTION
    assert "description" in reason.lower()


def test_documentation_only_path() -> None:
    status, reason = classify_skill(_read("docs_path"), "docs/my-skill")
    assert status == ValidationStatus.DOCUMENTATION_ONLY
    assert "docs" in reason.lower() or "documentation" in reason.lower()


def test_example_only_path() -> None:
    status, reason = classify_skill(_read("example_path"), "examples/starter")
    assert status == ValidationStatus.EXAMPLE_ONLY
    assert "example" in reason.lower()


def test_too_large_via_single_oversized_file() -> None:
    sizes = {"SKILL.md": 1024, "huge.bin": int(10 * _MB)}
    status, _ = classify_skill(
        _read("valid_standard"),
        "skills/x",
        tree_file_sizes=sizes,
        max_file_size_mb=5.0,
    )
    assert status == ValidationStatus.TOO_LARGE


def test_too_large_via_total_directory_size() -> None:
    sizes = {f"file_{i}.txt": int(5 * _MB) for i in range(10)}
    status, _ = classify_skill(
        _read("valid_standard"),
        "skills/x",
        tree_file_sizes=sizes,
        max_skill_directory_size_mb=25.0,
        max_file_size_mb=5.0,
    )
    assert status == ValidationStatus.TOO_LARGE


# ---------------------------------------------------------------------------
# Multi-skill scenario (two paths classified independently)
# ---------------------------------------------------------------------------


def test_multi_skill_repo_independent_classification() -> None:
    valid_content = _read("valid_standard")
    doc_content = _read("docs_path")

    status_a, _ = classify_skill(valid_content, "skills/pdf-analyzer")
    status_b, _ = classify_skill(doc_content, "docs/pdf-analyzer")

    assert status_a == ValidationStatus.VALID_STANDARD
    assert status_b == ValidationStatus.DOCUMENTATION_ONLY


# ---------------------------------------------------------------------------
# Size checker unit tests
# ---------------------------------------------------------------------------


def test_size_checker_within_limits() -> None:
    sizes = {"SKILL.md": 512, "run.py": 1024}
    result = preliminary_size_check(sizes, max_skill_directory_size_mb=25.0, max_file_size_mb=5.0)
    assert result is None


def test_size_checker_single_file_over_limit() -> None:
    sizes = {"SKILL.md": 512, "giant.bin": int(6 * _MB)}
    result = preliminary_size_check(sizes, max_skill_directory_size_mb=25.0, max_file_size_mb=5.0)
    assert result == ValidationStatus.TOO_LARGE


def test_size_checker_total_over_limit() -> None:
    sizes = {f"f{i}.txt": int(3 * _MB) for i in range(10)}
    result = preliminary_size_check(sizes, max_skill_directory_size_mb=25.0, max_file_size_mb=5.0)
    assert result == ValidationStatus.TOO_LARGE


def test_size_checker_empty_dict() -> None:
    result = preliminary_size_check({}, max_skill_directory_size_mb=25.0, max_file_size_mb=5.0)
    assert result is None
