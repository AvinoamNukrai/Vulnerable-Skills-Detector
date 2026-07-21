# Skills Scanning Project — Specification

## Overview

The project has two parts: **skill discovery** and **vulnerability scanning**.

---

## Part 1 — Skill Discovery Scanner

### Goal
Identify repositories that publish agent "skills" on public sources (GitHub, GitLab, etc.), rank them by stars in descending order, and take the **top-N repos** (start with 50, up to 100). Pull the skill files + necessary auxiliary files from those repos for assessment.

### Seed Sources
- **Claude skills:** https://awesome-skills.com/
- **Antigravity skills:** https://sickn33.github.io/antigravity-awesome-skills/

### Research Goal
Build a scraper that:
1. Crawls GitHub and discovers skill repos automatically
2. Produces an **exhaustive list** of discovered skills
3. Optimizes for **throughput** — parallelism, rate-limit handling, caching (GitHub API is the main bottleneck)

---

## Part 2 — Vulnerability Scanning

### Reference Scanners
- **NVIDIA SkillSpector:** https://github.com/NVIDIA/SkillSpector  
  64 patterns across 16 categories, static + optional LLM analysis
- **Cisco Skill Scanner:** https://github.com/cisco-ai-defense/skill-scanner  
  Published threat taxonomy, behavioral dataflow, meta-analyzer for false-positive filtering

### Research Goal
Review both scanners' code, identify gaps, and produce a **report + code improvements**.

---

## Part 2 — Tasks

### Task 1: Cross-Scanner Analysis
- Run **both scanners** over the same set of skills (output of Part 1)
- Flag every skill where one scanner detects something the other misses → these are **gap candidates**
- Manually inspect a sample of disagreements to confirm:
  - Real detections vs. noise
  - What each scanner catches that the other doesn't
- Produce a **false-positive (FP) report** for both scanners

### Task 2: Taxonomy Coverage Analysis
- Both repos publish their detection categories
- **Diff** them against each other and against external references:
  - [OWASP LLM / Agentic Risks](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
  - [MITRE ATLAS](https://atlas.mitre.org/)
- Any threat class in the external references that **neither scanner detects** = a coverage gap

### Deliverable
A **written analysis** of the gaps across both scanners, with:
- How to improve each scanner
- Pseudo-code **or** actual code for the improvements
