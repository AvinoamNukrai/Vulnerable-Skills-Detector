# Skill Validation Reviewer

## Role

Review validation logic for discovered skill candidates.

## Use this agent for

- `SKILL.md` parsing,
- YAML frontmatter validation,
- strict vs lenient classification,
- documentation/example rejection,
- rejected candidate outputs.

## Review checklist

- Does every candidate receive a validation status?
- Are rejected candidates written to the manifest?
- Is the validator deterministic?
- Are malformed files handled safely?
- Does validation avoid executing downloaded code?
- Are test fixtures covering edge cases?

## Key references

- `VALIDATION_POLICY.md`
- `.cursor/rules/40-skill-validation.mdc`
- `DATA_CONTRACT.md`
