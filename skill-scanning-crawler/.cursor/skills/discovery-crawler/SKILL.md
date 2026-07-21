---
name: discovery-crawler
description: Use when implementing or improving repository discovery for public agent skills.
---

# Discovery Crawler Skill

Use this skill when working on candidate discovery.

## Objective

Find public GitHub repositories that may contain agent skills, while recording how every candidate was discovered.

## Discovery channels

Implement separate collectors for:

1. curated seed lists,
2. GitHub code search,
3. GitHub repository search,
4. optional later graph expansion.

## Curated seed ingestion

Start with configured seed URLs.

The collector should extract:

- repository URL,
- owner,
- repo name,
- source list name,
- advertised skill name if available,
- discovered timestamp.

Normalize all repository URLs to canonical `github:owner/repo`.

## GitHub code search

Use configured queries from `config/github_queries.yaml`.

Typical query families:

- exact `SKILL.md` discovery,
- `SKILL.md` under `skills/`,
- README mentions of agent skills,
- Claude skills references,
- repository topics and descriptions.

Every candidate must preserve:

- query name,
- exact query string,
- search type,
- result URL if available.

## Candidate merging

If the same repository appears from multiple sources, merge it into one candidate while preserving all discovery sources and queries.

## Output

The discovery stage should produce candidate repository records, not validated skill records.

Validation belongs to the validator stage.
