# Data Model

## Repository vs skill

One repository may contain many skills.

```text
repository
├── skills/a/SKILL.md
├── skills/b/SKILL.md
└── skills/c/SKILL.md
```

Therefore, the project uses two main records:

- `RepositoryRecord`
- `SkillRecord`

## RepositoryRecord

Repository-level metadata and ranking information.

Used for:

- star ranking,
- filtering forks/archived repositories,
- grouping skills,
- reproducibility.

## SkillRecord

Skill-level validation and snapshot information.

Used for:

- scanner input,
- content hashing,
- Part 2 linkage.

## RejectedCandidateRecord

Rejected candidate information.

Used for:

- validation transparency,
- false-candidate analysis,
- improving discovery precision.
