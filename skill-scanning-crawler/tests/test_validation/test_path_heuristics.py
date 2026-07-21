"""Tests for path-based documentation and example heuristics."""

from __future__ import annotations

from skill_scanning_crawler.validation.path_heuristics import (
    is_documentation_path,
    is_example_path,
)

_DOC_IND = ["docs", "documentation", "tutorial", "tutorials", "spec", "specification"]
_EX_IND = ["example", "examples", "sample", "samples", "template", "templates", "demo", "demos"]


# ---------------------------------------------------------------------------
# Documentation path heuristics
# ---------------------------------------------------------------------------


def test_docs_segment_detected() -> None:
    assert is_documentation_path("docs/SKILL.md", _DOC_IND) is True


def test_docs_in_subdirectory_detected() -> None:
    assert is_documentation_path("src/docs/my-skill", _DOC_IND) is True


def test_documentation_segment_detected() -> None:
    assert is_documentation_path("documentation/skills/x", _DOC_IND) is True


def test_spec_segment_detected() -> None:
    assert is_documentation_path("spec/my-skill", _DOC_IND) is True


def test_skills_path_not_documentation() -> None:
    assert is_documentation_path("skills/my-skill", _DOC_IND) is False


def test_src_path_not_documentation() -> None:
    assert is_documentation_path("src/skills/pdf-analyzer", _DOC_IND) is False


def test_doc_as_prefix_of_segment_not_matched() -> None:
    # "my-docs-skill" should NOT match because it is not a standalone segment.
    assert is_documentation_path("my-docs-skill/SKILL.md", _DOC_IND) is False


def test_empty_path_not_documentation() -> None:
    assert is_documentation_path("", _DOC_IND) is False


def test_case_insensitive_docs() -> None:
    assert is_documentation_path("DOCS/my-skill", _DOC_IND) is True


# ---------------------------------------------------------------------------
# Example path heuristics
# ---------------------------------------------------------------------------


def test_examples_segment_detected() -> None:
    assert is_example_path("examples/my-skill", _EX_IND) is True


def test_example_singular_detected() -> None:
    assert is_example_path("example/x", _EX_IND) is True


def test_sample_detected() -> None:
    assert is_example_path("skills/sample", _EX_IND) is True


def test_template_detected() -> None:
    assert is_example_path("templates/starter-skill", _EX_IND) is True


def test_demo_detected() -> None:
    assert is_example_path("demo/my-skill", _EX_IND) is True


def test_skills_path_not_example() -> None:
    assert is_example_path("skills/my-skill", _EX_IND) is False


def test_example_as_prefix_not_matched() -> None:
    assert is_example_path("my-examples-repo/skill", _EX_IND) is False


def test_case_insensitive_example() -> None:
    assert is_example_path("EXAMPLES/skill", _EX_IND) is True
