# Future Enhancements

Tracked here rather than issues to keep them in-repo and visible during
development. No timeline, no priority order — just ideas worth keeping.

## Pipeline & Grading

- [ ] **Directness tag** — Add a `directness` field ("direct" / "proxy") to
      paper tagging. Papers that test the named technique directly get full
      grade weight; proxy evidence (related mechanism, different intervention)
      is capped. Requires LLM judgment during the tagging step.
  - Ivy Lee Method D→A and Time Blocking C→A are false positives from
    proxy-blind counting (see PR #3 review).
- [ ] **Per-outcome grading** — Store grades per focus facet
      (distraction_resistance, studying_learning, etc.) instead of one grade
      per technique. The PoC data already has per-outcome grades in the
      `outcomes` array.
  - Schema change to frontmatter. Site needs to display it too.
- [ ] **Confidence bands** — Show a confidence interval or "data quality" tag
      alongside each grade. A technique with 1 tiny RCT and one with 5 large
      meta-analyses both get "B" — the reader can't tell them apart.
  - Options: attach the paper count, or show "B (3 studies)" / "B (12 studies)"
- [ ] **Effect size from PubMed** — PubMed EFetch XML sometimes includes
      statistical data in the abstract text. Could regex for "d=", "g=",
      "p<", "Cohen's" patterns to auto-extract effect sizes instead of relying
      entirely on LLM extraction.
- [ ] **Semantic Scholar fallback** — When PubMed returns few results, query
      Semantic Scholar API as a secondary source. Was rate-limited in testing
      (100 req/5min without key). With free API key: 1 req/s sustained.

## Data Sources

- [ ] **New technique discovery** — PubMed topic clustering to suggest
      candidate techniques not yet in the config. The search script could flag
      frequently co-occurring keywords that aren't tracked.
- [ ] **Retraction watch** — Check for retracted or corrected papers before
      including them in the digest. The Retraction Watch API or PubMed's own
      status flags could catch this.
- [ ] **Citation tracking** — When a landmark paper is found, use Semantic
      Scholar's citation graph to find newer papers that cite it. Catches
      follow-up studies the author might have missed.

## Site & Content

- [ ] **Static site generator integration** — Transform `techniques/` markdown
      into a real site. Hugo, 11ty, Astro, or plain HTML generation script.
      Out of scope for the pipeline, but the data format should support it.
- [ ] **Tag review UI** — The PR body's "Papers Needing Tag Review" section
      shows which new papers lack MeSH. A future enhancement could batch all
      untagged papers into a single review issue each month.

## Infrastructure

- [ ] **GitHub Pages deployment** — Auto-deploy the static site when a PR is
      merged to main. GitHub Actions (if used later) or a webhook.
- [ ] **Multi-profile cron** — Run the pipeline on different schedules for
      different Hermes profiles (e.g., personal vs. work).
- [ ] **PR auto-merge** — If no grade changes and only 1-2 new papers with
      MeSH tags, auto-merge the PR. Risky — needs good confidence first.
