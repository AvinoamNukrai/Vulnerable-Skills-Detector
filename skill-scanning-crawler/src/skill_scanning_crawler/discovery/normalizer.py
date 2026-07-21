"""GitHub URL normalization and repository identity deduplication.

A *canonical_id* is ``github:<owner_lower>/<repo_lower>``.
Deduplication merges discovery_sources and discovery_queries from duplicates.
"""

from __future__ import annotations

import re

from skill_scanning_crawler.common.models import CandidateRepository

_GH_URL_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+?)(?:\.git)?(?:[/?#].*)?$"
)


def normalize_github_url(url: str) -> tuple[str, str] | None:
    """Return ``(owner, repo)`` extracted from a GitHub URL, or ``None``.

    Strips ``.git`` suffix, query strings, and fragments.
    Returns ``None`` for non-GitHub or malformed URLs.
    """
    m = _GH_URL_RE.match(url.strip())
    if not m:
        return None
    return m.group(1), m.group(2)


def make_canonical_id(owner: str, repo: str) -> str:
    return f"github:{owner.lower()}/{repo.lower()}"


def make_canonical_url(owner: str, repo: str) -> str:
    return f"https://github.com/{owner}/{repo}"


def deduplicate(
    candidates: list[CandidateRepository],
) -> list[CandidateRepository]:
    """Merge duplicates by ``canonical_id``, preserving all provenance.

    The first occurrence defines ``owner`` and ``repo`` casing.
    All ``discovery_sources`` and ``discovery_queries`` are merged and
    deduplicated while preserving insertion order.
    """
    seen: dict[str, CandidateRepository] = {}
    for cand in candidates:
        key = cand.canonical_id
        if key not in seen:
            seen[key] = cand
        else:
            existing = seen[key]
            for src in cand.discovery_sources:
                if src not in existing.discovery_sources:
                    existing.discovery_sources.append(src)
            for qry in cand.discovery_queries:
                if qry not in existing.discovery_queries:
                    existing.discovery_queries.append(qry)
    return list(seen.values())
