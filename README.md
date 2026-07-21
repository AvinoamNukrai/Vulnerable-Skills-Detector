# Vulnerable-Skills-Detector

A tool for detecting vulnerable skills in AI agent systems.

## Part 1 — Skill discovery scanner

The discovery-and-acquisition pipeline lives in
[`skill-scanning-crawler/`](skill-scanning-crawler/README.md). It crawls GitHub,
ranks skill-publishing repos by stars, and downloads the top-50 repos' skills.

**The discovered skills are saved (and committed) under
[`skill-scanning-crawler/data/`](skill-scanning-crawler/data/):**

- `data/snapshots/<owner>/<repo>/<skill>/<sha8>/` — the skill files themselves
  (`SKILL.md` + auxiliary files), frozen at a pinned commit SHA.
- `data/manifests/skills.jsonl` — index of all 735 skills (path, SHA, content
  hash, file list, snapshot path).
- `data/reports/` — discovery/dataset summaries.

See the [crawler README](skill-scanning-crawler/README.md#output-layout) for the
full layout.
