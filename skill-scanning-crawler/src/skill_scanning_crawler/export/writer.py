"""JSONL manifest writer with optional schema validation.

Writes three manifest files:
  data/manifests/repositories.jsonl
  data/manifests/skills.jsonl
  data/manifests/rejected_candidates.jsonl

Each line is a valid JSON object (one record per line).
Records are sorted deterministically when config.output.deterministic_ordering is True.
All exported records are validated against config/output_schema.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import jsonschema

from skill_scanning_crawler.common.config import CrawlerConfig
from skill_scanning_crawler.common.exceptions import SchemaError
from skill_scanning_crawler.common.models import (
    RejectedCandidateRecord,
    RepositoryRecord,
    SkillRecord,
)

log = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parents[3] / "config" / "output_schema.json"


def _load_schema() -> dict[str, Any]:
    if _SCHEMA_PATH.exists():
        result: dict[str, Any] = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        return result
    log.warning("output_schema.json not found at %s; skipping schema validation", _SCHEMA_PATH)
    return {}


def _validate_record(record: dict[str, Any], schema: dict[str, Any], record_type: str) -> None:
    if not schema:
        return
    definitions = schema.get("definitions", schema.get("$defs", {}))
    type_schema = definitions.get(record_type)
    if not type_schema:
        return
    try:
        jsonschema.validate(record, type_schema)
    except jsonschema.ValidationError as exc:
        raise SchemaError(
            f"Record failed schema validation ({record_type}): {exc.message}"
        ) from exc


def write_manifests(
    repositories: list[RepositoryRecord],
    skills: list[SkillRecord],
    rejected: list[RejectedCandidateRecord],
    config: CrawlerConfig,
) -> dict[str, Path]:
    """Write all three JSONL manifests and return a path dict."""
    schema = _load_schema()
    manifests_dir = Path(config.output.manifests_directory)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    do_sort = config.output.deterministic_ordering

    # Populate skill_count from the actual exported skills. The enricher sets
    # skill_count=0 as a placeholder (the count isn't known until skills are
    # located, validated, and downloaded), so we derive it here where both the
    # repository and skill records are available.
    skills_per_repo: dict[str, int] = {}
    for s in skills:
        skills_per_repo[s.repository_id] = skills_per_repo.get(s.repository_id, 0) + 1
    repositories = [
        repo.model_copy(update={"skill_count": skills_per_repo.get(repo.repository_id, 0)})
        for repo in repositories
    ]

    repo_path = _write_jsonl(
        records=repositories,
        sort_key=lambda r: r.repository_id if do_sort else "",
        path=manifests_dir / "repositories.jsonl",
        schema=schema,
        schema_type="RepositoryRecord",
    )
    skills_path = _write_jsonl(
        records=skills,
        sort_key=lambda r: r.skill_id if do_sort else "",
        path=manifests_dir / "skills.jsonl",
        schema=schema,
        schema_type="SkillRecord",
    )
    rejected_path = _write_jsonl(
        records=rejected,
        sort_key=lambda r: r.candidate_id if do_sort else "",
        path=manifests_dir / "rejected_candidates.jsonl",
        schema=schema,
        schema_type="RejectedCandidateRecord",
    )

    log.info(
        "Manifests written: repos=%d skills=%d rejected=%d dir=%s",
        len(repositories), len(skills), len(rejected), manifests_dir,
    )
    return {
        "repositories": repo_path,
        "skills": skills_path,
        "rejected_candidates": rejected_path,
    }


def _write_jsonl(
    records: list[Any],
    sort_key: Any,
    path: Path,
    schema: dict[str, Any],
    schema_type: str,
) -> Path:
    if sort_key:
        records = sorted(records, key=sort_key)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            d = record.model_dump(mode="json")
            _validate_record(d, schema, schema_type)
            fh.write(json.dumps(d) + "\n")
    log.debug("Wrote %d records to %s", len(records), path)
    return path
