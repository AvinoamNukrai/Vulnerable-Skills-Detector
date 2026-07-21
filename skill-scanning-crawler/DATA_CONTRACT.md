# Data Contract

This document defines the handoff between Part 1, the crawler, and Part 2, the vulnerability scanner evaluation.

Part 2 should treat the exported manifest files as authoritative.

## Manifest files

```text
data/manifests/
├── repositories.jsonl
├── skills.jsonl
└── rejected_candidates.jsonl
```

Each file is newline-delimited JSON. Every line must be a complete JSON object.

## RepositoryRecord

Represents a public repository that was discovered, enriched, and possibly selected.

Required fields:

```json
{
  "repository_id": "github__owner__repo",
  "platform": "github",
  "owner": "owner",
  "name": "repo",
  "full_name": "owner/repo",
  "url": "https://github.com/owner/repo",
  "description": "Repository description or null",
  "stars": 1234,
  "forks": 52,
  "is_fork": false,
  "is_archived": false,
  "default_branch": "main",
  "commit_sha": "abc123",
  "license": "MIT",
  "topics": ["agent-skills"],
  "repository_size_kb": 12345,
  "discovery_sources": ["github_code_search"],
  "discovery_queries": ["filename:SKILL.md"],
  "skill_count": 4,
  "selected_for_export": true,
  "collected_at": "2026-07-16T00:00:00Z"
}
```

## SkillRecord

Represents one validated skill directory.

Required fields:

```json
{
  "skill_id": "github__owner__repo__skills__pdf-analyzer",
  "repository_id": "github__owner__repo",
  "platform": "github",
  "owner": "owner",
  "repo": "repo",
  "repository_url": "https://github.com/owner/repo",
  "skill_path": "skills/pdf-analyzer",
  "skill_name": "pdf-analyzer",
  "description": "Skill description from frontmatter",
  "validation_status": "valid_standard",
  "commit_sha": "abc123",
  "content_hash": "sha256:...",
  "file_count": 4,
  "total_size_bytes": 12345,
  "files": [
    "SKILL.md",
    "scripts/analyze.py",
    "references/guide.md"
  ],
  "snapshot_path": "data/snapshots/github__owner__repo/skills/pdf-analyzer",
  "snapshot_complete": true,
  "excluded_files": [],
  "collected_at": "2026-07-16T00:00:00Z"
}
```

`snapshot_complete` is `false` when any file was excluded from the snapshot (binary, oversized, unsafe path, or download failure). `excluded_files` lists each excluded file with its reason: `{"path": "...", "reason": "binary|oversized|unsafe_path|download_failed"}`.

## RejectedCandidateRecord

Represents a candidate that was discovered but rejected or could not be validated.

Required fields:

```json
{
  "candidate_id": "github__owner__repo__docs__SKILL.md",
  "repository_id": "github__owner__repo",
  "platform": "github",
  "owner": "owner",
  "repo": "repo",
  "path": "docs/SKILL.md",
  "rejection_status": "documentation_only",
  "rejection_reason": "Path appears to be documentation, not an operational skill directory.",
  "discovery_sources": ["github_code_search"],
  "discovery_queries": ["filename:SKILL.md"],
  "commit_sha": "abc123",
  "collected_at": "2026-07-16T00:00:00Z"
}
```

## Required validation statuses

Valid:

- `valid_standard`
- `valid_lenient`

Invalid/rejected:

- `invalid_missing_skill_md`
- `invalid_missing_frontmatter`
- `invalid_malformed_frontmatter`
- `invalid_missing_name`
- `invalid_missing_description`
- `documentation_only`
- `example_only`
- `too_large`
- `binary_or_unsupported`
- `repository_unavailable`
- `undetermined`

## Schema-change rule

Any code change that modifies these records must also update:

- this file,
- `config/output_schema.json`,
- tests validating sample records.
