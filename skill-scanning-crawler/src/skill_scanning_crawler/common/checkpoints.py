"""Versioned checkpoint save/load for pipeline resume support.

Each stage saves a CheckpointEnvelope JSON file.  On ``--resume``, the
pipeline loads the file and validates that both ``checkpoint_version`` and
``config_hash`` match the current run before using the cached records.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from skill_scanning_crawler.common.exceptions import CheckpointError
from skill_scanning_crawler.common.models import CheckpointEnvelope

log = logging.getLogger(__name__)


def _checkpoint_path(output_dir: str, run_id: str, stage: str) -> Path:
    return Path(output_dir) / ".checkpoints" / run_id / f"{stage}.json"


def save_checkpoint(
    *,
    stage: str,
    run_id: str,
    config_hash: str,
    record_type: str,
    records: list[Any],  # JSON-serialisable dicts/primitives
    output_dir: str,
) -> Path:
    """Serialise ``records`` into a versioned checkpoint file."""
    envelope = CheckpointEnvelope(
        checkpoint_version=CheckpointEnvelope.CURRENT_VERSION,
        run_id=run_id,
        stage=stage,
        config_hash=config_hash,
        record_type=record_type,
        timestamp=datetime.now(UTC).isoformat(),
        record_count=len(records),
        records=records,
    )
    path = _checkpoint_path(output_dir, run_id, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(envelope), default=_json_default, indent=2),
        encoding="utf-8",
    )
    log.debug("Checkpoint saved: stage=%s records=%d path=%s", stage, len(records), path)
    return path


def load_checkpoint(
    *,
    stage: str,
    run_id: str,
    config_hash: str,
    output_dir: str,
) -> list[Any] | None:
    """Load and validate a checkpoint for ``stage``.

    Returns the raw record list on success, ``None`` if the file does not
    exist, or raises ``CheckpointError`` if the envelope is incompatible.
    """
    path = _checkpoint_path(output_dir, run_id, stage)
    if not path.exists():
        log.debug("No checkpoint found for stage=%s at %s", stage, path)
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise CheckpointError(f"Cannot read checkpoint {path}: {exc}") from exc

    version = raw.get("checkpoint_version")
    if version != CheckpointEnvelope.CURRENT_VERSION:
        raise CheckpointError(
            f"Incompatible checkpoint version {version!r} "
            f"(expected {CheckpointEnvelope.CURRENT_VERSION!r}) at {path}"
        )

    stored_hash = raw.get("config_hash")
    if stored_hash != config_hash:
        raise CheckpointError(
            f"Checkpoint config_hash mismatch at {path}: "
            f"stored={stored_hash!r}, current={config_hash!r}"
        )

    records: list[Any] = raw.get("records", [])
    log.info(
        "Checkpoint loaded: stage=%s records=%d path=%s",
        stage, len(records), path,
    )
    return records


def _json_default(obj: object) -> object:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
