# AGENTS.md

This repository supports an MSc project component: building a crawler that discovers public agent-skill repositories and exports a reproducible dataset for later vulnerability scanning.

## Core mission

Build a GitHub-based discovery and acquisition pipeline that:

1. discovers candidate repositories containing agent skills,
2. validates skill directories,
3. ranks repositories by stars,
4. freezes exact versions by commit SHA,
5. downloads valid skill directories and auxiliary files,
6. exports manifests and snapshots as prepared input for Part 2.

The project does **not** implement vulnerability scanning.

## Read first

Before making architectural or implementation changes, read:

- `PROJECT_SCOPE.md`
- `DATA_CONTRACT.md`
- `CRAWLER_DESIGN.md`
- `VALIDATION_POLICY.md`
- `PART2_HANDOFF.md`

## Implementation principles

- Keep the crawler modular.
- Treat every downloaded repository as hostile.
- Never execute code from downloaded repositories.
- Never hardcode tokens or secrets.
- Prefer deterministic, reproducible outputs.
- Every exported record must include provenance.
- Every live repository snapshot must be pinned to a commit SHA.
- Rejected candidates must be recorded, not silently discarded.
- Changes to output schema must update `DATA_CONTRACT.md` and `config/output_schema.json`.

## Suggested module boundaries

```text
src/skill_scanning_crawler/
├── discovery/
├── github_client/
├── metadata/
├── validation/
├── deduplication/
├── download/
├── export/
├── reports/
└── common/
```

Avoid building a single large script.

## Security constraints

When handling public repositories:

- do not run install commands,
- do not import downloaded Python modules,
- do not execute shell scripts,
- do not follow arbitrary symlinks outside the snapshot root,
- enforce maximum file and repository sizes,
- ignore or quarantine large/binary files unless explicitly configured,
- store GitHub tokens only in environment variables.

## Testing expectations

Add tests for:

- GitHub URL normalization,
- query parsing/config loading,
- `SKILL.md` path detection,
- YAML frontmatter parsing,
- validation status classification,
- content hashing,
- top-N ranking,
- manifest writing,
- schema validation,
- rejected-candidate recording.

## Preferred Python style

- Python 3.11+
- type hints required for public functions,
- `pydantic` models for public data records,
- small pure functions where possible,
- explicit error types for recoverable pipeline failures,
- structured logging,
- no global mutable state for crawler configuration.

## Deliverable definition

A successful v1 deliverable can produce:

```text
data/manifests/repositories.jsonl
data/manifests/skills.jsonl
data/manifests/rejected_candidates.jsonl
data/snapshots/
data/reports/discovery_summary.json
data/reports/dataset_statistics.json
```

Part 2 should be able to run vulnerability scanners against `data/snapshots/` using `skills.jsonl` as the authoritative index.
