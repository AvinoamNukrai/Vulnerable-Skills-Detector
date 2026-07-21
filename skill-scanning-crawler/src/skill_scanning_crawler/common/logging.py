"""Structured logging configuration for the crawler."""

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with a structured, human-readable formatter.

    Uses a consistent format that includes timestamp, level, logger name,
    and message. All output goes to stderr so stdout remains clean for
    piped manifest data.
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level!r}")

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Avoid duplicate handlers when called multiple times in tests.
    if not root.handlers:
        root.addHandler(handler)
    else:
        root.handlers.clear()
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger. Call after configure_logging()."""
    return logging.getLogger(name)
