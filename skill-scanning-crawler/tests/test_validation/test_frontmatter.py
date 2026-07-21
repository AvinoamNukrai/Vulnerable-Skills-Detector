"""Tests for the YAML frontmatter parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_scanning_crawler.common.exceptions import MalformedFrontmatterError
from skill_scanning_crawler.validation.frontmatter import parse_frontmatter

FIXTURES = Path(__file__).parent.parent / "fixtures" / "skills"


def _read(name: str) -> str:
    return (FIXTURES / name / "SKILL.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_valid_frontmatter_returns_dict() -> None:
    result = parse_frontmatter(_read("valid_standard"))
    assert isinstance(result, dict)
    assert result["name"] == "pdf-analyzer"
    assert "description" in result


def test_extra_frontmatter_fields_preserved() -> None:
    result = parse_frontmatter(_read("valid_standard"))
    assert result is not None
    assert "version" in result


def test_closing_ellipsis_delimiter_accepted() -> None:
    content = "---\nname: x\ndescription: y\n...\n\n# body\n"
    result = parse_frontmatter(content)
    assert result is not None
    assert result["name"] == "x"


def test_empty_frontmatter_block_returns_empty_dict() -> None:
    content = "---\n---\n\n# body\n"
    result = parse_frontmatter(content)
    assert result == {}


# ---------------------------------------------------------------------------
# No-frontmatter tests
# ---------------------------------------------------------------------------


def test_no_frontmatter_returns_none() -> None:
    result = parse_frontmatter(_read("missing_frontmatter"))
    assert result is None


def test_no_leading_delimiter_returns_none() -> None:
    content = "# Just a markdown file\n\nNo frontmatter here.\n"
    result = parse_frontmatter(content)
    assert result is None


def test_opening_delimiter_without_closing_returns_none() -> None:
    content = "---\nname: orphan\n\n# body without closing delimiter\n"
    result = parse_frontmatter(content)
    assert result is None


def test_empty_string_returns_none() -> None:
    assert parse_frontmatter("") is None


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


def test_malformed_yaml_raises() -> None:
    with pytest.raises(MalformedFrontmatterError):
        parse_frontmatter(_read("malformed_yaml"))


def test_non_mapping_yaml_raises() -> None:
    content = "---\n- item1\n- item2\n---\n"
    with pytest.raises(MalformedFrontmatterError, match="mapping"):
        parse_frontmatter(content)


def test_bom_prefixed_frontmatter_is_parsed() -> None:
    """Regression: a UTF-8 BOM before '---' must not be read as 'no frontmatter'."""
    content = "\ufeff---\nname: PDF Skill\ndescription: Handles PDFs\n---\n# Body\n"
    parsed = parse_frontmatter(content)
    assert parsed == {"name": "PDF Skill", "description": "Handles PDFs"}
