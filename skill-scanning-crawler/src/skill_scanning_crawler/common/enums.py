"""Enumerations shared across pipeline stages."""

from enum import StrEnum


class Platform(StrEnum):
    GITHUB = "github"


class DiscoverySource(StrEnum):
    SEED_LIST = "seed_list"
    GITHUB_CODE_SEARCH = "github_code_search"
    GITHUB_REPO_SEARCH = "github_repo_search"


class ValidationStatus(StrEnum):
    # Valid
    VALID_STANDARD = "valid_standard"
    VALID_LENIENT = "valid_lenient"

    # Invalid — structural
    INVALID_MISSING_SKILL_MD = "invalid_missing_skill_md"
    INVALID_MISSING_FRONTMATTER = "invalid_missing_frontmatter"
    INVALID_MALFORMED_FRONTMATTER = "invalid_malformed_frontmatter"
    INVALID_MISSING_NAME = "invalid_missing_name"
    INVALID_MISSING_DESCRIPTION = "invalid_missing_description"

    # Invalid — content category
    DOCUMENTATION_ONLY = "documentation_only"
    EXAMPLE_ONLY = "example_only"

    # Invalid — size / type / availability
    TOO_LARGE = "too_large"
    BINARY_OR_UNSUPPORTED = "binary_or_unsupported"
    REPOSITORY_UNAVAILABLE = "repository_unavailable"
    UNDETERMINED = "undetermined"
