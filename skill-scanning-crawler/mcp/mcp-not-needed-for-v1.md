# MCP Not Needed for v1

## Decision

Do not implement an active MCP server in v1.

## Rationale

The core project requirement is to discover and package public agent skills as a reproducible scanner input dataset.

A standalone CLI is simpler, safer, and easier to evaluate academically.

## Reconsider MCP only if

- Cursor needs to query local manifests interactively,
- the dataset becomes large enough to need an agent-facing browser,
- the crawler has a stable read-only API,
- no credentials or unsafe operations are exposed through MCP.

## Security constraint

If MCP is added later, it should be read-only by default and should not expose GitHub tokens or allow arbitrary command execution.
