# Focus Hacking — Agent Guide

Two systems share `techniques/` as source of truth:

```
techniques/      ← 58 markdown files (shared)
src/             ← (A) Astro website
scripts/         ← (B) PubMed research pipeline
config/          ← pipeline config (techniques.yaml, grading-rules.yaml)
data/            ← papers_index.json
package.json     ← Astro deps
requirements.txt ← Python deps (pyyaml>=6.0)
```

---

## (A) Astro Website — `src/`

**Stack:** Astro 6, TypeScript, vanilla CSS (custom properties), vanilla JS.
**Output:** Static HTML in `dist/`.

### Key files

| File | Purpose |
|------|---------|
| `src/pages/index.astro` | Listing — cards, filters, search, sort |
| `src/pages/techniques/[...slug].astro` | Technique detail pages |
| `src/layouts/BaseLayout.astro` | Shell: nav, footer, SEO, theme toggle |
| `src/components/TechniqueCard.astro` | Card used in listing |
| `src/content.config.ts` | Zod schema for frontmatter |
| `src/styles/global.css` | All CSS |
| `astro.config.mjs` | Site URL, trailing slash, sitemap |
| `src/pages/404.astro` | 404 page |
| `src/pages/rss.xml.js` | RSS feed |

### Commands

```bash
npm run dev       # http://0.0.0.0:4321
npm run build     # dist/
npm run preview   # Preview built site
npx astro check   # Type-check
```

### Content

`techniques/*.md` at repo root. Symlinked to `src/content/techniques`.
Each file has YAML frontmatter: `title`, `slug`, `grade`, `category`,
`difficulty`, `time_to_benefit`, `populations`, `focus_facets`, `summary`,
plus body (instructions, mechanism, papers).

See `WEB-TESTING.md` for testing. See `DESIGN.md` for design roadmap.

---

## (B) PubMed Research Pipeline — `scripts/`

**Stack:** Python 3 (stdlib + pyyaml), `urllib.request` for E-utilities.
**Trigger:** Hermes cron (weekly).

### Scripts

| Script | Purpose |
|--------|---------|
| `search_papers.py` | PubMed search + fetch, rate limited, deduped |
| `grade_technique.py` | Rule-based grade from `config/grading-rules.yaml` |
| `update_markdown.py` | Appends new papers to `techniques/*.md` |
| `build_pr.py` | Git branch + commit + GitHub PR |
| `migrate_from_poc.py` | One-time PoC data import |

### Pipeline

```
PubMed → search_papers.py → papers_index.json
                                   ↓
                           grade_technique.py
                                   ↓
                           update_markdown.py
                                   ↓
                           techniques/*.md ← Astro reads
                                   ↓
                           astro build → dist/
```

### Config

| File | Purpose |
|------|---------|
| `config/techniques.yaml` | PubMed queries + MeSH terms per technique |
| `config/grading-rules.yaml` | A/B/C/D/? thresholds |
| `data/papers_index.json` | Paper database (version-controlled) |

### Commands

```bash
python scripts/search_papers.py
python scripts/grade_technique.py
python scripts/update_markdown.py
python scripts/build_pr.py
```

---

## Shared Boundary

`techniques/*.md` is single source of truth. Pipeline writes, Astro reads.
When schema changes, update both:

1. `src/content.config.ts` — Astro Zod schema
2. `scripts/grade_technique.py` — pipeline field handling
3. `config/grading-rules.yaml` — if grade rules change
