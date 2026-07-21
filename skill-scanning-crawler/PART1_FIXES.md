# Part 1 — Correctness fixes

Branch: `fix/part1-seed-discovery-and-robustness`

This document explains the bugs found in the skill-scanning-crawler while
checking it against the **Part 1** brief, and the fixes applied. The crawler's
architecture already implemented every Part 1 requirement (seed lists → GitHub
crawl → dedup → enrich → locate → validate → rank by stars → snapshot skills +
auxiliary files → export). The issues below were correctness/robustness defects
that degraded a *real* run, the most important of which caused **one of the two
mandated seed lists to contribute zero repositories, silently**.

## How the issues were found

1. Read the brief (`Docs/instructions.txt`) and mapped each Part 1 requirement
   to code.
2. Ran the offline test suite (199 passing) and the CLI dry-run to confirm the
   pipeline was real and runnable.
3. Ran an adversarial multi-agent review: one reviewer per dimension
   (discovery, ranking, acquisition, throughput, enrich/locate/validate,
   runnability), and a second skeptic agent that tried to **refute** each
   finding. About half the initial findings were refuted and dropped.
4. Independently reproduced every surviving finding with live fetches and unit
   probes before fixing it.

The refuted (i.e. **not** changed, verified to be non-issues) claims included:
root-level `SKILL.md` pulling the whole repo, whole-repo `TOO_LARGE` rejection,
nested-skill over-inclusion, lenient-repo exclusion from ranking, and the
secondary-rate-limit backoff claims. Ranking (descending by stars), top-N
selection, SHA-pinned snapshots, and core acquisition were confirmed correct and
left unchanged.

---

## Fixes

### 1. (HIGH) Antigravity seed silently yielded 0 repositories

**Problem.** The brief names two curated seeds. The Antigravity seed URL
(`https://sickn33.github.io/antigravity-awesome-skills/`) now serves a 700-byte
**HTML `meta-refresh` stub** that returns **HTTP 200** (not a 3xx redirect) and
contains zero `github.com` links. `httpx` follows only HTTP redirects, not HTML
meta-refresh, so the crawler fetched the stub, extracted nothing, and logged
`extracted 0 candidates` at INFO — undetected. The page it redirects to is a
JS-rendered SPA, so even fetching it statically yields ~1 link.

**Evidence.**
```
antigravity (named URL) → 700 bytes, 0 repos
agentic (moved-to SPA)  → 10 KB, 1 repo
```

**Fix.**
- `config/discovery.example.yaml`: point the Antigravity seed at the list's
  **backing-repo README** (`raw.githubusercontent.com/sickn33/agentic-awesome-skills/main/README.md`),
  which contains the same links as plain markdown that the text extractor parses
  reliably.
- `discovery/seed_collector.py`: added **meta-refresh following** (bounded to 3
  hops) so any HTTP-200 meta-refresh stub is followed to its target — a general
  robustness improvement.
- `discovery/seed_collector.py`: a seed that extracts **0 repositories now logs
  a WARNING**, so a dead/moved/JS-rendered seed can never fail silently again.

**Result.** Antigravity seed: **0 → 217 repos**. Combined seed coverage:
**126 → 344 repos** (before GitHub search even runs).

**Tests.** `test_fetch_seed_list_follows_meta_refresh`.

### 2. (MEDIUM) Extraction regex dropped every path-carrying GitHub URL

**Problem.** `_GH_URL_BROAD_RE` kept `/` inside its trailing negated
character class (`[^\w/.\-]`), so any GitHub URL with a path or trailing slash
matched **nothing** — e.g. `…/owner/repo/tree/main/skills/foo`,
`…/owner/repo/blob/main/SKILL.md`, or a bare `…/owner/repo/`. Deep links to
skill subfolders are the **dominant citation form in "awesome" lists**, so these
repos were silently missed. (A correct regex existed in `normalizer.py` but was
never used for extraction.)

**Fix.** `discovery/seed_collector.py`: removed `/` from the terminator
(`[^\w/.\-]` → `[^\w.\-]`) so `/` correctly ends the repo capture; added a
trailing-dot cleanup for links captured from prose (`…/repo.`); expanded the
non-repo owner exclusion list (`sponsors`, `orgs`, `features`, …).

**Tests.** `test_extract_captures_path_carrying_urls` (parametrized),
`test_extract_strips_trailing_prose_dot`.

### 3. (MEDIUM) One unexpected error aborted an entire pipeline stage

**Problem.** Stage workers caught only `GitHubClientError`, and the stage-level
`asyncio.gather(...)` calls used no `return_exceptions`. A single non-`GitHubClientError`
(e.g. `httpx.RemoteProtocolError` — which is an `httpx.HTTPError` but **not** a
`NetworkError`, so the client's retry loop did not catch it — or a JSON-decode
error) would propagate and kill the whole `discover`/`enrich`/`locate`/`validate`/`snapshot`
stage mid-crawl.

**Fix.**
- `github_client/client.py`: broadened the transport `except` from
  `(TimeoutException, NetworkError)` to `httpx.HTTPError`, so protocol-level
  failures are retried and surface as a clean `GitHubClientError`.
- `metadata/enricher.py`, `validation/pipeline.py`, `locator/tree_scanner.py`,
  `download/snapshot.py`: each per-item worker now has a broad `except Exception`
  safety net that converts an unexpected error into a **rejection/skip** for that
  one item, so one bad repo never aborts the stage.

**Tests.** `test_enrich_unexpected_exception_does_not_abort_stage`.

### 4. (MEDIUM) Truncated git trees were silently under-scanned

**Problem.** `get_tree` ignored GitHub's `truncated` flag (set when a recursive
tree exceeds 100k entries), so `SKILL.md` and auxiliary files past the cap were
silently missed while snapshots still reported complete.

**Fix.** `github_client/client.py`: `get_tree` now logs a WARNING when
`truncated` is true, making large-repo under-scanning visible. (Full per-subtree
pagination is noted as future work — see below.)

### 5. (MEDIUM) BOM-prefixed `SKILL.md` was wrongly rejected

**Problem.** A UTF-8 BOM (`U+FEFF`) before the opening `---` made
`lines[0].strip() != "---"` true (`str.strip()` does not treat the BOM as
whitespace), so a valid skill was misclassified `INVALID_MISSING_FRONTMATTER`.

**Fix.** `validation/frontmatter.py`: strip a leading BOM before parsing.

**Tests.** `test_bom_prefixed_frontmatter_is_parsed`.

### 6. (LOW) `repositories.jsonl` always reported `skill_count = 0`

**Problem.** `enricher.py` set `skill_count=0` as a placeholder (the true count
isn't known until skills are located/validated/downloaded) and no later stage
updated it.

**Fix.** `export/writer.py`: `write_manifests` now derives `skill_count` per
repository from the exported `SkillRecord`s before writing the manifest.

**Tests.** `test_write_manifests_populates_skill_count`.

---

## Throughput fixes (found by running it end-to-end)

Running the fixed crawler against GitHub surfaced three throughput defects that
made a real top-50 run stall on GitHub's rate limits. All three are now fixed.

### 7. (HIGH) Tree-scanning every candidate tripped the secondary rate limit

**Problem.** The pipeline enriched **and** recursively tree-scanned *all* ~2,480
discovered candidates before taking the top-50. Firing thousands of recursive
`git/trees` calls at `tree_concurrency=6` tripped GitHub's **secondary (abuse)
rate limit** almost immediately; six workers each retrying kept it tripped (a
retry-storm) and the locate stage made ~zero progress for ~50 minutes.

**Fix.**
- New `github.preselect_top_k` (set to 250): after enrichment, only the top-K
  repos *by stars* are carried into locate/validate/snapshot. Since the output
  is the top-N by stars, this is ~10x fewer tree calls with no loss to the
  ranked result. (`pipeline.py:_preselect_for_scanning`, `config.py`)
- Gentler default concurrency in `discovery.example.yaml`
  (`tree_concurrency 6→3`, `metadata_concurrency 8→5`, `search_concurrency 2→1`).

### 8. (HIGH) Aggregator repos exploded the skill count

**Problem.** With the top-250 selected, locate found **19,922** SKILL.md
candidates — a few "awesome-skills" aggregator repos vendored thousands each
(one had 6,228). Validating/snapshotting all of them would blow the **primary**
5,000/hr rate limit.

**Fix.** New `github.max_skills_per_repo` (set to 25): caps SKILL.md candidates
per repo, keeping the shallowest (most representative) paths deterministically.
19,922 → 2,782 candidates. (`locator/tree_scanner.py`, `config.py`)

### 9. (MEDIUM) Redirect/rename aliases double-counted repos

**Problem.** Discovery dedupes on the *discovered* name, so a repo reachable via
two names (an old name + its renamed target) survived as two enriched records
(~0.5% of the set).

**Fix.** `enrich_repositories` now merges records that resolve to the same
`full_name` after redirects, unioning provenance. (`metadata/enricher.py`)

## Live run outcome

A real top-50 run (seeds + GitHub search, your `gh` token) produced:

- **Discovered:** 3,344 → **2,480** deduped candidates (the fixed Antigravity
  seed contributed **217**, previously 0).
- **Enriched:** 2,468 → **2,456** after alias dedup, with real GitHub star counts
  (verified against live API — e.g. `anthropics/skills` 162,865).
- **Ranked & selected:** **top-50 repos by stars** (162,856 → 26,155).
- **Skills identified:** **2,603** valid_standard skills; **735** in the top-50 repos.
- **Snapshotted:** 45 of 735 skill directories fully downloaded before the run
  hit the primary rate-limit ceiling; the remaining ~690 need a fresh hourly
  window (the crawler correctly backs off, so this is a budget limit, not a bug).

Artifacts: `data/manifests/repositories.jsonl` (2,456 ranked, top-50 flagged),
`data/manifests/skills_top50.jsonl` (735 skills), `data/manifests/repositories_ranked_by_stars.jsonl`,
`data/reports/ranked_top100_by_stars.md`, `data/reports/part1_summary.json`.

## Files changed

| File | Fix |
|---|---|
| `config/discovery.example.yaml` | 1 — Antigravity seed → raw README |
| `src/.../discovery/seed_collector.py` | 1, 2 — meta-refresh follow, 0-yield warning, regex, owner excludes |
| `src/.../github_client/client.py` | 3, 4 — broadened retry `except`, truncated-tree warning |
| `src/.../metadata/enricher.py` | 3 — per-item safety net |
| `src/.../validation/pipeline.py` | 3 — per-item safety net |
| `src/.../locator/tree_scanner.py` | 3 — per-item safety net |
| `src/.../download/snapshot.py` | 3 — per-item safety net |
| `src/.../validation/frontmatter.py` | 5 — BOM strip |
| `src/.../export/writer.py` | 6 — populate `skill_count` |
| `src/.../common/config.py` | 7, 8 — `preselect_top_k`, `max_skills_per_repo` |
| `src/.../pipeline.py` | 7 — `_preselect_for_scanning` before locate |
| `src/.../locator/tree_scanner.py` | 8 — per-repo skill cap |
| `src/.../metadata/enricher.py` | 9 — alias dedup by resolved `full_name` |
| `config/discovery.example.yaml` | 7, 8 — preselect cap, per-repo cap, gentle concurrency |
| `tests/...` | regression tests for fixes 1, 2, 3, 5, 6, 7, 8, 9 |

## Verification

- `pytest -m "not integration"` → **213 passed** (199 original + 14 new).
- `ruff check src/ tests/` → clean.
- `mypy src/` (strict) → clean.
- Live seed check through the real collector: awesome-skills **127**,
  antigravity **217**, total **344** unique seed repos.
- Full live run completed discovery → enrichment → locate → validate → rank,
  selecting the top-50 repos by stars and identifying 2,603 valid skills.

## Known limitations / future work

- **Antigravity SPA:** the fix reads the backing-repo README, which tracks the
  rendered list closely but could drift if the site and repo diverge. A
  longer-term option is to parse the SPA's data source directly.
- **Truncated trees:** currently surfaced via a warning; full correctness for
  >100k-entry repos needs per-subtree tree fetching.
- **Discovery breadth:** GitHub search is still capped at `max_pages=5`
  (~500 results/query vs GitHub's 1000 ceiling). Raising this is a throughput
  vs. rate-limit trade-off, not a correctness bug.
- **Snapshot cost:** snapshotting downloads every file of every skill via the
  Contents API (1 call/file), so 735 skills is a few thousand calls — near the
  5,000/hr primary limit. A cheaper design would download each repo's
  tarball/zipball once (1 call/repo) and extract skill dirs locally. Until then,
  a full top-50 snapshot should run in a fresh hourly window.
