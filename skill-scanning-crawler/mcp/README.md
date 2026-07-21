# MCP Notes

MCP is intentionally not active in v1.

The crawler should be implemented as a normal Python CLI/library so it can be reproduced outside Cursor or any AI client.

## Why no active MCP in v1?

- The project deliverable is a dataset, not an interactive agent tool.
- GitHub API access belongs in crawler application code.
- MCP adds complexity before the core acquisition pipeline works.
- Credentials are safer when handled by the crawler configuration and environment variables.

## Possible future MCP server

A later read-only MCP server could expose local dataset tools:

- `list_repositories`
- `list_skills`
- `get_skill_record`
- `search_rejected_candidates`
- `summarize_dataset`

This should only be added after the crawler and manifest contract are stable.
