# Crawler Design

## Purpose

The crawler converts unstructured public repositories into a structured, reproducible dataset of validated agent skills.

## Pipeline

```text
Seed collectors
      |
      v
Candidate repository queue
      |
      v
Repository identity normalizer
      |
      v
Repository metadata enricher
      |
      v
Repository tree scanner
      |
      v
Skill locator
      |
      v
Skill validator
      |
      v
Deduplicator
      |
      v
Top-N repository ranker
      |
      v
Snapshot downloader
      |
      v
Manifest exporter
      |
      v
Part 2 scanner input
```

## Core concepts

### Candidate repository

A repository discovered by a seed list, GitHub code search, GitHub repository search, or later graph expansion. It is not yet confirmed to contain a valid skill.

### Confirmed repository

A candidate repository that contains at least one valid skill.

### Skill candidate

A path or directory that might represent an agent skill, usually because it contains a file named `SKILL.md`.

### Valid skill

A skill candidate that passes the chosen validation policy.

### Snapshot

A local copy of a selected valid skill directory at a specific commit SHA.

## Component responsibilities

### Seed collectors

- Parse curated lists.
- Extract repository URLs.
- Normalize repository identities.
- Record provenance.

### GitHub search collectors

- Execute configured code-search and repository-search queries.
- Convert results into candidate repositories.
- Record query names and exact query strings.

### Metadata enricher

- Fetch repository metadata.
- Resolve default branch and current commit SHA.
- Record stars and other ranking metadata.
- Respect rate limits and cache results.

### Repository tree scanner

- Inspect repository file tree at the pinned commit.
- Find candidate `SKILL.md` files.
- Avoid downloading entire repositories when API tree inspection is sufficient.

### Skill locator

- Map each `SKILL.md` file to its parent directory.
- Support multiple skills per repository.

### Skill validator

- Download or fetch `SKILL.md`.
- Parse frontmatter.
- Apply strict or lenient validation policy.
- Emit valid skill records and rejected candidate records.

### Deduplicator

- Remove duplicate repositories by canonical identity.
- Compute skill content hashes.
- Mark exact duplicate skill directories.
- Preserve provenance even when candidates are merged.

### Ranker

- Rank confirmed repositories by stars.
- Apply filters:
  - exclude archived repositories,
  - optionally exclude forks,
  - require at least one valid skill.
- Select top-N repositories.

### Snapshot downloader

- Download selected skill directories at pinned commit SHA.
- Include auxiliary files inside the skill directory.
- Enforce file-size and path-safety policies.
- Compute content hash.

### Manifest exporter

- Write JSONL manifests.
- Validate output against schema.
- Generate summary statistics.

## Recommended implementation order

1. Define Pydantic models.
2. Implement URL normalization.
3. Implement curated-list ingestion.
4. Implement GitHub metadata client.
5. Implement tree scanning for `SKILL.md`.
6. Implement strict validation.
7. Implement JSONL export.
8. Implement ranking.
9. Implement snapshot download.
10. Implement summary reports.
11. Add scaling: async, caching, backoff, resumability.
