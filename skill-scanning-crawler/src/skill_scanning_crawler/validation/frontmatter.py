"""YAML frontmatter parser for SKILL.md files.

Operates purely on text content. No I/O, no network, no code execution.

Frontmatter is defined as a YAML block delimited by ``---`` on its own line
at the very start of the file, with a closing ``---`` or ``...`` line.
"""

from __future__ import annotations

from typing import Any

import yaml

from skill_scanning_crawler.common.exceptions import MalformedFrontmatterError

_DELIMITER = "---"
_CLOSE_DELIMITER = ("---", "...")


def parse_frontmatter(content: str) -> dict[str, Any] | None:
    """Extract and parse the YAML frontmatter from SKILL.md content.

    Args:
        content: Raw text content of a SKILL.md file.

    Returns:
        Parsed frontmatter dict, or ``None`` if no frontmatter block is present.

    Raises:
        MalformedFrontmatterError: If a frontmatter block is detected but its
            YAML is syntactically invalid.
    """
    # Strip a leading UTF-8 BOM if present. ``str.strip()`` does not treat
    # U+FEFF as whitespace, so a BOM-prefixed opening delimiter would
    # otherwise be misread as "no frontmatter" and reject a valid skill.
    if content.startswith("\ufeff"):
        content = content[1:]

    lines = content.splitlines()
    if not lines or lines[0].strip() != _DELIMITER:
        return None

    close_idx: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() in _CLOSE_DELIMITER:
            close_idx = i
            break

    if close_idx is None:
        # Opening delimiter found but no closing delimiter — treat as no frontmatter.
        return None

    yaml_block = "\n".join(lines[1:close_idx])
    try:
        parsed = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise MalformedFrontmatterError(
            f"YAML frontmatter is syntactically invalid: {exc}"
        ) from exc

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise MalformedFrontmatterError(
            f"YAML frontmatter must be a mapping, got {type(parsed).__name__}"
        )
    return parsed
