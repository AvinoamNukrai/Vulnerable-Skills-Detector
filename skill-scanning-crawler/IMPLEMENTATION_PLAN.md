# Implementation Plan: Skill Scanning Crawler

**Status: APPROVED FOR IMPLEMENTATION**

---

## 1. Project Goal

This project builds a reproducible data-acquisition pipeline that discovers public GitHub repositories containing agent skill packages, validates each candidate against a strict structural policy, freezes confirmed skills at an exact commit SHA, downloads their contents, and exports a clean, schema-validated dataset that vulnerability scanners can immediately consume in Part 2. The crawler never executes downloaded code and never classifies skills as malicious.

---

## 2. v1 Scope

| Axis | Constraint |
|---|---|
| Platform | GitHub only |
| Skill format | Strict `SKILL.md` with YAML frontmatter (`name` + `description` required) |
| Discovery sources | Seed lists (live-fetched, cached), GitHub code search, GitHub repo search |
| Ranking | Top-50 qualifying repositories by stars (non-fork, non-archived, ≥1 valid skill) |
| Snapshot export | Full valid skill directories at pinned commit SHA |
| Reproducibility | Commit SHA, content hash, `run_id`, `dataset_version`, and provenance on every record |
| Lenient skills | Recorded as rejected; excluded from primary export |
| Vulnerability scanning | Out of scope |
| Code execution | Never — not during validation, download, or export |
| MCP server | Documented, not implemented |

---

## 3. Internal Model Lifecycle

Models flow linearly through the pipeline. No stage creates a later-stage model; no stage skips a model.

```
Discovery
  CandidateRepository      ← discovered URL + provenance; deduplication occurs here

Enrichment
  RepositoryRecord         ← GitHub metadata, commit SHA, stars, fork/archived flags

Skill Location
  SkillCandidate           ← one per SKILL.md found in tree; path + commit SHA; no content yet

Validation
  ValidatedSkillCandidate  ← SKILL.md content fetched; strict classifier applied;
                             preliminary size check using tree metadata;
                             status is valid_standard | valid_lenient

Ranking
  RepositoryRecord         ← selected_for_export flag set on top-50 qualifying repos

Snapshot Download
  SnapshotResult           ← internal intermediate: downloaded files, excluded files,
                             per-file and directory size enforcement applied,
                             content hash computed from actual bytes on disk
  → SkillRecord            ← final exported record; only created after successful snapshot
  → RejectedCandidateRecord ← created for download failures or incomplete critical files

Export
  JSONL manifests + JSON reports
```

### Exported Pydantic models (manifest records)

These are the only models written to `data/manifests/`.

- `RepositoryRecord` — defined in `DATA_CONTRACT.md`; includes `selected_for_export`
- `SkillRecord` — defined in `DATA_CONTRACT.md`; extended with `snapshot_complete` and `excluded_files`
- `RejectedCandidateRecord` — defined in `DATA_CONTRACT.md`

### Internal dataclasses (never written to manifests)

- `CandidateRepository` — discovery output
- `SkillCandidate` — locator output; no validation yet
- `ValidatedSkillCandidate` — validator output; carries `validation_status`, `skill_md_content`
- `SnapshotResult` — snapshot-stage intermediate; carries `downloaded_files`, `excluded_files`, `content_hash`
- `ExcludedFile` — `path: str`, `reason: str` (`binary | oversized | unsafe_path | download_failed`)

### `SkillRecord` additions (requires updating `DATA_CONTRACT.md` and `config/output_schema.json`)

Two fields added to `SkillRecord` beyond the current schema:

| Field | Type | Description |
|---|---|---|
| `snapshot_complete` | `bool` | `True` if no files were excluded from the snapshot |
| `excluded_files` | `list[dict]` | Each entry: `{"path": "...", "reason": "..."}` |

These additions must be applied to `DATA_CONTRACT.md` and `config/output_schema.json` in Milestone 1.

---

## 4. Python Package Structure

```text
src/skill_scanning_crawler/
├── __init__.py
├── __main__.py              ← typer CLI; 8 commands
├── pipeline.py              ← Pipeline class; 8 stage methods + run_all
│
├── common/
│   ├── __init__.py
│   ├── config.py            ← load_config(path) → CrawlerConfig dataclass
│   ├── models.py            ← all Pydantic exported models + internal dataclasses
│   ├── enums.py             ← ValidationStatus, Platform, DiscoverySource
│   ├── exceptions.py        ← PipelineError, RateLimitError, DownloadError,
│   │                           ValidationError, ConfigError, CheckpointError
│   └── logging.py           ← configure_logging(level) → structured JSON formatter
│
├── github_client/
│   ├── __init__.py
│   ├── auth.py              ← get_token() from GITHUB_TOKEN env var only
│   ├── client.py            ← async GitHubClient; bounded concurrency; all API methods
│   ├── rate_limiter.py      ← per-category asyncio.Semaphore; backoff + jitter; Retry-After
│   └── cache.py             ← RequestCache (diskcache); stable cache keys
│
├── discovery/
│   ├── __init__.py
│   ├── seed_collector.py    ← live HTTP fetch + persistent cache + raw snapshot save;
│   │                           local_path fallback for offline/tests
│   ├── code_search_collector.py
│   ├── repo_search_collector.py
│   ├── candidate_normalizer.py  ← URL → github:owner/repo; repository deduplication here
│   └── candidate_store.py       ← in-memory + checkpoint-persistent registry
│
├── metadata/
│   ├── __init__.py
│   └── enricher.py          ← CandidateRepository → RepositoryRecord via GitHub API
│
├── locator/
│   ├── __init__.py
│   ├── tree_scanner.py      ← GitHub tree API at pinned SHA; find exact SKILL.md paths
│   └── skill_locator.py     ← tree paths → list[SkillCandidate]
│
├── validation/
│   ├── __init__.py
│   ├── frontmatter.py       ← parse YAML frontmatter from text; no I/O; no execution
│   ├── path_heuristics.py   ← doc-only / example-only detection
│   ├── size_checker.py      ← preliminary size check from tree metadata
│   └── validator.py         ← SkillCandidate → ValidatedSkillCandidate or RejectedCandidateRecord
│
├── ranking/
│   ├── __init__.py
│   └── ranker.py            ← rank qualifying repos; select top-N; report shortfall
│
├── download/
│   ├── __init__.py
│   ├── path_safety.py       ← reject traversal; normalize; refuse symlinks outside root
│   ├── file_filter.py       ← binary detection; per-file size enforcement
│   └── downloader.py        ← ValidatedSkillCandidate → SnapshotResult;
│                               final per-file + directory enforcement;
│                               records every excluded file + reason
│
├── export/
│   ├── __init__.py
│   ├── jsonl_writer.py      ← atomic JSONL writer; deterministic sort
│   └── schema_validator.py  ← validate each record against config/output_schema.json
│
└── reports/
    ├── __init__.py
    ├── discovery_summary.py  ← data/reports/discovery_summary.json
    └── dataset_statistics.py ← data/reports/dataset_statistics.json
```

Test layout:

```text
tests/
├── conftest.py                  ← shared fixtures; pytest marker registration
├── fixtures/
│   ├── skills/                  ← SKILL.md fixture files (valid, invalid, edge cases)
│   ├── github_responses/        ← mocked GitHub API JSON responses
│   └── seed_lists/              ← local seed list YAML and HTML fixtures
├── integration/                 ← live-GitHub tests; excluded from default runs
│   └── test_live_crawl.py
├── test_common/
├── test_github_client/
├── test_discovery/
├── test_metadata/
├── test_locator/
├── test_validation/
├── test_ranking/
├── test_download/
├── test_export/
└── test_reports/
```

---

## 5. Pipeline Stage Responsibilities

| Stage | Method | Input | Output |
|---|---|---|---|
| 1 | `run_discover` | `CrawlerConfig` | `list[CandidateRepository]` |
| 2 | `run_enrich` | `list[CandidateRepository]` | `list[RepositoryRecord]` + `list[RejectedCandidateRecord]` (unavailable) |
| 3 | `run_locate_skills` | `list[RepositoryRecord]` | `list[SkillCandidate]` |
| 4 | `run_validate` | `list[SkillCandidate]` | `list[ValidatedSkillCandidate]` + `list[RejectedCandidateRecord]` |
| 5 | `run_rank` | `list[RepositoryRecord]`, `list[ValidatedSkillCandidate]` | `list[RepositoryRecord]` (with `selected_for_export`) |
| 6 | `run_snapshot` | `list[RepositoryRecord]` (selected), `list[ValidatedSkillCandidate]` | `list[SkillRecord]` + `list[RejectedCandidateRecord]` (download failures) |
| 7 | `run_export` | all three manifest record lists | JSONL files + JSON reports on disk |
| — | `run_all` | `CrawlerConfig` | chains stages 1–7 |

**Deduplication placement:**

- Repository deduplication occurs during discovery normalization (`candidate_normalizer.py`). Same `github:owner/repo` from multiple sources is merged into one `CandidateRepository` with combined provenance before enrichment.
- Exact skill-content duplicate detection occurs after snapshot hashing. `SkillRecord.content_hash` identifies identical snapshots; duplicates are flagged in dataset statistics but not removed from the export.

---

## 6. CLI Commands

| Command | Stage method | Description |
|---|---|---|
| `discover` | `run_discover` | Seed list + GitHub search; write checkpoint |
| `enrich` | `run_enrich` | Fetch repo metadata; write checkpoint |
| `locate` | `run_locate_skills` | Tree scan → SkillCandidates; write checkpoint |
| `validate` | `run_validate` | Classify candidates; write checkpoint |
| `rank` | `run_rank` | Select top-N repos; write checkpoint |
| `snapshot` | `run_snapshot` | Download skill directories; write checkpoint |
| `export` | `run_export` | Write JSONL manifests + reports |
| `run` | `run_all` | Chain all stages end-to-end |

Every command accepts `--config PATH` (required), `--resume` (load compatible checkpoint), and `--dry-run` (plan only).

---

## 7. Checkpoint Envelopes

Every checkpoint written to disk uses a versioned envelope. Incompatible checkpoints are never silently loaded.

```python
@dataclass
class CheckpointEnvelope:
    checkpoint_version: str   # incremented when envelope schema changes; current: "1"
    run_id: str               # UUID4; stable for the life of a pipeline run
    stage: str                # e.g. "discover", "validate"
    config_hash: str          # SHA-256 of the serialized active CrawlerConfig
    record_type: str          # e.g. "CandidateRepository", "ValidatedSkillCandidate"
    timestamp: str            # ISO-8601 UTC
    record_count: int
    records: list[Any]        # serialized stage output records
```

Checkpoints are written to `.cache/checkpoints/<run_id>/<stage>.json`.

---

## 8. `--resume` Semantics

When `--resume` is passed, the pipeline loads a stage checkpoint if and only if:

1. A checkpoint file exists for that stage.
2. `checkpoint_version` matches the current code's expected version.
3. `config_hash` matches the SHA-256 of the currently active config.

If any condition fails, the stage is re-run from scratch and the old checkpoint is overwritten. A mismatch is logged at WARNING level explaining which condition failed.

---

## 9. `--dry-run` Semantics

When `--dry-run` is passed, the pipeline:

1. Parses and type-validates the config file.
2. Logs planned stages in order.
3. Logs each discovery query and filter setting.
4. Logs planned output paths.
5. Inspects and reports existing checkpoints (stage, timestamp, record count, compatibility).
6. Makes **no network calls**.
7. Creates or modifies **no files**.
8. Exits 0 if config is valid; non-zero if config is invalid.

---

## 10. Top-N Selection Behavior

1. All discovered candidates are enriched and validated before ranking.
2. A repository qualifies for ranking if and only if: `is_fork = False`, `is_archived = False`, and it contains at least one `valid_standard` skill.
3. Qualifying repositories are sorted descending by `stars`; ties broken ascending by `repository_id`.
4. The top 50 are selected (`selected_for_export = True`); all others get `selected_for_export = False`.
5. If fewer than 50 repositories qualify, the pipeline selects all that do and reports the shortfall in `discovery_summary.json`. It never pads with invalid candidates.

---

## 11. Binary and Oversized File Handling

1. Every file considered during snapshot is evaluated individually.
2. Files excluded for any reason are recorded in `SnapshotResult.excluded_files` with a specific reason string: `binary`, `oversized`, `unsafe_path`, or `download_failed`.
3. `SkillRecord.excluded_files` carries this list; `SkillRecord.snapshot_complete` is `False` when any file is excluded.
4. If `SKILL.md` itself cannot be downloaded or is excluded → the skill is rejected entirely; a `RejectedCandidateRecord` is emitted from `run_snapshot` and no `SkillRecord` is created.
5. If only auxiliary files are excluded → a `SkillRecord` is created with `snapshot_complete = False`. Part 2 can choose whether to scan incomplete snapshots.
6. Files are never silently omitted. Every exclusion is logged and recorded.

---

## 12. Test Strategy

**Mandatory tests** (run on every `pytest` invocation, no network required):

- Use `respx` or `httpx.MockTransport` for all HTTP interactions.
- Use local fixture files for all file content.
- Must pass with no environment variables set.
- Run command: `python -m pytest tests/ -v` (default `addopts` excludes integration marker).

**Optional integration tests** (require live GitHub API access):

- Stored in `tests/integration/`.
- Decorated with `@pytest.mark.integration`.
- Auto-skipped when `GITHUB_TOKEN` is not set via `pytest.mark.skipif(not os.getenv("GITHUB_TOKEN"), ...)`.
- Run explicitly with: `python -m pytest tests/integration/ -m integration`.
- Never run as part of CI default.

`pyproject.toml` configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not integration'"
markers = [
  "integration: requires live GITHUB_TOKEN; skipped by default"
]
```

---

## 13. Milestones

### Milestone 0 — Package Skeleton

**Purpose:** Installable package, full directory layout, 8 CLI command stubs, typed config loader, structured logging, custom exception hierarchy. No network calls.

**Files to create or edit:**

| File | Action |
|---|---|
| `pyproject.toml` | Edit — add `diskcache`, `tenacity`; dev: `pytest-asyncio`, `respx` |
| `src/skill_scanning_crawler/__init__.py` | Create |
| `src/skill_scanning_crawler/__main__.py` | Create — 8 CLI stubs via `typer` |
| `src/skill_scanning_crawler/pipeline.py` | Create — `Pipeline` class; 8 method stubs raising `NotImplementedError` |
| `src/skill_scanning_crawler/common/config.py` | Create — `load_config(path: Path) -> CrawlerConfig` |
| `src/skill_scanning_crawler/common/enums.py` | Create — `ValidationStatus` (11 values), `Platform`, `DiscoverySource` |
| `src/skill_scanning_crawler/common/exceptions.py` | Create — `PipelineError`, `RateLimitError`, `DownloadError`, `ValidationError`, `ConfigError`, `CheckpointError` |
| `src/skill_scanning_crawler/common/logging.py` | Create — `configure_logging(level: str = "INFO") -> None` |
| All 9 sub-package `__init__.py` files | Create — empty |
| `tests/conftest.py` | Create — marker registration, `tmp_path`-based fixtures |
| `tests/fixtures/` | Create directory tree |
| `tests/test_common/test_config.py` | Create |

**Key functions/classes:**

- `CrawlerConfig` dataclass mirroring all sections of `config/discovery.example.yaml`
- `load_config(path: Path) -> CrawlerConfig` — raises `ConfigError` for missing or malformed files
- `configure_logging(level: str) -> None`
- Exception hierarchy rooted at `PipelineError`
- `Pipeline.__init__(config, client)` and 8 stub methods
- All 8 `typer` commands wired to matching `Pipeline` methods

**Mandatory tests:**

- `test_config.py`: round-trip parse of `config/discovery.example.yaml`; missing key raises `ConfigError`; extra key raises `ConfigError`

**Inspection:**

```powershell
pip install -e ".[dev]"
python -m skill_scanning_crawler --help
python -m pytest tests/test_common/ -v
```

---

### Milestone 1 — Data Models

**Purpose:** Define all exported Pydantic models and all internal dataclasses. Update `DATA_CONTRACT.md` and `config/output_schema.json` with the `snapshot_complete` and `excluded_files` additions.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/common/models.py` | Create — all models |
| `DATA_CONTRACT.md` | Edit — add `snapshot_complete`, `excluded_files` to `SkillRecord` |
| `config/output_schema.json` | Edit — add `snapshot_complete`, `excluded_files` to `SkillRecord` schema |
| `tests/fixtures/sample_repository_record.json` | Create |
| `tests/fixtures/sample_skill_record.json` | Create |
| `tests/fixtures/sample_rejected_candidate_record.json` | Create |
| `tests/test_common/test_models.py` | Create |

**Exported Pydantic models** (`model_config = ConfigDict(extra="forbid")`):

- `RepositoryRecord` — all fields from `DATA_CONTRACT.md`
- `SkillRecord` — all fields from `DATA_CONTRACT.md` plus `snapshot_complete: bool` and `excluded_files: list[dict]`
- `RejectedCandidateRecord` — all fields from `DATA_CONTRACT.md`

**Internal dataclasses:**

- `CandidateRepository` — `canonical_id`, `owner`, `repo`, `url`, `discovery_sources: list[str]`, `discovery_queries: list[str]`, `discovered_at: datetime`
- `SkillCandidate` — `repository_id`, `owner`, `repo`, `skill_path`, `skill_md_path`, `commit_sha`, `discovery_sources`, `discovery_queries`, `located_at: datetime`
- `ValidatedSkillCandidate` — extends `SkillCandidate` with `skill_md_content: str`, `validation_status: ValidationStatus`, `validation_reason: str`, `validated_at: datetime`
- `SnapshotResult` — `candidate: ValidatedSkillCandidate`, `local_root: Path`, `downloaded_files: list[str]`, `excluded_files: list[ExcludedFile]`, `total_size_bytes: int`, `content_hash: str`, `snapshot_complete: bool`
- `ExcludedFile` — `path: str`, `reason: str`
- `CheckpointEnvelope` — all fields from Section 7

**Mandatory tests:**

- All three Pydantic models instantiate from sample fixtures
- Missing required field raises `pydantic.ValidationError`
- Unknown extra field raises `pydantic.ValidationError`
- All 11 `ValidationStatus` enum values present
- JSON round-trip stable for all three Pydantic models
- JSON schema validation (via `jsonschema`) passes for each sample fixture against `config/output_schema.json`

**Inspection:**

```powershell
python -m pytest tests/test_common/ -v
```

---

### Milestone 2 — Validation Engine

**Purpose:** Pure deterministic logic that classifies a `SkillCandidate` (with fetched content) into `valid_standard` or a rejection status. No I/O, no network, no execution of any kind.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/validation/frontmatter.py` | Create |
| `src/skill_scanning_crawler/validation/path_heuristics.py` | Create |
| `src/skill_scanning_crawler/validation/size_checker.py` | Create |
| `src/skill_scanning_crawler/validation/validator.py` | Create |
| `tests/fixtures/skills/valid_standard/SKILL.md` | Create |
| `tests/fixtures/skills/missing_frontmatter/SKILL.md` | Create |
| `tests/fixtures/skills/malformed_yaml/SKILL.md` | Create |
| `tests/fixtures/skills/missing_name/SKILL.md` | Create |
| `tests/fixtures/skills/missing_description/SKILL.md` | Create |
| `tests/fixtures/skills/docs_path/SKILL.md` | Create |
| `tests/fixtures/skills/example_path/SKILL.md` | Create |
| `tests/test_validation/test_frontmatter.py` | Create |
| `tests/test_validation/test_path_heuristics.py` | Create |
| `tests/test_validation/test_validator.py` | Create |

**Key functions:**

- `parse_frontmatter(content: str) -> dict | None` — `None` if no `---` block; raises `MalformedFrontmatterError` (subclass of `ValidationError`) if YAML is syntactically invalid
- `is_documentation_path(path: str, indicators: list[str]) -> bool`
- `is_example_path(path: str, indicators: list[str]) -> bool`
- `preliminary_size_check(tree_file_sizes: dict[str, int], policy: SizePolicy) -> ValidationStatus | None` — uses tree metadata (not actual bytes); returns `too_large` or `None`
- `classify_skill(skill_md_content: str, skill_path: str, tree_file_sizes: dict[str, int], policy: ValidationPolicyConfig) -> tuple[ValidationStatus, str]` — pure function; returns status + human-readable reason

**Mandatory tests:**

- `test_frontmatter.py`: valid frontmatter parsed correctly; no delimiters → `None`; malformed YAML → exception; extra frontmatter fields ignored
- `test_path_heuristics.py`: `docs/SKILL.md` → doc flag; `examples/x/SKILL.md` → example flag; `skills/x/SKILL.md` → no flag
- `test_validator.py`: all 7 rejection fixtures produce correct status; valid fixture produces `valid_standard`; multi-skill scenario (two paths, one valid, one docs-only) handled independently

**Inspection:**

```powershell
python -m pytest tests/test_validation/ -v
```

---

### Milestone 3 — GitHub Client

**Purpose:** Async HTTP client with full rate-limit safety from day one: per-category bounded concurrency, exponential backoff with jitter, `Retry-After` handling, and persistent disk cache. The token is never logged.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/github_client/auth.py` | Create |
| `src/skill_scanning_crawler/github_client/rate_limiter.py` | Create |
| `src/skill_scanning_crawler/github_client/cache.py` | Create |
| `src/skill_scanning_crawler/github_client/client.py` | Create |
| `tests/test_github_client/test_auth.py` | Create |
| `tests/test_github_client/test_rate_limiter.py` | Create |
| `tests/test_github_client/test_client.py` | Create — all tests use `respx` |

**Key classes and methods:**

- `get_token() -> str` — `os.environ["GITHUB_TOKEN"]`; raises `ConfigError` if absent; value never logged
- `class RateLimiter`:
  - Per-category `asyncio.Semaphore`: `search` (2), `metadata` (8), `tree` (6), `download` (4) — limits from config
  - `async acquire(category: str) -> None`
  - `async handle_response(response: httpx.Response) -> None` — reads `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`; sleeps if 429; logs remaining count
- `class RequestCache` (diskcache backend):
  - Keys: `github:owner/repo` (metadata), `github:owner/repo@sha` (tree), `github:owner/repo@sha:path` (file content)
  - `get(key) -> Any | None`, `set(key, value, ttl) -> None`, `has(key) -> bool`
- `class GitHubClient` (async context manager):
  - `async search_code(query: str, page: int = 1) -> list[dict]`
  - `async search_repos(query: str, page: int = 1) -> list[dict]`
  - `async get_repo(owner: str, repo: str) -> dict`
  - `async get_default_branch_sha(owner: str, repo: str, branch: str) -> str`
  - `async get_tree(owner: str, repo: str, sha: str, recursive: bool = True) -> list[dict]`
  - `async get_file_content(owner: str, repo: str, path: str, ref: str) -> str`

**Mandatory tests (all mocked with `respx`):**

- `test_auth.py`: token from env; absent token raises `ConfigError`; token value absent from captured log output (use `caplog`)
- `test_rate_limiter.py`: concurrency cap enforced; `Retry-After` produces correct sleep; backoff intervals computed correctly
- `test_client.py`: successful response parsed; 429 → sleep → retry → success; 500 → retry → eventual `RateLimitError`; cache hit → no HTTP call; token absent from log output

**Safe token setup (documented here, never in chat):**

```powershell
# Set for current PowerShell session only
$env:GITHUB_TOKEN = (Read-Host "GitHub PAT")
# Reference: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
```

**Inspection:**

```powershell
python -m pytest tests/test_github_client/ -v
```

---

### Milestone 4 — Discovery → `run_discover`

**Purpose:** Collect candidate repositories from three sources. Repository deduplication by canonical `github:owner/repo` identity happens here, before enrichment. Seed lists are fetched live with persistent caching; local fixture files are supported for offline runs and tests.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/discovery/seed_collector.py` | Create |
| `src/skill_scanning_crawler/discovery/code_search_collector.py` | Create |
| `src/skill_scanning_crawler/discovery/repo_search_collector.py` | Create |
| `src/skill_scanning_crawler/discovery/candidate_normalizer.py` | Create |
| `src/skill_scanning_crawler/discovery/candidate_store.py` | Create |
| `tests/fixtures/seed_lists/sample_seed_list.yaml` | Create |
| `tests/test_discovery/test_seed_collector.py` | Create |
| `tests/test_discovery/test_candidate_normalizer.py` | Create |
| `tests/test_discovery/test_candidate_store.py` | Create |

**Seed collector design:**

```
Per seed entry in config:
  if local_path set → read local file (offline / test mode)
  else → HTTP GET seed URL
       → cache response to .cache/seed-lists/<name>.raw
       → save dated raw snapshot to .cache/seed-lists/snapshots/<name>-<YYYY-MM-DD>.raw
  → parse GitHub repo URLs from content
  → normalize each → CandidateRepository
```

**Key functions/classes:**

- `normalize_github_url(url: str) -> str` — canonical `github:owner/repo`; raises `ConfigError` on non-GitHub input
- `async fetch_seed_list(seed: SeedConfig, http_client: httpx.AsyncClient, cache: RequestCache) -> list[CandidateRepository]`
- `async collect_from_code_search(queries: list[QueryConfig], client: GitHubClient) -> list[CandidateRepository]`
- `async collect_from_repo_search(queries: list[QueryConfig], client: GitHubClient) -> list[CandidateRepository]`
- `class CandidateStore`: `add(c: CandidateRepository) -> None` (merge if duplicate), `get_all() -> list[CandidateRepository]`, `save_checkpoint(path: Path) -> None`, `load_checkpoint(path: Path) -> None`

**Mandatory tests:**

- `test_seed_collector.py`: local fixture path → parsed; mocked HTTP fetch → parsed and cache written; second call → cache hit, no HTTP; two seeds produce distinct candidates
- `test_candidate_normalizer.py`: `https://github.com/foo/bar` → `github:foo/bar`; trailing slash stripped; non-GitHub URL raises; same repo from two sources → one record with merged sources
- `test_candidate_store.py`: add and retrieve; duplicate merges `discovery_sources`; checkpoint round-trip

**Inspection:**

```powershell
python -m pytest tests/test_discovery/ -v
python -m skill_scanning_crawler discover --config config/discovery.example.yaml --dry-run
```

---

### Milestone 5 — Metadata Enrichment → `run_enrich`

**Purpose:** Fetch repository-level metadata for every `CandidateRepository`, producing a fully populated `RepositoryRecord` with commit SHA, stars, archived/fork flags, license, topics, and size.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/metadata/enricher.py` | Create |
| `tests/fixtures/github_responses/repo_response.json` | Create |
| `tests/fixtures/github_responses/repo_404.json` | Create |
| `tests/test_metadata/test_enricher.py` | Create |

**Key functions:**

- `async enrich_repository(candidate: CandidateRepository, client: GitHubClient) -> RepositoryRecord | RejectedCandidateRecord` — 404/403 → `RejectedCandidateRecord(rejection_status="repository_unavailable")`
- `async enrich_batch(candidates: list[CandidateRepository], client: GitHubClient) -> tuple[list[RepositoryRecord], list[RejectedCandidateRecord]]` — bounded by `metadata` semaphore

**Mandatory tests:**

- Successful enrichment from `repo_response.json` fixture produces fully populated `RepositoryRecord`
- 404 response produces `RejectedCandidateRecord` with `repository_unavailable`
- `is_archived=True` and `is_fork=True` flags set correctly

**Inspection:**

```powershell
python -m pytest tests/test_metadata/ -v
python -m skill_scanning_crawler enrich --config config/discovery.example.yaml --dry-run
```

---

### Milestone 6 — Skill Location → `run_locate_skills`

**Purpose:** Scan each repository's file tree at its pinned commit SHA. Find every file named exactly `SKILL.md` (case-sensitive, no variants). Produce one `SkillCandidate` per skill directory found. This stage produces no validation results.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/locator/tree_scanner.py` | Create |
| `src/skill_scanning_crawler/locator/skill_locator.py` | Create |
| `tests/fixtures/github_responses/tree_multi_skill.json` | Create |
| `tests/fixtures/github_responses/tree_empty.json` | Create |
| `tests/fixtures/github_responses/tree_no_skill_md.json` | Create |
| `tests/test_locator/test_tree_scanner.py` | Create |
| `tests/test_locator/test_skill_locator.py` | Create |

**Key functions:**

- `async scan_tree(owner: str, repo: str, sha: str, client: GitHubClient) -> list[dict]` — returns raw tree entries where `path.endswith("/SKILL.md")` and `name == "SKILL.md"` exactly
- `locate_skill_directories(tree_entries: list[dict]) -> list[str]` — pure; returns parent dirs; e.g. `skills/pdf/SKILL.md` → `skills/pdf`; root `SKILL.md` → `""`
- `build_skill_candidates(repo: RepositoryRecord, skill_dirs: list[str], tree_entries: list[dict]) -> list[SkillCandidate]` — attaches `tree_file_sizes` dict for use by the preliminary size checker in validation

**Mandatory tests:**

- Three `SKILL.md` entries in tree → three `SkillCandidate` records
- `skill.md`, `SKILL.MD`, `SKILL.md.bak` → not matched (case-sensitive)
- Empty tree → empty list
- Tree without any `SKILL.md` → empty list
- Root-level `SKILL.md` → `skill_path = ""`

**Inspection:**

```powershell
python -m pytest tests/test_locator/ -v
python -m skill_scanning_crawler locate --config config/discovery.example.yaml --dry-run
```

---

### Milestone 7 — Validation Pipeline → `run_validate`

**Purpose:** Wire the validation engine (Milestone 2) into the live pipeline. Fetch `SKILL.md` content for each `SkillCandidate` via the GitHub client. Apply the strict classifier. Emit `ValidatedSkillCandidate` or `RejectedCandidateRecord`. No `SkillRecord` objects are created here.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/validation/validator.py` | Edit — add `validate_batch()` |
| `tests/test_validation/test_batch_validator.py` | Create |

**Key functions:**

- `async fetch_and_validate(candidate: SkillCandidate, client: GitHubClient, policy: ValidationPolicyConfig) -> ValidatedSkillCandidate | RejectedCandidateRecord` — fetches content; calls `classify_skill()`; 404 on fetch → `repository_unavailable`
- `async validate_batch(candidates: list[SkillCandidate], client: GitHubClient, policy: ValidationPolicyConfig) -> tuple[list[ValidatedSkillCandidate], list[RejectedCandidateRecord]]`

**Mandatory tests:**

- Mocked client returns valid `SKILL.md` → `ValidatedSkillCandidate(validation_status="valid_standard")`
- Mocked client returns content with missing `name` → `RejectedCandidateRecord(rejection_status="invalid_missing_name")`
- Mocked client returns 404 → `RejectedCandidateRecord(rejection_status="repository_unavailable")`
- No `SkillRecord` is created in this stage

**Inspection:**

```powershell
python -m pytest tests/test_validation/ -v
python -m skill_scanning_crawler validate --config config/discovery.example.yaml --dry-run
```

---

### Milestone 8 — Ranking → `run_rank`

**Purpose:** Pure ranking stage. Select the top-50 qualifying repositories. Report shortfalls honestly. Never pad.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/ranking/ranker.py` | Create |
| `tests/test_ranking/test_ranker.py` | Create |

**Key functions:**

- `rank_repositories(repos: list[RepositoryRecord], validated: list[ValidatedSkillCandidate], top_n: int, exclude_forks: bool, exclude_archived: bool) -> tuple[list[RepositoryRecord], int]` — returns `(ranked_with_flags, shortfall_count)`; qualifies only repos with ≥1 `ValidatedSkillCandidate`; sorts descending by `stars`, ascending by `repository_id` on tie
- `mark_selected(repos: list[RepositoryRecord], selected_ids: set[str]) -> list[RepositoryRecord]` — sets `selected_for_export` on all records

**Mandatory tests (pure functions — no mocking needed):**

- Top-3 from 10 → correct 3 selected
- Archived repo excluded even with highest stars
- Fork excluded when `exclude_forks=True`
- Repo with zero valid skills excluded
- Tie broken ascending by `repository_id`
- `selected_for_export=True` only on selected repos; `False` on all others
- Fewer than top-N qualify → all that qualify selected; shortfall count returned correctly

**Inspection:**

```powershell
python -m pytest tests/test_ranking/ -v
python -m skill_scanning_crawler rank --config config/discovery.example.yaml --dry-run
```

---

### Milestone 9 — Snapshot Download → `run_snapshot`

**Purpose:** Download full valid skill directories at pinned commit SHA. Enforce path safety and per-file and directory-size limits (final enforcement — not preliminary). Record every excluded file. Produce `SkillRecord` on success or `RejectedCandidateRecord` on failure. Compute `content_hash` from bytes actually written to disk.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/download/path_safety.py` | Create |
| `src/skill_scanning_crawler/download/file_filter.py` | Create |
| `src/skill_scanning_crawler/download/downloader.py` | Create |
| `tests/test_download/test_path_safety.py` | Create |
| `tests/test_download/test_file_filter.py` | Create |
| `tests/test_download/test_downloader.py` | Create |

**Key functions:**

- `is_safe_relative_path(path: str, root: Path) -> bool` — rejects `..`, absolute, and paths resolving outside root
- `is_binary_file(filename: str, sample: bytes) -> bool` — null bytes + known binary extensions
- `exceeds_file_size(size_bytes: int, limit_mb: float) -> bool`
- `class SnapshotDownloader`:
  - `async download_skill(candidate: ValidatedSkillCandidate, client: GitHubClient, output_root: Path, policy: ValidationPolicyConfig) -> SnapshotResult`
  - Fetches subtree for `candidate.skill_path` at `candidate.commit_sha`
  - Per file: check path safety → check binary → check size → download → write
  - Records each exclusion in `SnapshotResult.excluded_files` with exact reason
  - Computes `content_hash` from bytes of successfully written files (sorted by normalized relative path)
  - If `SKILL.md` excluded → raises `DownloadError` (caller emits `RejectedCandidateRecord`)
- `snapshot_to_skill_record(result: SnapshotResult, repo: RepositoryRecord) -> SkillRecord`

**Security invariants (enforced, tested):**

- No file written outside `output_root / repository_id / skill_path`
- No symlink followed outside snapshot root
- `content_hash` computed from bytes actually written, never from API metadata

**Mandatory tests:**

- `test_path_safety.py`: safe path accepted; `../../etc/passwd` rejected; absolute path rejected
- `test_file_filter.py`: `.py` text file → not binary; bytes with null → binary; `.exe` → binary; file over limit detected
- `test_downloader.py`: successful download → correct `SnapshotResult` (files, sizes, hash); unsafe path → recorded in `excluded_files`, not written; binary file → recorded in `excluded_files`; oversized file → recorded; `SKILL.md` excluded → `DownloadError`; `snapshot_complete=False` when any exclusion; output never written outside `output_root`

**Inspection:**

```powershell
python -m pytest tests/test_download/ -v
python -m skill_scanning_crawler snapshot --config config/discovery.example.yaml --dry-run
```

---

### Milestone 10 — Export + Reports → `run_export`

**Purpose:** Write all three JSONL manifest files and both JSON reports. Validate every record against `config/output_schema.json` before writing. Sort records deterministically.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/export/jsonl_writer.py` | Create |
| `src/skill_scanning_crawler/export/schema_validator.py` | Create |
| `src/skill_scanning_crawler/reports/discovery_summary.py` | Create |
| `src/skill_scanning_crawler/reports/dataset_statistics.py` | Create |
| `tests/test_export/test_jsonl_writer.py` | Create |
| `tests/test_export/test_schema_validator.py` | Create |
| `tests/test_reports/test_discovery_summary.py` | Create |
| `tests/test_reports/test_dataset_statistics.py` | Create |

**Key functions:**

- `class JsonlWriter`: `write_records(records: list[BaseModel], path: Path, sort_key: str) -> None` — validate each record against JSON schema before write; atomic write (temp file → rename); raises if any record is invalid
- `validate_jsonl_file(path: Path, record_type: str, schema: dict) -> list[str]` — returns violation strings; empty → valid
- `generate_discovery_summary(run_id: str, dataset_version: str, ...) -> dict` — counts, curated-rediscovery rate, per-source breakdown, top-N shortfall if any
- `generate_dataset_statistics(run_id: str, dataset_version: str, ...) -> dict` — counts, star distribution, file-type distribution, duplicate content-hash count, `snapshot_complete` rate, top-5 repos by stars

**`run_id` and `dataset_version`:**

- `run_id`: UUID4 generated once at `Pipeline` construction; propagated to all stages and both report files
- `dataset_version`: ISO date string (`YYYY-MM-DD`) of pipeline start; included in both report files
- Individual JSONL records do not include `run_id`; provenance lives in reports

**Mandatory tests:**

- `test_jsonl_writer.py`: deterministic sort; each line parses as valid JSON; round-trip stable; invalid record raises before any file is written; empty list → file with zero lines
- `test_schema_validator.py`: valid record passes; missing required field fails; invalid enum value fails
- `test_discovery_summary.py`: correct counts; `run_id` and `dataset_version` present; shortfall reported when < top-N qualify
- `test_dataset_statistics.py`: duplicate hash count; `snapshot_complete` rate; `run_id` and `dataset_version` present

**Inspection:**

```powershell
python -m pytest tests/test_export/ tests/test_reports/ -v
python -m skill_scanning_crawler export --config config/discovery.example.yaml --dry-run
python -m json.tool data\reports\dataset_statistics.json
```

---

### Milestone 11 — Pipeline Orchestration → `run_all`

**Purpose:** Fully implement `Pipeline`, all 8 CLI commands, checkpoint envelope save/load, `--resume` compatibility checks, and `--dry-run` plan output.

**Files to create or edit:**

| File | Action |
|---|---|
| `src/skill_scanning_crawler/pipeline.py` | Implement fully |
| `src/skill_scanning_crawler/__main__.py` | Implement all 8 commands fully |
| `tests/test_pipeline/test_pipeline.py` | Create — fully mocked client |
| `tests/test_pipeline/test_cli.py` | Create — `typer.testing.CliRunner` |

**`Pipeline` class:**

```python
class Pipeline:
    def __init__(self, config: CrawlerConfig, run_id: str | None = None) -> None
    # run_id generated here if not supplied; used for all checkpoints and reports

    async def run_discover(self) -> list[CandidateRepository]
    async def run_enrich(self, candidates: list[CandidateRepository]) -> tuple[list[RepositoryRecord], list[RejectedCandidateRecord]]
    async def run_locate_skills(self, repos: list[RepositoryRecord]) -> list[SkillCandidate]
    async def run_validate(self, candidates: list[SkillCandidate]) -> tuple[list[ValidatedSkillCandidate], list[RejectedCandidateRecord]]
    async def run_rank(self, repos: list[RepositoryRecord], validated: list[ValidatedSkillCandidate]) -> list[RepositoryRecord]
    async def run_snapshot(self, repos: list[RepositoryRecord], validated: list[ValidatedSkillCandidate]) -> tuple[list[SkillRecord], list[RejectedCandidateRecord]]
    async def run_export(self, repos: list[RepositoryRecord], skills: list[SkillRecord], rejected: list[RejectedCandidateRecord]) -> None
    async def run_all(self) -> None
```

**Checkpoint helpers:**

- `save_checkpoint(stage: str, records: Any, record_type: str, config_hash: str) -> None` — writes `CheckpointEnvelope` to `.cache/checkpoints/<run_id>/<stage>.json`
- `load_checkpoint(stage: str, config_hash: str) -> Any | None` — returns `None` if missing, version mismatch, or config-hash mismatch; logs reason at WARNING

**`--dry-run` implementation:**

1. Parse and validate config
2. Print planned stage sequence
3. Print each query, filter, top-N setting, output paths
4. Load and report existing checkpoints (stage, timestamp, record count, compatibility)
5. Print: "Dry run complete — no files written, no network calls made"
6. Exit 0 (invalid config → exit 1)

**`--resume` implementation:**

For each stage in sequence: attempt `load_checkpoint`; if compatible → use loaded data and skip re-run; if incompatible or missing → run stage normally.

**Mandatory tests:**

- `test_pipeline.py`: full `run_all` with mocked client → all 5 output files produced; checkpoint saved after each stage; `--resume` skips stage with compatible checkpoint; incompatible checkpoint (wrong config hash) → stage re-runs
- `test_cli.py` (CliRunner): each of 8 commands exits 0 with fully mocked pipeline; `--dry-run` produces no files; missing `--config` exits non-zero

**Inspection:**

```powershell
python -m pytest tests/ -v
# Step-by-step live run (GITHUB_TOKEN set in terminal, not chat):
python -m skill_scanning_crawler discover  --config config/discovery.example.yaml
python -m skill_scanning_crawler enrich    --config config/discovery.example.yaml
python -m skill_scanning_crawler locate    --config config/discovery.example.yaml
python -m skill_scanning_crawler validate  --config config/discovery.example.yaml
python -m skill_scanning_crawler rank      --config config/discovery.example.yaml
python -m skill_scanning_crawler snapshot  --config config/discovery.example.yaml
python -m skill_scanning_crawler export    --config config/discovery.example.yaml
# Or all at once:
python -m skill_scanning_crawler run       --config config/discovery.example.yaml
```

---

## 14. Dependency Order

```
M0 (Skeleton)
    └── M1 (Data Models)
            ├── M2 (Validation Engine)   ← pure logic; parallel with M3
            └── M3 (GitHub Client)       ← full async + rate limits + cache
                    ├── M4 (Discovery)
                    │       └── M5 (Enrich)
                    │               └── M6 (Locate Skills)
                    │                       └── M7 (Validate Pipeline ← feeds from M2)
                    │                               └── M8 (Rank)
                    │                                       └── M9 (Snapshot)
                    │                                               └── M10 (Export)
                    │                                                       └── M11 (Pipeline)
                    └── M2 feeds into M7
```

Critical path: M0 → M1 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10 → M11

M2 can be built in parallel with M3 immediately after M1.

---

## 15. Commands After Each Milestone

```powershell
pip install -e ".[dev]"
ruff check src/ tests/
mypy src/
python -m pytest tests/ -v          # addopts excludes integration by default
```

---

## 16. Risks and Assumptions

| # | Risk / Assumption | Severity | Mitigation |
|---|---|---|---|
| R1 | `SKILL.md` format is rare; GitHub search returns few real results | High | Seed lists are primary source; search augments; recall proxy in reports |
| R2 | Rate limits slow large crawls | Medium | Full rate-limit safety in M3 before first live run |
| R3 | Strict frontmatter requirements reject many real-world skills | Medium | All rejected recorded with reasons; lenient mode available via config |
| R4 | Large repositories cause download hangs or disk exhaustion | Medium | Preliminary size check in validation; final enforcement in snapshot |
| R5 | Path traversal in fetched file paths writes outside snapshot root | High | `path_safety.py` mandatory; all paths resolved inside `output_root` |
| R6 | Fewer than 50 repos qualify for top-N | Low | Reported honestly in summary; never padded |
| R7 | Seed list URLs change format or go offline | Medium | Persistent cache; raw snapshots saved; local fixture fallback |
| A1 | `GITHUB_TOKEN` is set in the terminal before running | — | `ConfigError` with clear message if absent |
| A2 | Python 3.11 available in dev environment | — | `pyproject.toml` pins `>=3.11` |
| A3 | `diskcache`, `tenacity`, `respx`, `pytest-asyncio` are acceptable | — | See Q2 |

---

## 17. Open Questions

| # | Question | Proposed default |
|---|---|---|
| Q1 | Top-50 **repositories** or top-50 **individual skills**? | Top-50 repositories; all valid skills from each selected repo are exported |
| Q2 | Are `diskcache`, `tenacity`, `respx`, `pytest-asyncio` acceptable additions? | Yes |
| Q4 | Should `repositories.jsonl` include all enriched candidates or only confirmed repos? | All enriched; `selected_for_export=False` for unconfirmed |
| Q7 | Flat `data/` or versioned `data/releases/YYYY-MM-DD/`? | Flat `data/`; `run_id` + `dataset_version` in reports for traceability |
| Q8 | Are seed list URLs HTML pages, YAML files, or something else? Needed to implement the seed parser correctly. | Unknown — needs your input |

---

## 18. v1 Complete Checklist

### Deliverable files

- [ ] `data/manifests/repositories.jsonl`
- [ ] `data/manifests/skills.jsonl`
- [ ] `data/manifests/rejected_candidates.jsonl`
- [ ] `data/snapshots/github__<owner>__<repo>/`
- [ ] `data/reports/discovery_summary.json` — includes `run_id`, `dataset_version`
- [ ] `data/reports/dataset_statistics.json` — includes `run_id`, `dataset_version`

### Pipeline compliance

- [ ] All 7 stages individually invocable via CLI (`locate`, `rank`, `snapshot` explicit)
- [ ] `run_validate` produces `ValidatedSkillCandidate`; never creates `SkillRecord`
- [ ] `run_snapshot` produces both `SkillRecord` and `RejectedCandidateRecord` for failures
- [ ] Repository deduplication in discovery normalization
- [ ] Skill content duplicate detection after snapshot hashing
- [ ] Every excluded file recorded with reason; `snapshot_complete` flag set

### Correctness

- [ ] Every `SkillRecord` has `commit_sha`, `content_hash`, `snapshot_complete`
- [ ] Every `RepositoryRecord` has `commit_sha` and `collected_at`
- [ ] Every `RejectedCandidateRecord` has `rejection_status` and `rejection_reason`
- [ ] No candidate silently discarded
- [ ] No downloaded code executed or imported
- [ ] `GITHUB_TOKEN` value never appears in any output file or log

### Checkpoint / resume

- [ ] Checkpoint envelope contains: `checkpoint_version`, `run_id`, `stage`, `config_hash`, `record_type`, `timestamp`, `record_count`, `records`
- [ ] `--resume` rejects incompatible checkpoints (version mismatch or config hash mismatch)
- [ ] `--dry-run` makes no network calls and writes no files

### Top-N behavior

- [ ] Only non-fork, non-archived repos with ≥1 valid skill qualify
- [ ] Shortfall reported in `discovery_summary.json` when < 50 qualify
- [ ] Invalid candidates never used to pad

### Schema compliance

- [ ] `repositories.jsonl` validates against `config/output_schema.json`
- [ ] `skills.jsonl` validates against `config/output_schema.json`
- [ ] `rejected_candidates.jsonl` validates against `config/output_schema.json`

### Tests

- [ ] `python -m pytest tests/ -v` passes (no network, no token required)
- [ ] Integration tests skipped automatically when `GITHUB_TOKEN` unset
- [ ] `ruff check src/ tests/` — zero errors
- [ ] `mypy src/` — zero errors

### Reproducibility

- [ ] Fixture-based test runs are bit-identical
- [ ] Live runs are deterministic except for volatile fields (`collected_at`, `stars`, upstream state)
- [ ] `run_id` present in both report files
- [ ] `dataset_version` present in both report files
- [ ] `content_hash` computed from bytes actually written to disk

### Documentation

- [ ] `DATA_CONTRACT.md` includes `snapshot_complete` and `excluded_files` on `SkillRecord`
- [ ] `config/output_schema.json` includes `snapshot_complete` and `excluded_files`
- [ ] `README.md` has working quickstart and safe token setup instructions
