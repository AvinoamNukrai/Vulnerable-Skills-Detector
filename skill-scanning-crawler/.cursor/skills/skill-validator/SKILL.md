---
name: skill-validator
description: Use when implementing or reviewing logic that detects and validates agent skill directories.
---

# Skill Validator Skill

Use this skill when implementing `SKILL.md` discovery and validation.

## Strict v1 definition

A skill is valid only if:

1. a file named exactly `SKILL.md` exists,
2. it is inside a skill directory,
3. it contains YAML frontmatter,
4. the frontmatter parses,
5. `name` is present and non-empty,
6. `description` is present and non-empty,
7. the candidate is not only documentation, sample, tutorial, or template content.

## Validation outputs

Emit one of:

- `valid_standard`
- `valid_lenient`
- `invalid_missing_skill_md`
- `invalid_missing_frontmatter`
- `invalid_malformed_frontmatter`
- `invalid_missing_name`
- `invalid_missing_description`
- `documentation_only`
- `example_only`
- `too_large`
- `binary_or_unsupported`
- `repository_unavailable`
- `undetermined`

## Important rule

Do not silently drop candidates.

Rejected candidates must be written with reason and provenance.

## Tests to add

- valid standard skill,
- missing frontmatter,
- malformed YAML,
- missing name,
- missing description,
- documentation-only path,
- example-only path,
- multi-skill repository.
