# Skill Scanning Crawler

MSc project component — discovery and dataset-acquisition pipeline for public agent skills.

## What it does

Discovers public GitHub repositories that publish agent skills, validates them, ranks by
popularity, downloads frozen snapshots, and exports a reproducible dataset that Part 2
can analyse with vulnerability-scanning tools.

It does **not** decide whether a skill is malicious; it produces the dataset that scanners
will analyse later.

## Pipeline

```text
Seed lists + GitHub code/repo search
        ↓
CandidateRepository list         (run_discover)
        ↓
RepositoryRecord list            (run_enrich)
        ↓
SkillCandidate list              (run_locate_skills)
        ↓
ValidatedSkillCandidate list     (run_validate)
        ↓
Ranked RepositoryRecord list     (run_rank)
        ↓
SkillRecord list + snapshots     (run_snapshot)
        ↓
JSONL manifests + JSON reports   (run_export)
```

## Quick start

### 1. Install

```powershell
pip install -e ".[dev]"
```

### 2. Set your GitHub token (never paste tokens into chat)

```powershell
$env:GITHUB_TOKEN = "ghp_…"      # PowerShell
# or
export GITHUB_TOKEN="ghp_…"      # bash/zsh
```

### 3. Run the full pipeline

```powershell
python -m skill_scanning_crawler run --config config/discovery.example.yaml
```

### 4. Run individual stages

```powershell
python -m skill_scanning_crawler discover  --config config/discovery.example.yaml
python -m skill_scanning_crawler enrich    --config config/discovery.example.yaml
python -m skill_scanning_crawler locate    --config config/discovery.example.yaml
python -m skill_scanning_crawler validate  --config config/discovery.example.yaml
python -m skill_scanning_crawler rank      --config config/discovery.example.yaml
python -m skill_scanning_crawler snapshot  --config config/discovery.example.yaml
python -m skill_scanning_crawler export    --config config/discovery.example.yaml
```

Every command supports `--dry-run` and `--resume`:

```powershell
python -m skill_scanning_crawler run --config config/discovery.example.yaml --dry-run
python -m skill_scanning_crawler run --config config/discovery.example.yaml --resume
```

## Output layout

All pipeline output is written under `skill-scanning-crawler/data/`. **The
Part 1 dataset is committed to this repository**, so the discovered skills and
their manifests are available directly — no run or GitHub token required to
inspect them. (Run-internal state — `data/.checkpoints/`, `data/.current_run_id`,
the request cache, and logs — is git-ignored.)

```text
data/
├── manifests/
│   ├── repositories.jsonl                 # all 2,456 enriched repos
│   ├── repositories_ranked_by_stars.jsonl # repos ranked descending by stars, top-50/100 flagged
│   ├── skills.jsonl                        # all 735 downloaded, validated skills (one row per skill)
│   ├── skills_top50.jsonl                  # skills belonging to the top-50 repos
│   └── rejected_candidates.jsonl           # every rejection with reason
├── snapshots/                              # ← the skills themselves are saved here
│   └── <owner>/<repo>/<skill>/<sha8>/      # frozen at the pinned commit SHA (first 8 chars)
│       ├── SKILL.md                        # skill manifest (validated YAML frontmatter)
│       └── ...                             # auxiliary files: references/, scripts, README, etc.
└── reports/
    ├── discovery_summary.json
    ├── dataset_statistics.json
    ├── ranked_top100_by_stars.md
    └── part1_summary.json
```

**Where the skills are saved:** each skill's files live at
`skill-scanning-crawler/data/snapshots/<owner>/<repo>/<skill>/<sha8>/`, and every
skill's metadata (path, commit SHA, content hash, file list, snapshot path) is
indexed in `data/manifests/skills.jsonl`. Snapshot files are stored byte-for-byte
(`.gitattributes` marks them `-text`), so they reproduce the original download and
match the content hashes recorded in the manifest.

## Tests

```powershell
# Run all offline tests (no GITHUB_TOKEN needed)
python -m pytest tests/ -m "not integration" -v

# Run optional live integration tests (requires GITHUB_TOKEN)
python -m pytest tests/ -m integration -v
```

## Code quality

```powershell
ruff check src/ tests/
mypy src/
```

## Configuration

Edit `config/discovery.example.yaml` to set:

- `seed_lists` — curated seed-list URLs or local fixture paths
- `github.top_n_repositories` — how many repos to export (default 50)
- `github.include_forks` / `include_archived` — filter controls
- `rate_limits` — concurrency and retry settings
- `cache.enabled` — disable for clean runs

## Security constraints

- Token loaded from `GITHUB_TOKEN` environment variable only — never hardcoded or logged.
- Downloaded repository code is never executed, imported, or installed.
- Path traversal is rejected during snapshot download.
- Binary and oversized files are recorded and excluded, never silently dropped.
- Every rejected candidate is written to `rejected_candidates.jsonl`.

## Non-goals (v1)

- Vulnerability scanning
- Maliciousness classification
- GitLab or other platforms
- Active MCP server
- Scanner comparison
