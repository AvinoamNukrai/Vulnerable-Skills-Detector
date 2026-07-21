# Project Scope

## One-sentence scope

Build a reproducible GitHub crawler that discovers, validates, ranks, freezes, and exports public agent skills as prepared input for a later vulnerability-scanning phase.

## In scope

### Discovery

- Parse curated seed lists.
- Search GitHub for repositories likely to contain agent skills.
- Track discovery provenance for each candidate repository.

### Repository metadata

Collect:

- owner,
- repository name,
- URL,
- stars,
- forks,
- fork status,
- archived status,
- default branch,
- latest commit SHA,
- license,
- topics,
- repository size,
- timestamps where available.

### Skill location

- Locate files named exactly `SKILL.md`.
- Map each `SKILL.md` to its parent skill directory.
- Support repositories that contain multiple skills.

### Skill validation

- Parse YAML frontmatter.
- Require strict fields for v1.
- Classify invalid candidates.
- Record rejected candidates.

### Ranking and selection

- Rank confirmed repositories by GitHub stars.
- Select top-N repositories, starting with top 50.
- Extract all valid skill directories from selected repositories.

### Snapshot and export

- Pin every repository to a commit SHA.
- Download valid skill directories and auxiliary files.
- Generate reproducible manifests.
- Compute content hashes.
- Produce dataset statistics.

## Out of scope for v1

- Vulnerability scanning.
- Deciding whether a skill is malicious.
- Running NVIDIA SkillSpector.
- Running Cisco Skill Scanner.
- Comparing scanner findings.
- Manual security annotation.
- GitLab support.
- Full web-scale crawling.
- Executing downloaded repository code.
- Active MCP server.
- Paid/cloud-based external scanner services.

## Possible later extensions

- GitLab support.
- Near-duplicate detection with MinHash or embeddings.
- Lenient support for nonstandard Claude command formats.
- Read-only MCP server over local manifests.
- Incremental refresh mode.
- Dataset browser.
- Integration tests against real GitHub fixtures.
