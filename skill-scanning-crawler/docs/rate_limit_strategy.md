# Rate Limit Strategy

## Goals

- Avoid triggering GitHub secondary limits.
- Maximize useful throughput.
- Make runs resumable.

## Rules

- Use authenticated requests.
- Use bounded concurrency.
- Separate semaphores for search, metadata, tree, and download.
- Cache stable responses.
- Respect `Retry-After`.
- Use exponential backoff with jitter.
- Persist checkpoints.

## Suggested initial concurrency

```yaml
search_concurrency: 2
metadata_concurrency: 8
tree_concurrency: 6
download_concurrency: 4
```

Tune empirically.

## Logging

Log:

- request type,
- status code,
- retry count,
- rate-limit remaining where available,
- cache hit/miss,
- repository identity,
- query name.
