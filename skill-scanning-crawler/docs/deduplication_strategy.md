# Deduplication Strategy

## Repository-level deduplication

Canonical identity:

```text
github:owner/repo
```

Normalize URLs before adding candidates.

## Forks

Default v1 configuration excludes forks.

If forks are included later, record fork status and parent repository when available.

## Skill-level deduplication

Compute a content hash for each exported skill directory.

Recommended approach:

1. collect all included files,
2. sort by normalized relative path,
3. hash path + content bytes,
4. produce a stable SHA-256 digest.

## Exact duplicates

If two skill directories have the same content hash, mark them as exact duplicates.

Do not automatically delete them unless the experiment design requires it. Popularity and provenance may still matter.

## Near duplicates

Near-duplicate detection is out of scope for v1.
