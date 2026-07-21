"""Preliminary size checks using file-size metadata from the GitHub tree API.

This is a *preliminary* check only, performed before any files are downloaded.
Final, authoritative per-file and total-directory enforcement happens in
``download/downloader.py`` after actual bytes are fetched.
"""

from __future__ import annotations

from skill_scanning_crawler.common.enums import ValidationStatus

_BYTES_PER_MB = 1_048_576


def preliminary_size_check(
    tree_file_sizes: dict[str, int],
    max_skill_directory_size_mb: float,
    max_file_size_mb: float,
) -> ValidationStatus | None:
    """Check whether a skill directory would exceed configured size limits.

    Uses file-size metadata from the GitHub tree API response. Returns
    ``ValidationStatus.TOO_LARGE`` if limits are exceeded, or ``None``
    if the candidate passes this preliminary check.

    Args:
        tree_file_sizes: Mapping of relative file path to size in bytes,
            as reported by the GitHub tree API.
        max_skill_directory_size_mb: Maximum allowed total size for the
            skill directory in megabytes.
        max_file_size_mb: Maximum allowed size for any individual file
            in megabytes.

    Returns:
        ``ValidationStatus.TOO_LARGE`` if any limit is exceeded, else ``None``.
    """
    max_dir_bytes = max_skill_directory_size_mb * _BYTES_PER_MB
    max_file_bytes = max_file_size_mb * _BYTES_PER_MB

    total = 0
    for size_bytes in tree_file_sizes.values():
        if size_bytes > max_file_bytes:
            return ValidationStatus.TOO_LARGE
        total += size_bytes

    if total > max_dir_bytes:
        return ValidationStatus.TOO_LARGE

    return None
