"""Build a self-contained demo dataset for Part 2 handoff.

This script produces all required output files from synthetic but
schema-valid records, without calling the GitHub API.  It is the
fastest way to verify that the export pipeline is end-to-end correct.

Usage::

    python scripts/build_demo_dataset.py
    python scripts/build_demo_dataset.py --config config/offline_demo.yaml

The output lands in the ``data/`` directory configured by the YAML file.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

# Make sure the package is importable whether installed or editable
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from skill_scanning_crawler.common.config import load_config
from skill_scanning_crawler.common.enums import ValidationStatus
from skill_scanning_crawler.common.models import (
    RejectedCandidateRecord,
    RepositoryRecord,
    SkillRecord,
)
from skill_scanning_crawler.export.reports import write_reports
from skill_scanning_crawler.export.writer import write_manifests

_NOW = datetime.now(UTC).isoformat()

_REPOS: list[RepositoryRecord] = [
    RepositoryRecord(
        repository_id="github:anthropics/anthropic-quickstarts",
        platform="github",
        owner="anthropics",
        name="anthropic-quickstarts",
        full_name="anthropics/anthropic-quickstarts",
        url="https://github.com/anthropics/anthropic-quickstarts",
        description="Quickstart code examples for the Anthropic API.",
        stars=4200,
        forks=980,
        is_fork=False,
        is_archived=False,
        default_branch="main",
        commit_sha="abc1234def5678abc1234def5678abc1234def56",
        license="MIT",
        topics=["anthropic", "claude", "ai"],
        collected_at=_NOW,
        selected_for_export=True,
    ),
    RepositoryRecord(
        repository_id="github:getcursor/cursor",
        platform="github",
        owner="getcursor",
        name="cursor",
        full_name="getcursor/cursor",
        url="https://github.com/getcursor/cursor",
        description="The AI-first code editor.",
        stars=31000,
        forks=2100,
        is_fork=False,
        is_archived=False,
        default_branch="main",
        commit_sha="dead1234beef5678dead1234beef5678dead1234",
        license="MIT",
        topics=["cursor", "ai", "editor"],
        collected_at=_NOW,
        selected_for_export=True,
    ),
]

_SKILLS: list[SkillRecord] = [
    SkillRecord(
        skill_id=(
            "github:anthropics/anthropic-quickstarts"
            "@abc1234def5678abc1234def5678abc1234def56"
            "::computer-use-demo/SKILL.md"
        ),
        repository_id="github:anthropics/anthropic-quickstarts",
        platform="github",
        owner="anthropics",
        repo="anthropic-quickstarts",
        repository_url="https://github.com/anthropics/anthropic-quickstarts",
        skill_path="computer-use-demo/SKILL.md",
        skill_name="Computer Use Demo",
        description="Interactive Claude computer-use demonstration skill.",
        validation_status=ValidationStatus.VALID_STANDARD,
        commit_sha="abc1234def5678abc1234def5678abc1234def56",
        content_hash="sha256:aabbccdd" * 8,
        file_count=3,
        total_size_bytes=4096,
        files=["SKILL.md", "main.py", "README.md"],
        snapshot_path="data/snapshots/anthropics/anthropic-quickstarts/computer-use-demo",
        snapshot_complete=True,
        excluded_files=[],
        collected_at=_NOW,
    ),
    SkillRecord(
        skill_id=(
            "github:getcursor/cursor"
            "@dead1234beef5678dead1234beef5678dead1234"
            "::skills/coding/SKILL.md"
        ),
        repository_id="github:getcursor/cursor",
        platform="github",
        owner="getcursor",
        repo="cursor",
        repository_url="https://github.com/getcursor/cursor",
        skill_path="skills/coding/SKILL.md",
        skill_name="Cursor Coding Skill",
        description="AI-powered coding assistance skill for the Cursor editor.",
        validation_status=ValidationStatus.VALID_STANDARD,
        commit_sha="dead1234beef5678dead1234beef5678dead1234",
        content_hash="sha256:11223344" * 8,
        file_count=2,
        total_size_bytes=2048,
        files=["SKILL.md", "README.md"],
        snapshot_path="data/snapshots/getcursor/cursor/skills/coding",
        snapshot_complete=True,
        excluded_files=[],
        collected_at=_NOW,
    ),
]

_REJECTED: list[RejectedCandidateRecord] = [
    RejectedCandidateRecord(
        candidate_id="github:langchain-ai/langchain::SKILL.md",
        repository_id="github:langchain-ai/langchain",
        platform="github",
        owner="langchain-ai",
        repo="langchain",
        path="SKILL.md",
        rejection_status=ValidationStatus.INVALID_MISSING_NAME,
        rejection_reason="SKILL.md missing required frontmatter field 'name'",
        discovery_sources=["github_code_search"],
        discovery_queries=["filename:SKILL.md"],
        collected_at=_NOW,
    ),
    RejectedCandidateRecord(
        candidate_id="github:BuilderIO/builder::SKILL.md",
        repository_id="github:BuilderIO/builder",
        platform="github",
        owner="BuilderIO",
        repo="builder",
        path="SKILL.md",
        rejection_status=ValidationStatus.REPOSITORY_UNAVAILABLE,
        rejection_reason="Repository not found (404) or private",
        discovery_sources=["seed"],
        discovery_queries=["fixture-seed"],
        collected_at=_NOW,
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="config/offline_demo.yaml",
        help="Path to YAML config file (default: config/offline_demo.yaml)",
    )
    args = parser.parse_args()

    print(f"Loading config: {args.config}")
    cfg = load_config(Path(args.config))

    print(f"Output directory : {cfg.output.directory}")
    print(f"Manifests        : {cfg.output.manifests_directory}")
    print(f"Reports          : {cfg.output.reports_directory}")

    # Create snapshot directories for the synthetic skills
    for skill in _SKILLS:
        snap = Path(skill.snapshot_path)
        snap.mkdir(parents=True, exist_ok=True)
        skill_md = snap / "SKILL.md"
        if not skill_md.exists():
            skill_md.write_text(
                f"---\nname: {skill.skill_name}\ndescription: {skill.description}\n---\n"
                "# Skill\n\nSynthetic demo skill file for Part 2 handoff testing.\n"
            )

    write_manifests(_REPOS, _SKILLS, _REJECTED, cfg)
    write_reports(_REPOS, _SKILLS, _REJECTED, cfg, run_id="demo-dataset-v1")

    manifests = Path(cfg.output.manifests_directory)
    reports = Path(cfg.output.reports_directory)

    print("\nGenerated files:")
    for f in sorted(manifests.glob("*.jsonl")):
        lines = len(f.read_text().splitlines())
        print(f"  {f}  ({lines} lines)")
    for f in sorted(reports.glob("*.json")):
        print(f"  {f}")

    print("\nDone. data/ is ready for Part 2 handoff.")


if __name__ == "__main__":
    main()
