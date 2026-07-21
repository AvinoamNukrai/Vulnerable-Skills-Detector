---
name: part2-packager
description: Use when preparing the final scanner-input directory and Part 2 handoff artifacts.
---

# Part 2 Packager Skill

Use this skill when exporting the final dataset for scanner evaluation.

## Output structure

```text
data/
├── manifests/
│   ├── repositories.jsonl
│   ├── skills.jsonl
│   └── rejected_candidates.jsonl
├── snapshots/
│   └── github__owner__repo/
│       └── ...
└── reports/
    ├── discovery_summary.json
    └── dataset_statistics.json
```

## Snapshot rules

- Export full valid skill directories.
- Include auxiliary files inside the skill directory.
- Normalize paths.
- Reject path traversal.
- Enforce file-size limits.
- Avoid executing or importing any downloaded file.

## Handoff rule

Part 2 should scan local snapshots, not live GitHub URLs.

`skills.jsonl` is the authoritative scanner input index.

## Dataset statistics

Generate summary stats:

- candidate repository count,
- confirmed repository count,
- selected repository count,
- valid skill count,
- rejected candidate count,
- discovery-source contribution,
- top repositories by stars,
- file-type distribution,
- duplicate hash count.
