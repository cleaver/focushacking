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
