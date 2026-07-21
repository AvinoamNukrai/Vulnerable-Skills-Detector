# Cursor Workflow

## Recommended first prompt to Cursor

Ask Cursor:

```text
Read AGENTS.md, PROJECT_SCOPE.md, DATA_CONTRACT.md, CRAWLER_DESIGN.md, VALIDATION_POLICY.md, and PART2_HANDOFF.md. Then create a minimal Python package skeleton for the crawler without implementing live GitHub calls yet.
```

## Milestone prompts

### Milestone 1: package skeleton

```text
Create the Python package skeleton under src/skill_scanning_crawler according to AGENTS.md and CRAWLER_DESIGN.md. Add pyproject.toml, basic CLI entrypoint, and placeholder modules. Do not implement network calls yet.
```

### Milestone 2: data models

```text
Implement Pydantic models for RepositoryRecord, SkillRecord, and RejectedCandidateRecord according to DATA_CONTRACT.md and config/output_schema.json. Add tests with sample records.
```

### Milestone 3: validation

```text
Implement strict SKILL.md validation according to VALIDATION_POLICY.md. Add fixtures and tests for valid, malformed, missing frontmatter, missing name, missing description, docs-only, and examples-only candidates.
```

### Milestone 4: GitHub client

```text
Implement a GitHub client abstraction with token loading from GITHUB_TOKEN, bounded concurrency, retries, caching hooks, and mocked tests. Do not hardcode credentials.
```

### Milestone 5: export

```text
Implement JSONL manifest writing, deterministic ordering, content hashing, and summary report generation.
```

## Use Cursor skills

Invoke the relevant Cursor skill when needed:

- discovery-crawler
- github-rate-limit-planner
- skill-validator
- dataset-manifest-builder
- part2-packager

## Use Cursor agents

Ask specific agents to review work:

- crawler-architect
- github-api-engineer
- skill-validation-reviewer
- dataset-contract-reviewer
- security-reviewer
