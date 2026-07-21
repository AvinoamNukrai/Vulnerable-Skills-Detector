"""Path-based heuristics for detecting documentation-only and example-only skill candidates.

These functions are pure: they take a path string and a list of indicator
substrings from config/validation_policy.yaml and return a boolean.

A positive flag from these heuristics is not an automatic rejection.
The validator combines path evidence with content evidence.
"""

from __future__ import annotations


def is_documentation_path(path: str, indicators: list[str]) -> bool:
    """Return True if the path contains a documentation-directory indicator.

    Matching is case-insensitive and checks each path segment individually
    so that ``docs/skills/my-skill`` matches but ``my-docs-skill`` does not.

    Args:
        path: Relative path of the skill directory (e.g. ``docs/skills/my-skill``).
        indicators: List of indicator strings from ``validation_policy.yaml``,
            e.g. ``["docs/", "documentation/", "spec/"]``.
    """
    normalised = path.replace("\\", "/").lower()
    segments = normalised.split("/")
    for indicator in indicators:
        indicator_clean = indicator.rstrip("/").lower()
        if indicator_clean in segments:
            return True
    return False


def is_example_path(path: str, indicators: list[str]) -> bool:
    """Return True if any path segment matches an example/sample indicator.

    Args:
        path: Relative path of the skill directory.
        indicators: List of indicator strings from ``validation_policy.yaml``,
            e.g. ``["example", "examples", "sample", "template", "demo"]``.
    """
    normalised = path.replace("\\", "/").lower()
    segments = normalised.split("/")
    for indicator in indicators:
        indicator_clean = indicator.rstrip("/").lower()
        if indicator_clean in segments:
            return True
    return False
