# Validation Policy

## Goal

Classify discovered skill candidates deterministically so Part 2 receives a clean dataset.

## Default mode for v1

Use **strict validation** only.

Lenient formats may be recorded later, but they should not be included in the primary v1 scanner dataset unless the TA explicitly approves.

## Strict valid skill

A candidate is `valid_standard` only if all of the following are true:

1. It contains a file named exactly `SKILL.md`.
2. `SKILL.md` is inside a directory that represents the skill root.
3. `SKILL.md` contains YAML frontmatter.
4. The YAML frontmatter parses successfully.
5. The frontmatter contains a non-empty `name`.
6. The frontmatter contains a non-empty `description`.
7. The candidate does not appear to be only documentation, a tutorial, or a template.
8. The skill directory can be safely listed, hashed, and exported.
9. The candidate is not too large according to the configured policy.

## Lenient valid skill

A candidate may later be marked `valid_lenient` if it clearly represents an agent skill or command but does not fully match the strict format.

Examples may include:

- nonstandard Claude command directories,
- Antigravity-style skill packages,
- markdown-based agent capabilities without standard frontmatter.

Do not include lenient candidates in v1 top-N export unless configured.

## Rejection statuses

Use one of the following statuses:

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

## Documentation-only heuristics

A candidate should be suspected as documentation-only when the path includes:

- `docs/`
- `documentation/`
- `tutorial/`
- `tutorials/`
- `examples/docs/`
- `spec/`
- `specification/`

This is not an automatic rejection by itself. The validator should combine path evidence with content evidence.

## Example-only heuristics

A candidate should be suspected as an example-only candidate when:

- the path contains `example`, `examples`, `sample`, `template`, or `demo`;
- the frontmatter describes how to create skills rather than an operational skill;
- the README explicitly says the directory is a sample.

## Rejected-candidate rule

Never silently discard a candidate.

Every rejected candidate should be written to `rejected_candidates.jsonl` with:

- path,
- repository,
- reason,
- discovery source,
- query if applicable,
- commit SHA if available.

## Safety rule

Validation must never execute downloaded code.
