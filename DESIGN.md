# Design Notes — POC Site Analysis

> Source: https://calm-meadow-4cd0.cbarnes.workers.dev/
> Context: Original proof-of-concept for Focus Hacking. Single-page app (Cloudflare Worker).
> Current site: Astro static site at focushacking.com.

## Architecture: SPA vs Static

**POC:** Full SPA. All technique data embedded in a single JS bundle (Cloudflare Worker).
No separate technique pages. Detail views rendered as modals via client-side JS.
URL never changes. No SSR, no SEO for individual techniques.

**Current (Astro):** Static HTML. Each technique is a pre-rendered page at
`/techniques/[slug]/`. Listing page has embedded JSON + client-side filter/sort.
No server, no JS framework — vanilla JS for interactivity.

**Recommended direction (static + modal-enhanced navigation):**

> Page-first, modal-enhanced routing. Each technique exists as a full static page
> at `/techniques/[slug]/`. When user clicks from the listing, intercept navigation
> and render destination content in a modal overlay while updating URL to
> `/techniques/[slug]/`. Direct visit, refresh, copy-paste, and search engines
> all see the standalone page.

```
Direct visit → /techniques/pomodoro-technique/ → full page
Click from / → intercept click → modal overlay, URL becomes /techniques/pomodoro-technique/
Close modal → history.back() → back to / with filters preserved
```

This gives best of both: SEO/SSR for each technique + fast, fluid browsing from
the listing.

---

## Visual Design

### Color Palette (POC)

| Role | Light Mode | Notes |
|------|-----------|-------|
| Header bg | Dark navy (#1a1a2e est.) | Full-width bar, white text |
| Page bg | White (#fff) | Clean, minimal |
| Card/row bg | White | Table rows with subtle dividers |
| Text primary | Near-black (#333) | Body and headings |
| Text muted | Gray (#666/#888) | Labels, descriptions |
| Accent / links | Blue (#2563eb) | View buttons, links |
| Grade A | Green (#16a34a) | Badge background |
| Grade B | Blue (#2563eb) | Badge background |
| Grade C | Amber (#d97706) | Badge background |
| Grade D | Red (#dc2626) | Badge background |
| Grade ? | Gray (#78716c) | Badge background |

Category filter pills each have distinct colors (e.g., Time Mgmt = blue,
Mindfulness = green, Breathing = teal, Physical = orange, etc.)

### Dark Mode (Current Site)

Current Astro site has dark mode via CSS custom properties + `.dark` class on
`<html>`. POC has no dark mode. Keep current approach.

### Typography

POC uses system font stack (no custom fonts loaded):
```css
font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
  Oxygen, Ubuntu, Cantarell, sans-serif;
```

Current Astro site uses same system stack. No change needed — keeps load fast,
no Google Fonts dependency.

### Icons

POC uses emoji/unicode for icons in the stats bar:
- 📋 58 TECHNIQUES
- 🗂️ 7 CATEGORIES
- 📊 A–D EVIDENCE GRADES
- 💯 100% FREE

Navigation icons: ⚡ for logo/brand.

Current site uses ⚡ for brand, 🌙/☀️ for theme toggle. Cards use colored grade
badges. No icon library needed — keep using emoji for simplicity.

### Spacing & Radius

POC uses generous spacing:
- `border-radius: 8px` on cards and buttons
- `border-radius: 9999px` on pill filters
- `padding: 12-16px` on cards
- `gap: 8-12px` between elements

Current site matches closely. Keep consistent.

---

## Page Layout (Hierarchy)

### 1. Header / Nav

```
[⚡ Focus Hacking]  [Techniques] [RSS] [🌙]
```

Current: clean, minimal. POC has similar but simpler. Keep current.

### 2. Stats Bar (POC feature — not in current site)

```
┌──────────────────────────────────────────────────────────────┐
│ 📋 58 TECHNIQUES  🗂️ 7 CATEGORIES  📊 A–D GRADES  💯 FREE  │
└──────────────────────────────────────────────────────────────┘
```

Four stat cards in a horizontal row. Each has an icon + label + value.
Consider adding to current site above the filter area.

### 3. Evidence Grade Legend (POC feature — not in current site)

```
A → Strong — ≥3 RCTs or large meta-analysis, consistent, moderate-to-large effect
B → Good — ≥2 RCTs or 1 meta-analysis, mostly consistent, small-to-moderate effect
C → Limited — 1-2 RCTs or mixed results, methodological limitations
D → Weak — Primarily observational, self-report, or single underpowered study
```

Compact table or stacked list. Each row has grade badge + short description.
Consider adding as collapsible or always-visible above filters.

### 4. Filters & Search

Current: category pills + grade pills + search input + sort select.

POC has same filters plus:
- **Result counter**: "58 of 58 techniques shown"
- **Clear all filters**: link/button that resets everything
- Both are useful UX additions.

### 5. Technique Listing

**POC (table layout):**
```
GRADE | TECHNIQUE | CATEGORY | DESCRIPTION | DIFFICULTY | TIME TO BENEFIT | DETAILS
  C   | Pomodoro  | Time Mgmt| Work in...  | Beginner   | Immediate       | [View]
```

Table is information-dense but can feel cramped on mobile. Each row shows all
metadata inline.

**Current (card grid):**
```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ C Pomodoro      │ │ A Time Blocking │ │ D Eat the Frog  │
│ Time Management │ │ Time Management │ │ Time Management │
│ Work in focused…│ │ Assign every…   │ │ Begin each…     │
│ Beginner · Imm  │ │ Intermed · 1-2w │ │ Beginner · Imm  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

Cards are more visual, responsive, and touch-friendly. Metadata is visible but
summary-only. Full details require navigating to technique page.

**Recommendation:** Keep card grid for listing. Cards are mobile-first and
scannable. The table approach can supplement as a toggle option ("Card view" /
"Table view") if desired later.

### 6. Technique Detail

**POC:** Modal overlay triggered by "View" button. Content includes:
- Grade badge, title, category
- Summary/description
- What it is, how to do it, mechanism
- Research papers list
- Close button → back to listing

**Current:** Separate static page at `/techniques/[slug]/` with:
- Grade badge, title, category
- Grade detail, difficulty, time to benefit, papers count
- Populations, focus facets
- Full rendered markdown (what_it_is, how_to_do_it, mechanism, papers)
- "← Back to all techniques" link

**Recommended enhancement (modal-enhanced navigation):**

Implement modal-enhanced routing:
1. Click technique card on listing → intercept click via JS
2. Fetch `/techniques/[slug]/` content via `fetch()` (or embed in JSON data)
3. Open modal overlay with the technique content
4. Update URL via `history.pushState()` to `/techniques/[slug]/`
5. Close modal → `history.back()` → back to listing with filters intact
6. Direct visit to `/techniques/[slug]/` → normal full page (no JS needed)

This requires:
- Technique data (or rendered HTML) available client-side
- Modal component (HTML + CSS overlay)
- History API navigation
- Focus trap inside modal
- Keyboard: Escape closes modal

### 7. Footer

Current: "Evidence-graded directory of focus techniques. Updated weekly via PubMed."

POC has more detailed footer:
```
FocusHacking.com
Evidence grades follow a methodology adapted from Examine.com: A–D based on
number of RCTs, consistency, and effect size. All study links go to PubMed or
journal DOIs. Grades reflect evidence for cognitive focus outcomes specifically.
```

Consider expanding footer with methodology attribution + links.

---

## Functionality Checklist

### Current site has:
- [x] Client-side category filtering (pills)
- [x] Client-side grade filtering (pills)
- [x] Client-side search (text input)
- [x] Client-side sort (dropdown)
- [x] Dark mode toggle (localStorage + prefers-color-scheme)
- [x] Static technique pages (SSR)
- [x] RSS feed
- [x] Sitemap
- [x] OG/Twitter meta tags
- [x] 404 page

### POC has that current site could adopt:
- [ ] Stats bar (techniques, categories, grades, free)
- [ ] Evidence grade legend table
- [ ] "X of Y techniques shown" counter
- [ ] "Clear all filters" action
- [ ] Modal-enhanced navigation (page-first, modal routing)
- [ ] Table view as alternative to card grid
- [ ] Expanded footer with methodology

### Future possibilities (in FUTURE.md or new):
- Per-outcome grading display
- Confidence bands / paper count badges
- Directness tags on evidence
- Tag review UI for pipeline

---

## Technical Implementation Notes

### Modal-Enhanced Navigation Pattern

```astro
---
// src/pages/index.astro
// Embed technique data (already done via JSON in hidden div)
---
<script>
  // Intercept card clicks
  document.getElementById("grid").addEventListener("click", async (e) => {
    const card = e.target.closest(".card");
    if (!card) return;
    e.preventDefault();

    const url = card.getAttribute("href");
    const slug = url.replace(/\/techniques\//, "").replace(/\/$/, "");

    // Show modal with technique data from embedded JSON
    showTechniqueModal(slug);

    // Update URL
    history.pushState({ slug }, "", url);
  });

  // Handle back/forward navigation
  window.addEventListener("popstate", (e) => {
    if (e.state?.slug) {
      showTechniqueModal(e.state.slug);
    } else {
      closeTechniqueModal();
    }
  });

  // Close on Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeTechniqueModal();
  });
</script>
```

### Modal Overlay CSS

```css
.modal-overlay {
  position: fixed; inset: 0; z-index: 50;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  overflow-y: auto;
}
.modal-content {
  background: var(--color-surface);
  border-radius: 12px;
  max-width: 48rem;
  width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
  padding: 2rem;
  position: relative;
}
```

### Data Flow

For modal to work without network requests, technique data needs:
- All frontmatter fields (already in `jsonData` variable)
- Rendered HTML for the technique body

Options:
1. **Embed full HTML** — Include rendered technique body in JSON (larger payload)
2. **Fetch on demand** — `fetch(/techniques/${slug}/index.html)` and extract content
3. **Template client-side** — Render from structured data (papers, instructions, mechanism)

Option 1 is simplest for static sites. Option 2 works if technique pages have
a predictable content selector. Option 3 is most flexible but duplicates
rendering logic.

### Dark Mode Compatibility

Theme toggle must persist across modal open/close. Since modal is rendered
client-side, it inherits current theme from `<html class="dark">` + CSS
custom properties. No special handling needed.

### SEO Considerations

- Each technique MUST remain accessible at its own URL (direct visit = full page)
- Modal navigation uses `history.pushState` — search engines see canonical URLs
- `popstate` handler ensures browser back/forward work correctly
- No `#` fragment routing — use real paths

---

## Visual Alignment Checklist — Current Site → POC

Changes needed to match POC visual design. Each item links to the relevant
section above.

### Header / Navigation

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| H1 | Change header bg to dark navy (`#1a1a2e` or similar dark bg for both modes) | `BaseLayout.astro` | High | [x] |
| H2 | Header text white (`#fff`) instead of accent color | `BaseLayout.astro` | High | [x] |
| H3 | Remove header bottom border, use solid bg instead | `BaseLayout.astro` | Medium | [x] |
| H4 | Dark mode: header bg stays dark (e.g., `#0a0a1a`) | `BaseLayout.astro` | High | [x] |
| H5 | Nav links white in light mode, adjust hover states | `BaseLayout.astro` | Medium | [x] |

### Stats Bar *(new section)*

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| S1 | Add 4-card stats row below page title: techniques count, categories, grades, free | `index.astro` | High | [x] |
| S2 | Icon + value + label layout per card (📋 58 TECHNIQUES, etc.) | `index.astro` | High | [x] |
| S3 | Stats cards styled with border, rounded, subtle bg | `global.css` | High | [x] |
| S4 | Responsive: 4 columns → 2 columns → stacked on mobile | `global.css` | Medium | [x] |
| S5 | Dark mode variants for stats cards | `global.css` | High | [x] |

### Evidence Grade Legend *(new section)*

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| L1 | Add grade legend table below stats bar or above filters | `index.astro` | Medium | [ ] |
| L2 | Each row: color-coded badge + letter + short description | `index.astro` | Medium | [ ] |
| L3 | Compact layout — single row or 2×2 grid | `global.css` | Low | [ ] |
| L4 | Option: collapsible "How grades work" toggle | `index.astro` | Low | [ ] |

### Filter Pills

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| F1 | Distinct background colors per category pill (not just accent) | `index.astro`, `global.css` | Medium | [ ] |
| F2 | Category colors: Time Mgmt=blue, Mindfulness=green, Breathing=teal, Physical=orange, Environment=amber, Cognitive=purple, Technology=slate | `global.css` | Medium | [ ] |
| F3 | Active pill state: filled bg with white text (POC style) | `global.css` | Medium | [ ] |
| F4 | Inactive pill state: outlined with muted text (POC style) | `global.css` | Low | [ ] |
| F5 | Grade pills keep same style but use grade colors | `global.css` | Low | [ ] |

### Result Counter & Clear Filters *(new)*

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| R1 | Add "X of 58 techniques shown" text below filter pills or above grid | `index.astro` | High | [ ] |
| R2 | Update counter dynamically in `filter()` JS function | `index.astro` (script) | High | [ ] |
| R3 | Add "Clear all filters" link/button next to counter | `index.astro` | Medium | [ ] |
| R4 | Wire clear button to reset all pills + search + sort to defaults | `index.astro` (script) | Medium | [ ] |

### Search & Sort Controls

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| C1 | Match POC search input styling (slightly different border-radius/padding) | `global.css` | Low | [ ] |
| C2 | Match POC sort select styling | `global.css` | Low | [ ] |

### Technique Cards (Listing)

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| T1 | Match POC card/row hover effect (subtle shadow or bg shift) | `global.css` | Low | [ ] |
| T2 | Ensure consistent border-radius across all cards | `global.css` | Low | [ ] |
| T3 | Consider "View details" link at bottom of card (like POC's "View" button) | `TechniqueCard.astro` | Low | [ ] |

### Technique Detail Page

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| D1 | Match POC's content structure: title, grade, summary, what/why/how sections | `[...slug].astro` | Low | [ ] |
| D2 | Add paper count badge or "N studies tracked" styling consistent with POC | `[...slug].astro` | Low | [ ] |

### Footer

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| FT1 | Expand footer text with methodology attribution (adapted from Examine.com, A–D based on RCTs etc.) | `BaseLayout.astro` | Medium | [ ] |
| FT2 | Add "Focus Hacking home" link | `BaseLayout.astro` | Low | [ ] |
| FT3 | Add "EVIDENCE-GRADED · SCIENCE-BACKED · FREE" tagline from POC | `BaseLayout.astro` | Low | [ ] |

### Color Tokens

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| CL1 | Add CSS custom properties for each category pill color (light + dark) | `global.css` | Medium | [x] |
| CL2 | Verify grade colors match POC exactly (green/blue/amber/red/gray) | `global.css` | Low | [ ] |
| CL3 | Add header-specific color tokens (light + dark) | `global.css` | High | [x] |

### Typography

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| TY1 | Keep system font stack (POC uses same) — no change | — | — | [ ] |
| TY2 | Verify heading sizes match POC proportions | `global.css` | Low | [ ] |
| TY3 | Verify body text sizes match POC | `global.css` | Low | [ ] |

### Icons

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| I1 | Add emoji icons to stats bar (📋 🗂️ 📊 💯) | `index.astro` | High | [ ] |
| I2 | Keep ⚡ for brand, 🌙/☀️ for theme toggle (current) | — | — | [ ] |
| I3 | No icon library needed — emoji-only keeps bundle zero | — | — | [ ] |

### Spacing & Radius

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| R1 | Verify card padding matches POC (`16px` — current uses `1rem` = `16px`, OK) | — | — | [ ] |
| R2 | Verify filter pill border-radius matches POC (`9999px` — current matches) | — | — | [ ] |
| R3 | Verify gap between filter pills matches POC | `global.css` | Low | [ ] |

### Responsive Breakpoints

| # | Change | File | Priority | Done |
|---|--------|------|----------|------|
| BP1 | Stats bar: 4-col → 2-col at `640px` → 1-col at `480px` | `global.css` | Medium | [ ] |
| BP2 | Grade legend: inline on desktop, stacked on mobile | `global.css` | Low | [ ] |
| BP3 | Card grid: 3-col → 2-col → 1-col (already done) | — | — | [x] |

---

## Accessibility Checklist

### Color & Contrast

| # | Requirement | WCAG | Status | Done |
|---|-------------|------|--------|------|
| A1 | Grade badges: white text on colored bg — verify contrast ≥ 4.5:1 against all grade colors | 1.4.3 AA | ⚠️ Verify A (green) and D (red) with white text | [ ] |
| A2 | Dark mode grade badges: verify contrast against dark bg variants | 1.4.3 AA | ⚠️ Verify | [ ] |
| A3 | Text on page bg: `--color-text` vs `--color-bg` ratio ≥ 4.5:1 | 1.4.3 AA | ✓ Likely OK (near-black on near-white) | [ ] |
| A4 | Muted text (`--color-text-muted`): verify ≥ 4.5:1 for body text, 3:1 for decorative | 1.4.3 AA | ⚠️ Check light mode `#57534e` on `#fafaf9` | [ ] |
| A5 | Link/active accent color: verify contrast against bg | 1.4.3 AA | ⚠️ Check | [ ] |
| A6 | Focus indicators: all interactive elements must have visible focus ring | 2.4.7 AA | ❌ Missing — add `:focus-visible` outlines | [ ] |
| A7 | Dark mode: re-verify all contrast ratios with dark palette | 1.4.3 AA | ⚠️ Verify | [ ] |
| A8 | Category pills with distinct colors: ensure color is not sole differentiator — pair with text label | 1.4.1 A | ✓ Already have text labels | [x] |

### Semantic HTML

| # | Requirement | WCAG | Status | Done |
|---|-------------|------|--------|------|
| A9 | Page has one `<h1>` (already true — technique title or "Focus Hacking") | 1.3.1 A | ✓ | [x] |
| A10 | Heading hierarchy: `h1` → `h2` → `h3`, no skips | 1.3.1 A | ✓ Technique detail uses h2/h3 correctly | [x] |
| A11 | Filter pills are `<button>` elements (already true) | 4.1.2 A | ✓ | [x] |
| A12 | Search input has associated `<label>` or `aria-label` | 1.3.1 A | ❌ Missing — add `aria-label="Search techniques"` | [ ] |
| A13 | Sort select has associated `<label>` or `aria-label` | 1.3.1 A | ❌ Missing — add `aria-label="Sort by"` | [ ] |
| A14 | Technique cards use `<a>` with valid `href` (already true) | 4.1.2 A | ✓ | [x] |
| A15 | Nav `<nav>` element or `role="navigation"` | 1.3.1 A | ⚠️ Current `<nav>` tag exists — OK | [x] |
| A16 | Main content in `<main>` (already true) | 1.3.1 A | ✓ | [x] |
| A17 | Footer content in `<footer>` (already true) | 1.3.1 A | ✓ | [x] |

### Keyboard Navigation

| # | Requirement | WCAG | Status | Done |
|---|-------------|------|--------|------|
| K1 | All filter pills focusable and activatable via keyboard (Tab + Enter/Space) | 2.1.1 A | ✓ (native `<button>`) | [x] |
| K2 | Search input keyboard-operable (native `<input>`) | 2.1.1 A | ✓ | [x] |
| K3 | Sort select keyboard-operable (native `<select>`) | 2.1.1 A | ✓ | [x] |
| K4 | Technique cards keyboard-navigable via Tab (native `<a>`) | 2.1.1 A | ✓ | [x] |
| K5 | Theme toggle keyboard-operable (native `<button>`) | 2.1.1 A | ✓ | [x] |
| K6 | Tab order matches visual order | 2.4.3 A | ✓ (DOM order) | [x] |
| K7 | No keyboard traps | 2.1.2 A | ✓ | [x] |
| K8 | Modal (future): focus trap inside modal when open | 2.1.2 A | ❌ Future — must implement | [ ] |
| K9 | Modal: close on Escape key | 2.1.2 A | ❌ Future — planned | [ ] |

### Screen Reader Support

| # | Requirement | WCAG | Status | Done |
|---|-------------|------|--------|------|
| S1 | Stats bar numbers announced correctly (use normal text, not CSS-generated) | 1.1.1 A | ⚠️ Ensure numbers are in HTML, not `::before`/`::after` | [ ] |
| S2 | Grade badges: include aria-label or screen reader text "Grade A" not just "A" | 1.1.1 A | ❌ Current `<span class="grade-badge">A</span>` — add `aria-label="Grade A"` | [ ] |
| S3 | Filter pills: active state announced — use `aria-pressed` or `aria-current` | 4.1.2 AA | ❌ Currently only visual `.active` class — add `aria-pressed` | [ ] |
| S4 | "X of Y techniques shown": use `aria-live="polite"` region for dynamic updates | 4.1.3 AA | ❌ Future — must implement | [ ] |
| S5 | Clear filters button: descriptive text or `aria-label` | 2.4.4 A | ❌ Future — implement | [ ] |
| S6 | Theme toggle has `aria-label="Toggle dark mode"` (already true) | 4.1.2 A | ✓ | [x] |
| S7 | Images: no `<img>` elements currently, but if added, require `alt` text | 1.1.1 A | ✓ | [x] |
| S8 | Modal (future): `role="dialog"`, `aria-modal="true"`, `aria-labelledby` | 4.1.2 AA | ❌ Future — planned | [ ] |
| S9 | Technique detail page: main heading matches `h1` (already true) | 1.3.1 A | ✓ | [x] |

### Motion & Animation

| # | Requirement | WCAG | Status | Done |
|---|-------------|------|--------|------|
| M1 | Respect `prefers-reduced-motion` — disable CSS transitions for card hover, modal open/close | 2.3.3 AAA | ❌ Add `@media (prefers-reduced-motion: no-preference)` wrapper | [ ] |
| M2 | Theme transition (`background 0.2s, color 0.2s`) — respect reduced motion | 2.3.3 AAA | ❌ Same fix | [ ] |
| M3 | Modal (future): add fade/scale animation only if motion allowed | 2.3.3 AAA | ❌ Future — planned | [ ] |

### Forms & Input

| # | Requirement | WCAG | Status | Done |
|---|-------------|------|--------|------|
| G1 | Search input needs associated `<label>` — either visible or `aria-label` | 1.3.1 A | ❌ Add `aria-label="Search techniques"` | [ ] |
| G2 | Sort select needs associated `<label>` or `aria-label` | 1.3.1 A | ❌ Add `aria-label="Sort techniques by"` | [ ] |
| G3 | Error state: "No techniques match your filters" — ensure it's announced to screen readers | 4.1.3 AA | ❌ Use `aria-live="polite"` on grid container | [ ] |

### Zoom & Responsiveness

| # | Requirement | WCAG | Status | Done |
|---|-------------|------|--------|------|
| Z1 | Page usable at 200% browser zoom (no horizontal scroll, no cut-off content) | 1.4.10 AA | ⚠️ Verify responsive layout | [ ] |
| Z2 | Text can be resized 200% without losing functionality | 1.4.4 AA | ✓ (relative units used) | [x] |
| Z3 | Touch targets ≥ 24×24px (AA) / 44×44px (AAA) | 2.5.8 AA / 2.5.5 AAA | ⚠️ Verify filter pills and buttons meet minimum | [ ] |

### Focus Management (Future Modal)

| # | Requirement | WCAG | Status | Done |
|---|-------------|------|--------|------|
| FM1 | Focus moves into modal when opened | 2.4.3 A | ❌ Future | [ ] |
| FM2 | Tab cycles within modal (focus trap) | 2.1.2 A | ❌ Future | [ ] |
| FM3 | Focus returns to triggering element when modal closes | 2.4.3 A | ❌ Future | [ ] |
| FM4 | Escape key closes modal | 2.1.2 A | ❌ Future | [ ] |

### HTML Validation

| # | Requirement | WCAG | Status | Done |
|---|-------------|------|--------|------|
| V1 | Page validates as HTML5 (no duplicate IDs, unclosed tags, etc.) | 4.1.1 A | ⚠️ Run validator | [ ] |
| V2 | Dynamic `grid.innerHTML` injections produce valid HTML | 4.1.1 A | ⚠️ Review template strings | [ ] |
| V3 | No duplicate `id` attributes across pages | 4.1.1 A | ✓ (static pages, single instance each) | [x] |

### Quick Wins (Easy Fixes)

Items that can be fixed immediately with minimal effort:

| # | Task | Done |
|---|------|------|
| Q1 | Add `aria-label="Search techniques"` to search input | [ ] |
| Q2 | Add `aria-label="Sort techniques by"` to sort select | [ ] |
| Q3 | Add `aria-label="Grade {letter}"` to grade badges (SSR + JS `grid.innerHTML`) | [ ] |
| Q4 | Add `aria-pressed` to filter pills — toggle with `.active` class in `toggleFilter()` | [ ] |
| Q5 | Add `aria-live="polite"` to grid container — so filter results are announced | [ ] |
| Q6 | Wrap CSS transitions in `@media (prefers-reduced-motion: no-preference)` | [ ] |
| Q7 | Add `:focus-visible` outline to all interactive elements | [ ] |
