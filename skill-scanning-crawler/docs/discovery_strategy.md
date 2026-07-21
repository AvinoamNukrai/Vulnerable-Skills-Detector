# Discovery Strategy

## Goal

Find repositories likely to contain public agent skills.

## Discovery sources

### Curated lists

Use curated lists as seed sources and recall checks.

### GitHub code search

Search for `SKILL.md` and related patterns.

### GitHub repository search

Search repository names, descriptions, topics, and README content through configured queries.

## Provenance

Every candidate repository should record:

- discovery source,
- query name,
- exact query text,
- result URL if available,
- timestamp.

## Candidate merging

A repository discovered multiple times should appear once, with merged provenance.

## Recall proxy

The curated lists can help evaluate recall:

```text
rediscovered curated repositories / total curated repositories
```

This is not true global recall, but it is a useful proxy.
