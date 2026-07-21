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

```text
data/
├── manifests/
│   ├── repositories.jsonl          # all enriched repos
│   ├── skills.jsonl                # all downloaded, validated skills
│   └── rejected_candidates.jsonl  # every rejection with reason
├── snapshots/
│   └── <owner>/<repo>/<skill>/<sha8>/
│       ├── SKILL.md
│       └── ...
└── reports/
    ├── discovery_summary.json
    └── dataset_statistics.json
```

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
