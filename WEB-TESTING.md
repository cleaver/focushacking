# Web Testing — Astro Site

Testing strategy for the Astro static site only. Data pipeline scripts
(`scripts/`) are tested separately — see their docstrings.

## Tier 1 — Build & Content

### Type checking

```bash
npx astro check
```

Runs TypeScript checks across all `.astro` and `.ts` files. Catches:
- Missing frontmatter fields
- Incorrect prop types passed to components
- Schema violations in `content.config.ts`

Run before every build or PR.

### Content schema validation

Built into the Astro build. `content.config.ts` defines a Zod schema for
technique frontmatter:

```ts
schema: z.object({
  title: z.string(),
  slug: z.string(),
  category: z.string(),
  grade: z.string(),
  // ...
})
```

If a technique markdown file is missing a required field, `astro build`
fails with a descriptive error. No extra setup needed — just build.

### Broken internal links

Scan the built `dist/` for dead links:

```bash
npm install -D hyperlink
npx hyperlink dist/ --recursive --screenshots=false
```

Catches:
- Technique cards linking to wrong slugs
- Back-to-listing links pointing to missing pages
- RSS feed link targets that don't exist

### Smoke test

Quick sanity check after build:

```bash
npm run build
echo "Pages built: $(find dist -name 'index.html' | wc -l)"
```

Should output `60` (index + 58 techniques + 404).

---

## Tier 2 — HTML & Accessibility

### HTML validation

Validate all generated HTML for spec compliance:

```bash
npm install -D html-validate
npx html-validate dist/
```

Catches:
- Duplicate `id` attributes
- Unclosed tags
- Missing required attributes (`alt`, `lang`, etc.)
- Invalid ARIA attributes
- Bad nesting (e.g., `<button>` inside `<a>`)

### Automated accessibility checks

Run aXe-based audits against the dev server:

```bash
npm install -D pa11y
```

```bash
# Start dev server, then:
npx pa11y http://localhost:4321/
npx pa11y http://localhost:4321/techniques/pomodoro-technique/
npx pa11y http://localhost:4321/techniques/time-blocking/
npx pa11y http://localhost:4321/404/
```

Catches:
- Color contrast violations
- Missing form labels
- Missing ARIA roles/attributes
- Focus order problems
- Landmark structure issues

Test in both light and dark mode:

```bash
# Requires a quick eval to set localStorage before pa11y runs.
# Use Puppeteer/Playwright instead for dark mode a11y checks.
```

---

## CI (GitHub Actions)

Add `.github/workflows/test.yml`:

```yaml
name: Test (Astro site)
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: npm ci
      - run: npx astro check
      - run: npm run build
      - run: npx html-validate dist/
      - run: npx hyperlink dist/ --recursive --screenshots=false
```

---

## Per-Round Verification

When implementing checklist items from `DESIGN.md`, verify each change with:

| Check | Command |
|-------|---------|
| Build succeeds | `npm run build` |
| Page count correct | `find dist -name 'index.html' \| wc -l` |
| HTML valid | `npx html-validate dist/` |
| No dead links | `npx hyperlink dist/ --recursive --screenshots=false` |
| Visual: light mode | Open `dist/index.html` in browser |
| Visual: dark mode | Toggle theme, reload |
| Visual: mobile | DevTools responsive mode at 375px and 768px |
| Visual: technique page | Navigate to `/techniques/pomodoro-technique/` |
| Visual: 404 page | Navigate to `/nonexistent/` |

---

## Future (Tier 3–4)

- **Playwright screenshot diffing** — visual regression tests (see `DESIGN.md`)
- **Playwright E2E** — automated filter/search/sort/dark-mode interaction tests
- **Lighthouse CI** — performance, a11y, SEO scoring per PR
