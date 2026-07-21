---
name: github-rate-limit-planner
description: Use when implementing GitHub API clients, retries, caching, and high-throughput crawling.
---

# GitHub Rate Limit Planner

Use this skill whenever touching GitHub API code.

## Goals

- Maximize throughput safely.
- Avoid secondary rate limits.
- Make long runs resumable.
- Avoid duplicate API calls.

## Requirements

Use:

- token authentication through environment variables,
- bounded concurrency,
- exponential backoff with jitter,
- `Retry-After` handling,
- persistent cache,
- checkpointed run state,
- structured logging.

## Suggested concurrency separation

Use independent concurrency controls for:

- search,
- metadata,
- tree inspection,
- content download.

Do not use unbounded concurrency.

## Cache keys

Cache by stable identities, for example:

- repository metadata: `github:owner/repo`
- tree: `github:owner/repo@commit_sha`
- file content: `github:owner/repo@commit_sha:path`

## Resumability

A failed run should be restartable without losing completed work.

Persist:

- candidate repository set,
- enriched repository records,
- validation results,
- rejected candidates,
- downloaded snapshot status.

## Secrets

Never log tokens.

Never write tokens to manifests.

Never expose tokens to downloaded repository files.
