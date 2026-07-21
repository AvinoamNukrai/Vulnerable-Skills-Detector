# Part 2 Handoff

This document explains how the output of this crawler should be consumed by the vulnerability-scanning phase.

## Authoritative index

Part 2 should use:

```text
data/manifests/skills.jsonl
```

as the authoritative list of skills to scan.

Each `SkillRecord` contains:

- repository identity,
- skill path,
- validation status,
- commit SHA,
- snapshot path,
- content hash,
- file list.

## Scanner input directory

Scanner input should come from:

```text
data/snapshots/
```

Each skill snapshot should correspond to one `SkillRecord`.

Example:

```text
data/snapshots/github__owner__repo/skills/pdf-analyzer/
├── SKILL.md
├── scripts/
└── references/
```

## Do not scan live GitHub by default

Part 2 should not re-fetch live repository contents unless the project explicitly performs a dataset refresh.

Reason: repositories can change, disappear, or rewrite history. The crawler output is a frozen experimental corpus.

## Minimum scanner loop

Part 2 can iterate over the manifest:

```python
for skill in read_jsonl("data/manifests/skills.jsonl"):
    scan_path = skill["snapshot_path"]
    run_scanner(scan_path)
```

## Recommended scanner-output linkage

Part 2 findings should include:

- `skill_id`,
- `repository_id`,
- `commit_sha`,
- `content_hash`,
- scanner name,
- scanner version,
- scanner configuration.

This makes scanner results traceable to the exact dataset version.

## Dataset refreshes

If the crawler is rerun, write a new dataset version rather than overwriting old results.

Recommended:

```text
data/releases/2026-07-16/
data/releases/2026-07-30/
```

Each release should include its own manifests, snapshots, and reports.
