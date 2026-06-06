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
│   └── grading-rules.yaml    # A/B/C/D/? thresholds
│
├── data/
│   └── papers_index.json     # Persistent paper database (version-controlled)
│
├── scripts/                  # PubMed research pipeline
│   ├── search_papers.py      # PubMed E-utilities + rate limiting + dedup
│   ├── grade_technique.py    # Rule-based grade recalculation
│   ├── update_markdown.py    # Appends new papers to .md files
│   ├── build_pr.py           # Git branch + commit + PR creation
│   └── migrate_from_poc.py   # Import tool for PoC data
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
plus body text with papers, instructions, and mechanism notes.

The `techniques/` directory is the single source of truth. Both the
pipeline scripts and the Astro website read from it.

### Website (Astro)
- **Static HTML** — all pages pre-rendered at build time. No server, no DB.
- **58 individual technique pages** at `/techniques/pomodoro-technique/` etc.
- **Listing page** at `/` — pre-rendered cards with client-side filtering
  by category, grade, search, and sort. JSON data embedded in the page
  for instant filtering (no network calls).
- **Dark mode** — defaults to system preference (`prefers-color-scheme`),
  toggle stored in localStorage.
- **RSS feed** at `/rss.xml`.

### Research Pipeline (Hermes cron)
A weekly cron job searches PubMed for new papers, uses an LLM to tag
populations and focus facets, recalculates grades, and opens a PR:

1. `search_papers.py` — PubMed E-utilities, rate limited, deduped
2. LLM tagging — populations, facets, effect sizes from abstracts
3. `grade_technique.py` — rules-based grading (study type, sample size,
   effect size, consistency)
4. `update_markdown.py` — appends new papers to markdown files
5. `build_pr.py` — creates git branch + GitHub PR for review

## Commands

```bash
npm run dev       # Start dev server on http://0.0.0.0:4321
npm run build     # Build site to dist/
npm run preview   # Preview built site on http://0.0.0.0:4321
```

## Tech Stack

- **Astro 6** — static site generator
- **No UI framework** — vanilla CSS with custom properties (light/dark)
- **No database** — all content in version-controlled markdown
- **Pipeline** — Python scripts + Hermes cron + gh CLI

## Colophon

Techniques and grades from the original Proof of Concept by C Barnes.
PubMed search pipeline and website built with Hermes Agent.
