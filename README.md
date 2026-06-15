# Focus Hacking

Evidence-graded directory of free focus and attention techniques.
Each technique graded A–D based on peer-reviewed research from PubMed.

## Project Structure

```
focushacking/
├── techniques/               # Markdown files — one per technique (source of truth)
│   ├── pomodoro-technique.md
│   ├── mindfulness-meditation.md
│   └── ...                   # 58 techniques
│
├── config/
│   ├── techniques.yaml       # PubMed search queries per technique
│   ├── grading-rules.yaml    # A/B/C/D/? thresholds (machine-readable)
│   └── GRADING_RUBRIC.md     # Human-readable methodology (adapted from Examine.com)
│
├── data/
│   ├── papers_index.json     # Persistent paper database (146 papers, version-controlled)
│   └── outcomes_index.json   # Per-technique outcome grades (editorial, version-controlled)
│
├── scripts/                  # Research pipeline + quality checks
│   ├── search_papers.py      #   WEEKLY   PubMed E-utilities + rate limiting + dedup
│   ├── grade_technique.py    #   WEEKLY   Rule-based grade recalculation
│   ├── update_markdown.py    #   WEEKLY   Updates papers_index.json + frontmatter counters
│   ├── build_pr.py           #   WEEKLY   Git branch + commit + GitHub PR
│   ├── import_base_data.py   # ON-DEMAND  Import editorial data from POC JSON
│   ├── validate_base_data.py # ON-DEMAND  Cross-check editorial data consistency
│   ├── detect_outcome_drift.py # WEEKLY  Flag outcomes stale vs latest papers
│   ├── detect_grade_drift.py   # WEEKLY  Track grade changes + near-miss detection
│   ├── assess_paper_health.py  # WEEKLY  Evidence depth, stagnation, coverage
│   └── migrate_from_poc.py   # ONE-TIME   Initial import from PoC (historical)
│
├── src/                      # Astro website
│   ├── content.config.ts     # Content collection — reads techniques/*.md
│   ├── content/techniques → ../../techniques  (symlink)
│   ├── pages/
│   │   ├── index.astro       # Listing page with filters and search
│   │   ├── techniques/[...slug].astro  # Individual technique pages
│   │   ├── rss.xml.js        # RSS feed
│   │   └── 404.astro
│   ├── layouts/
│   │   └── BaseLayout.astro  # Nav, footer, theme toggle, SEO
│   ├── components/
│   │   └── TechniqueCard.astro
│   └── styles/
│       └── global.css        # CSS with light/dark theme variables
│
├── package.json
├── astro.config.mjs
└── tsconfig.json
```

## How It Works

### Content
Each technique is a markdown file with YAML frontmatter:
`grade`, `populations`, `focus_facets`, `difficulty`, `time_to_benefit`,
`session_time`, plus body text with description, example, steps, and mechanism.

Papers and outcomes are stored as structured JSON (`data/papers_index.json`,
`data/outcomes_index.json`) — not duplicated into markdown. The Astro site
reads all three sources at build time.

### Website (Astro)
- **Static HTML** — all pages pre-rendered at build time. No server, no DB.
- **58 individual technique pages** at `/techniques/pomodoro-technique/` etc.
- **Data-driven rendering** — papers (design badges, effect chips, PubMed links)
  and outcomes (grade pips, effect chips) rendered from JSON at build time.
- **Listing page** at `/` — pre-rendered cards with client-side filtering
  by category, grade, search, and sort. JSON data embedded in the page
  for instant filtering (no network calls).
- **Dark mode** — defaults to system preference (`prefers-color-scheme`),
  toggle stored in localStorage.
- **RSS feed** at `/rss.xml`.

### Research Pipeline

A weekly cron job searches PubMed for new papers, tags populations and focus
facets, recalculates grades, and opens a PR for human review.

#### Weekly Pipeline (automated, in order)

```
search_papers.py     →  .hermes/new_candidates.json
  (LLM tagging step) →  .hermes/tagged_candidates.json
update_markdown.py   →  data/papers_index.json (updated)
                      →  techniques/*.md (frontmatter counters)
grade_technique.py   →  techniques/*.md (grade, grade_detail recalculated)
build_pr.py          →  GitHub branch + PR
```

After the pipeline, run the health checks (can be in the same cron job):

```
detect_outcome_drift.py   →  .hermes/outcome_drift_report.json
detect_grade_drift.py     →  .hermes/grade_drift_report.json
                           →  .hermes/grade_history.json (appended)
assess_paper_health.py    →  .hermes/paper_health_report.json
```

#### Scripts Reference

| Script | Run | Purpose |
|--------|-----|---------|
| `search_papers.py` | Weekly | Queries PubMed for each technique (rate-limited), deduplicates against `papers_index.json`, writes candidates to `.hermes/new_candidates.json` |
| `update_markdown.py` | Weekly | Reads tagged candidates, adds new papers to `papers_index.json`, updates `total_papers`/`new_papers_this_run`/`last_searched` in each `.md` frontmatter. Papers are stored in the JSON index only — not duplicated into markdown body. |
| `grade_technique.py` | Weekly | Reads `papers_index.json` and `config/grading-rules.yaml`, recalculates `grade` and `grade_detail` in each `.md` frontmatter |
| `build_pr.py` | Weekly | Creates a git branch, commits all changes, opens a GitHub PR for human review |
| `detect_outcome_drift.py` | Weekly | Cross-references `outcomes_index.json` against `papers_index.json`. Flags: outcomes with recent un-reviewed papers, effect direction conflicts between outcomes and papers |
| `detect_grade_drift.py` | Weekly | Compares current grades against stored history in `.hermes/grade_history.json`. Reports: which grades changed (and why), near-miss grades (one paper away from bumping up/down) |
| `assess_paper_health.py` | Weekly | Holistic paper coverage report: evidence depth per technique, stagnation flags (no new papers in 2+ years), frontmatter count vs index consistency, grade drift vs POC baseline, study type mix |
| `import_base_data.py` | On-demand | Imports editorial base data from POC `techniques_v2.json` into `outcomes_index.json` and `session_time` frontmatter. Idempotent — use `--force` to overwrite, `--dry-run` to preview |
| `validate_base_data.py` | On-demand | Cross-checks all 58 `.md` files against POC JSON: outcomes present, session_time present, mechanism present, step count matches, grade drift warnings. Exit code 1 on critical issues. Writes `.hermes/validation_report.json` |
| `migrate_from_poc.py` | One-time | Historical — initial migration from POC JSON to markdown files. Not needed for ongoing operation |

#### Data Sources (single source of truth)

| Data | Source | Updated |
|------|--------|---------|
| Technique editorial content (description, example, steps, mechanism) | `techniques/*.md` frontmatter + body | Manual edits |
| Papers (title, year, pubtype, sample, effect, DOI) | `data/papers_index.json` | Weekly pipeline |
| Outcome grades (per cognitive outcome, per technique) | `data/outcomes_index.json` | Manual edits (drift-detected weekly) |
| Evidence grades (overall A–D per technique) | `techniques/*.md` frontmatter `grade` field | Weekly pipeline |
| Grade history (52-week rolling log) | `.hermes/grade_history.json` | Weekly `detect_grade_drift.py` |

## Commands

### Website
```bash
npm run dev       # Start dev server on http://0.0.0.0:4321
npm run build     # Build site to dist/
npm run preview   # Preview built site on http://0.0.0.0:4321
```

### Pipeline (Python)
```bash
# Weekly automated pipeline
python scripts/search_papers.py
python scripts/update_markdown.py
python scripts/grade_technique.py
python scripts/build_pr.py

# Post-pipeline health checks
python scripts/detect_outcome_drift.py
python scripts/detect_grade_drift.py
python scripts/assess_paper_health.py

# On-demand editorial maintenance
python scripts/import_base_data.py        # Import base data from POC
python scripts/import_base_data.py --dry-run  # Preview changes
python scripts/validate_base_data.py      # Cross-check data consistency
```

## Tech Stack

- **Astro 6** — static site generator
- **No UI framework** — vanilla CSS with custom properties (light/dark)
- **No database** — all content in version-controlled markdown
- **Pipeline** — Python scripts + Hermes cron + gh CLI

## Colophon

Techniques and grades from the original Proof of Concept by C Barnes.
PubMed search pipeline and website built with Hermes Agent.
