"""CLI entry point for the skill-scanning-crawler.

Eight commands, one per pipeline stage, plus ``run`` to chain all stages.
Every command accepts --config, --run-id, --resume, and --dry-run.

Stage commands are fully wired: each command loads the required previous-stage
checkpoint automatically so stages can be run sequentially in separate
invocations.

Run-ID stability
----------------
If ``--run-id`` is not specified, the CLI reads/writes
``{output_dir}/.current_run_id``. The first ``discover`` invocation creates
the file; subsequent stage commands read it so that all checkpoints belong to
the same logical run. Pass ``--run-id`` explicitly to target a specific run.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Coroutine
from pathlib import Path
from typing import Annotated, Any

import typer

from skill_scanning_crawler.common.config import load_config
from skill_scanning_crawler.common.exceptions import ConfigError, PipelineError
from skill_scanning_crawler.common.logging import configure_logging
from skill_scanning_crawler.pipeline import Pipeline

log = logging.getLogger(__name__)

app = typer.Typer(
    name="skill-scanning-crawler",
    help="Discovery and dataset-acquisition pipeline for public agent skills.",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# Shared option types
# ---------------------------------------------------------------------------

ConfigOption = Annotated[
    Path,
    typer.Option("--config", "-c", help="Path to YAML config file.", show_default=False),
]
RunIdOption = Annotated[
    str | None,
    typer.Option(
        "--run-id",
        help=(
            "Use a specific run ID. "
            "If omitted, reads/creates data/.current_run_id so stage commands "
            "share the same logical run."
        ),
    ),
]
ResumeOption = Annotated[
    bool,
    typer.Option(
        "--resume",
        help="Skip this stage if a compatible checkpoint already exists.",
    ),
]
DryRunOption = Annotated[
    bool,
    typer.Option(
        "--dry-run",
        help="Validate config and show plan; make no network calls or file writes.",
    ),
]
LogLevelOption = Annotated[
    str,
    typer.Option("--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)."),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_run_id(
    run_id: str | None,
    output_dir: str,
    dry_run: bool = False,
) -> str:
    """Return a stable run ID for sequential stage commands.

    Reads ``{output_dir}/.current_run_id`` if ``--run-id`` is not given.
    Creates the file on the first invocation (unless dry_run=True).
    """
    if run_id:
        return run_id
    run_id_file = Path(output_dir) / ".current_run_id"
    if run_id_file.exists():
        existing = run_id_file.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    new_id = str(uuid.uuid4())
    if not dry_run:
        run_id_file.parent.mkdir(parents=True, exist_ok=True)
        run_id_file.write_text(new_id, encoding="utf-8")
        log.info("New run ID created: %s (saved to %s)", new_id, run_id_file)
    return new_id


def _make_pipeline(
    config_path: Path,
    run_id: str | None,
    resume: bool,
    dry_run: bool = False,
) -> Pipeline:
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(1) from exc
    resolved = _resolve_run_id(run_id, cfg.output.directory, dry_run=dry_run)
    return Pipeline(cfg, run_id=resolved, resume=resume)


def _run(coro: Coroutine[Any, Any, Any]) -> None:
    asyncio.run(coro)


def _run_stage(coro: Coroutine[Any, Any, Any]) -> None:
    """Run an async stage, catching PipelineError and printing a friendly message."""
    try:
        asyncio.run(coro)
    except PipelineError as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(1) from exc


# ---------------------------------------------------------------------------
# Stage commands
# ---------------------------------------------------------------------------


@app.command()
def discover(
    config: ConfigOption,
    run_id: RunIdOption = None,
    resume: ResumeOption = False,
    dry_run: DryRunOption = False,
    log_level: LogLevelOption = "INFO",
) -> None:
    """Stage 1 — collect candidate repositories from seed lists and GitHub search."""
    configure_logging(log_level)
    pipeline = _make_pipeline(config, run_id, resume, dry_run)
    if dry_run:
        _dry_run_plan(pipeline, stages=["discover"], resume=resume)
        return
    _run_stage(pipeline.run_discover())


@app.command()
def enrich(
    config: ConfigOption,
    run_id: RunIdOption = None,
    resume: ResumeOption = False,
    dry_run: DryRunOption = False,
    log_level: LogLevelOption = "INFO",
) -> None:
    """Stage 2 — fetch GitHub metadata for each candidate repository."""
    configure_logging(log_level)
    pipeline = _make_pipeline(config, run_id, resume, dry_run)
    if dry_run:
        _dry_run_plan(pipeline, stages=["enrich"], resume=resume)
        return
    _run_stage(pipeline.run_enrich())


@app.command()
def locate(
    config: ConfigOption,
    run_id: RunIdOption = None,
    resume: ResumeOption = False,
    dry_run: DryRunOption = False,
    log_level: LogLevelOption = "INFO",
) -> None:
    """Stage 3 — scan repository file trees and find SKILL.md files."""
    configure_logging(log_level)
    pipeline = _make_pipeline(config, run_id, resume, dry_run)
    if dry_run:
        _dry_run_plan(pipeline, stages=["locate"], resume=resume)
        return
    _run_stage(pipeline.run_locate_skills())


@app.command()
def validate(
    config: ConfigOption,
    run_id: RunIdOption = None,
    resume: ResumeOption = False,
    dry_run: DryRunOption = False,
    log_level: LogLevelOption = "INFO",
) -> None:
    """Stage 4 — fetch SKILL.md content and apply strict validation rules."""
    configure_logging(log_level)
    pipeline = _make_pipeline(config, run_id, resume, dry_run)
    if dry_run:
        _dry_run_plan(pipeline, stages=["validate"], resume=resume)
        return
    _run_stage(pipeline.run_validate())


@app.command()
def rank(
    config: ConfigOption,
    run_id: RunIdOption = None,
    resume: ResumeOption = False,
    dry_run: DryRunOption = False,
    log_level: LogLevelOption = "INFO",
) -> None:
    """Stage 5 — rank qualifying repositories and select the top-N."""
    configure_logging(log_level)
    pipeline = _make_pipeline(config, run_id, resume, dry_run)
    if dry_run:
        _dry_run_plan(pipeline, stages=["rank"], resume=resume)
        return
    _run_stage(pipeline.run_rank())


@app.command()
def snapshot(
    config: ConfigOption,
    run_id: RunIdOption = None,
    resume: ResumeOption = False,
    dry_run: DryRunOption = False,
    log_level: LogLevelOption = "INFO",
) -> None:
    """Stage 6 — download selected skill directories at pinned commit SHA."""
    configure_logging(log_level)
    pipeline = _make_pipeline(config, run_id, resume, dry_run)
    if dry_run:
        _dry_run_plan(pipeline, stages=["snapshot"], resume=resume)
        return
    _run_stage(pipeline.run_snapshot())


@app.command()
def export(
    config: ConfigOption,
    run_id: RunIdOption = None,
    resume: ResumeOption = False,
    dry_run: DryRunOption = False,
    log_level: LogLevelOption = "INFO",
) -> None:
    """Stage 7 — write JSONL manifests and JSON reports."""
    configure_logging(log_level)
    pipeline = _make_pipeline(config, run_id, resume, dry_run)
    if dry_run:
        _dry_run_plan(pipeline, stages=["export"], resume=resume)
        return
    _run_stage(pipeline.run_export())


@app.command(name="run")
def run_all(
    config: ConfigOption,
    run_id: RunIdOption = None,
    resume: ResumeOption = False,
    dry_run: DryRunOption = False,
    log_level: LogLevelOption = "INFO",
) -> None:
    """Chain all 7 stages end-to-end: discover, enrich, locate, validate, rank, snapshot, export."""
    configure_logging(log_level)
    pipeline = _make_pipeline(config, run_id, resume, dry_run)
    if dry_run:
        _dry_run_plan(
            pipeline,
            stages=["discover", "enrich", "locate", "validate", "rank", "snapshot", "export"],
            resume=resume,
        )
        return
    _run_stage(pipeline.run_all())


# ---------------------------------------------------------------------------
# Dry-run helper
# ---------------------------------------------------------------------------


def _dry_run_plan(pipeline: Pipeline, stages: list[str], resume: bool) -> None:
    cfg = pipeline.config
    typer.echo("=== DRY RUN — no network calls, no files written ===")
    typer.echo(f"run_id        : {pipeline.run_id}")
    typer.echo(f"config hash   : {cfg.compute_hash()[:16]}...")
    typer.echo(f"planned stages: {' -> '.join(stages)}")
    typer.echo(f"top_n         : {cfg.github.top_n_repositories}")
    typer.echo(f"include_forks : {cfg.github.include_forks}")
    typer.echo(f"include_archived: {cfg.github.include_archived}")
    typer.echo(f"output dir    : {cfg.output.directory}")
    typer.echo(f"manifests dir : {cfg.output.manifests_directory}")
    typer.echo(f"snapshots dir : {cfg.output.snapshots_directory}")
    typer.echo(f"reports dir   : {cfg.output.reports_directory}")
    typer.echo(f"resume        : {resume}")
    typer.echo("=== Dry run complete ===")


if __name__ == "__main__":
    app()
