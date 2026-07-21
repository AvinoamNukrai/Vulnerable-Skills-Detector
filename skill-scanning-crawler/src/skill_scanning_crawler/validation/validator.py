"""Strict skill validator.

``classify_skill`` is the core pure function of the validation engine.
It takes text content and path metadata and returns a (ValidationStatus, reason)
tuple. It never performs I/O, network calls, or code execution.

The pipeline-level ``validate_batch`` (which fetches SKILL.md content via the
GitHub client) lives in Milestone 7 and will call ``classify_skill`` for each
candidate.
"""

from __future__ import annotations

from skill_scanning_crawler.common.enums import ValidationStatus
from skill_scanning_crawler.common.exceptions import MalformedFrontmatterError
from skill_scanning_crawler.validation.frontmatter import parse_frontmatter
from skill_scanning_crawler.validation.path_heuristics import (
    is_documentation_path,
    is_example_path,
)
from skill_scanning_crawler.validation.size_checker import preliminary_size_check

# Default path heuristic lists (overridable via policy config).
_DEFAULT_DOC_INDICATORS = [
    "docs",
    "documentation",
    "tutorial",
    "tutorials",
    "spec",
    "specification",
]
_DEFAULT_EXAMPLE_INDICATORS = [
    "example",
    "examples",
    "sample",
    "samples",
    "template",
    "templates",
    "demo",
    "demos",
]


def classify_skill(
    skill_md_content: str,
    skill_path: str,
    tree_file_sizes: dict[str, int] | None = None,
    *,
    doc_indicators: list[str] | None = None,
    example_indicators: list[str] | None = None,
    max_skill_directory_size_mb: float = 25.0,
    max_file_size_mb: float = 5.0,
) -> tuple[ValidationStatus, str]:
    """Apply strict validation rules to a SKILL.md candidate.

    This is a pure function — no I/O, no network calls.

    Args:
        skill_md_content: Raw text of the SKILL.md file.
        skill_path: Relative path of the skill directory within the repository
            (e.g. ``"skills/pdf-analyzer"``).
        tree_file_sizes: Optional mapping of relative file paths to sizes in
            bytes, used for the preliminary size check.
        doc_indicators: Path segment tokens that indicate documentation-only
            content. Defaults to ``_DEFAULT_DOC_INDICATORS``.
        example_indicators: Path segment tokens that indicate example/template
            content. Defaults to ``_DEFAULT_EXAMPLE_INDICATORS``.
        max_skill_directory_size_mb: Preliminary total-directory size limit.
        max_file_size_mb: Preliminary per-file size limit.

    Returns:
        A ``(ValidationStatus, reason_string)`` tuple.
    """
    doc_ind = doc_indicators if doc_indicators is not None else _DEFAULT_DOC_INDICATORS
    ex_ind = example_indicators if example_indicators is not None else _DEFAULT_EXAMPLE_INDICATORS

    # ------------------------------------------------------------------
    # 1. Preliminary size check (uses tree metadata if available)
    # ------------------------------------------------------------------
    if tree_file_sizes:
        size_status = preliminary_size_check(
            tree_file_sizes, max_skill_directory_size_mb, max_file_size_mb
        )
        if size_status is not None:
            return size_status, "Skill directory exceeds configured size limits (preliminary check)."

    # ------------------------------------------------------------------
    # 2. Frontmatter present and parseable
    # ------------------------------------------------------------------
    try:
        frontmatter = parse_frontmatter(skill_md_content)
    except MalformedFrontmatterError as exc:
        return ValidationStatus.INVALID_MALFORMED_FRONTMATTER, str(exc)

    if frontmatter is None:
        return (
            ValidationStatus.INVALID_MISSING_FRONTMATTER,
            "SKILL.md does not contain a YAML frontmatter block delimited by '---'.",
        )

    # ------------------------------------------------------------------
    # 3. Required frontmatter fields
    # ------------------------------------------------------------------
    name = frontmatter.get("name")
    if not name or not str(name).strip():
        return (
            ValidationStatus.INVALID_MISSING_NAME,
            "Frontmatter 'name' field is absent or empty.",
        )

    description = frontmatter.get("description")
    if not description or not str(description).strip():
        return (
            ValidationStatus.INVALID_MISSING_DESCRIPTION,
            "Frontmatter 'description' field is absent or empty.",
        )

    # ------------------------------------------------------------------
    # 4. Path heuristics (documentation-only / example-only)
    # ------------------------------------------------------------------
    if is_documentation_path(skill_path, doc_ind):
        return (
            ValidationStatus.DOCUMENTATION_ONLY,
            f"Skill path '{skill_path}' contains a documentation-directory indicator.",
        )

    if is_example_path(skill_path, ex_ind):
        return (
            ValidationStatus.EXAMPLE_ONLY,
            f"Skill path '{skill_path}' contains an example/template-directory indicator.",
        )

    # ------------------------------------------------------------------
    # 5. Passed all strict checks
    # ------------------------------------------------------------------
    return ValidationStatus.VALID_STANDARD, "Passed all strict validation rules."
