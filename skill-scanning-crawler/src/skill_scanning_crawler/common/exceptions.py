"""Typed exception hierarchy for recoverable pipeline failures."""


class PipelineError(Exception):
    """Base class for all crawler pipeline errors."""


class ConfigError(PipelineError):
    """Raised when configuration is missing, malformed, or invalid."""


class RateLimitError(PipelineError):
    """Raised when the GitHub API rate limit is exhausted after all retries."""


class DownloadError(PipelineError):
    """Raised when a required file cannot be downloaded (e.g. SKILL.md missing)."""


class ValidationError(PipelineError):
    """Raised when a validation rule encounters an unrecoverable error."""


class MalformedFrontmatterError(ValidationError):
    """Raised when a SKILL.md file contains syntactically invalid YAML frontmatter."""


class GitHubClientError(PipelineError):
    """Raised for unrecoverable GitHub API errors (non-429/non-5xx)."""


class CheckpointError(PipelineError):
    """Raised when a checkpoint cannot be read, written, or is incompatible."""


class SchemaError(PipelineError):
    """Raised when an output record fails JSON schema validation."""
