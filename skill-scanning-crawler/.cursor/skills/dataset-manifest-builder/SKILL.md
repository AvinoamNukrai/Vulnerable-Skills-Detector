---
name: dataset-manifest-builder
description: Use when creating or modifying manifest schemas, JSONL exports, hashes, and dataset summaries.
---

# Dataset Manifest Builder Skill

Use this skill when working on output manifests.

## Required manifests

- `repositories.jsonl`
- `skills.jsonl`
- `rejected_candidates.jsonl`

## Record principles

Every exported record must be:

- machine-readable,
- schema-valid,
- deterministic,
- traceable to discovery source,
- reproducible by commit SHA where applicable.

## Repository records

Must include:

- repository ID,
- owner/name,
- stars,
- fork/archive status,
- default branch,
- commit SHA,
- discovery sources,
- discovery queries,
- skill count,
- selected flag.

## Skill records

Must include:

- skill ID,
- repository ID,
- skill path,
- skill name,
- validation status,
- commit SHA,
- content hash,
- file list,
- snapshot path.

## Rejected candidate records

Must include:

- candidate ID,
- repository ID,
- path,
- rejection status,
- rejection reason,
- discovery source/query,
- commit SHA if available.

## Schema rule

Any schema modification must update:

- `DATA_CONTRACT.md`,
- `config/output_schema.json`,
- schema tests.
