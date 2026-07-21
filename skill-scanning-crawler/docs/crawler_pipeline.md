# Crawler Pipeline

## Stage 1: Discover candidates

Sources:

- curated lists,
- GitHub code search,
- GitHub repository search,
- optional future graph expansion.

Output:

```text
candidate repositories
```

## Stage 2: Normalize identities

Convert all GitHub URLs into a canonical `github:owner/repo` identity.

## Stage 3: Enrich metadata

Fetch stars, forks, archive status, default branch, commit SHA, topics, license, and repository size.

## Stage 4: Locate skills

Inspect the repository tree and find `SKILL.md` files.

## Stage 5: Validate skills

Apply strict validation policy.

## Stage 6: Deduplicate

Merge duplicate repository identities and compute skill content hashes.

## Stage 7: Rank repositories

Rank confirmed repositories by stars and select top-N.

## Stage 8: Export snapshots

Download full valid skill directories at pinned commit SHA.

## Stage 9: Export manifests

Write JSONL manifests and summary reports.
