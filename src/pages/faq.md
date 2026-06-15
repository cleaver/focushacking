---
layout: ../layouts/TermsLayout.astro
title: "Frequently Asked Questions"
description: "Frequently asked questions about Focus Hacking — evidence-graded focus techniques and research."
---

# Frequently Asked Questions

_Last updated: 15 June, 2026_

## What is Focus Hacking?

Focus Hacking is a free, evidence-graded directory of focus and attention techniques. Each technique is rated A–D based on the strength of available peer-reviewed research — a methodology adapted from evidence-based medicine grading systems, applied to behavioural and cognitive interventions.

## How are grades determined?

Grades are calculated by a pipeline that reads papers from PubMed and applies a rule-based rubric:

| Grade | Meaning |
|-------|---------|
| **A** | Strong evidence — ≥3 RCTs or large meta-analysis, consistent results, moderate-to-large effect |
| **B** | Good evidence — ≥2 RCTs or meta-analysis, mostly consistent, small-to-moderate effect |
| **C** | Limited evidence — 1–2 RCTs or mixed results, methodological limitations |
| **D** | Weak evidence — primarily observational, self-report, or single underpowered study |
| **?** | Insufficient evidence — no peer-reviewed studies found |

The full [grading rubric](/grading-rubric) explains the criteria and methodology in detail.

## A technique I use works for me. Why do you give it a low rating?

Individual results may vary. Even in studies where a clear majority of participants show a benefit — say 80% — that means 20% of people experienced no benefit or even a negative effect. Your personal experience is real and valid, but it doesn't necessarily reflect the average outcome across the wider population.

Our grades are based on the strength of the overall evidence from aggregate research, not on individual anecdotes or testimonials. A low grade means the scientific literature is limited or mixed, not that the technique is useless. You should keep using what works for you.

## A technique I tried doesn't work for me. Why do you give it a high rating?

A high grade means the preponderance of published research shows a positive effect *on average* across study populations. It does not guarantee the technique will work for every individual. Factors like genetics, environment, baseline habits, consistency of practice, and the specific outcome being measured can all influence whether a given technique is effective for you personally.

Studies may also use specific protocols or supervision that differ from how you applied the technique on your own. If something doesn't work for you, it may be worth adjusting how you practice it — or it may simply not be the right fit for your brain.

## How often is the research updated?

PubMed is searched weekly via an automated pipeline. New papers are added to the index, grades are recalculated, and changes are opened as a GitHub PR for human review. The "last searched" date appears in each technique's detail page.

## Can I trust the letter grades?

The grades reflect our editorial interpretation of the available evidence. They are not clinical guidelines or medical advice. Evidence changes over time, and we may not include every study. You should independently evaluate whether a technique is appropriate for you.

## What kind of techniques are listed?

We cover 58 techniques across 7 categories:

- **Time Management** — Pomodoro, Time Blocking, Eat the Frog, etc.
- **Mindfulness** — Meditation, Body Scan, Gratitude Practice, etc.
- **Breathing** — Box Breathing, 4-7-8 Breathing, Cyclic Sighing, etc.
- **Physical** — Aerobic Exercise, Power Nap, Kettlebell Training, etc.
- **Environment** — Clean Desk, Noise-Cancelling Headphones, Optimal Temperature, etc.
- **Cognitive** — Deep Work, Spaced Repetition, Interleaving Practice, etc.
- **Technology** — Website Blockers, Grayscale Mode, Notification Batching, etc.

## Where do the studies come from?

All studies are sourced from PubMed, the National Library of Medicine's database of biomedical literature. Each paper link goes to the published article on PubMed or the journal's DOI page.

## Is this site free?

Yes. The site is and will remain free. No paywalls, no subscriptions, no account required.

## How can I suggest a technique or report an issue?

Techniques and data are managed through our GitHub repository. You can open an issue or pull request there. The research pipeline is automated, so corrections to paper metadata or grades can be submitted as PRs against `data/papers_index.json` or `data/outcomes_index.json`.

## Does the site use AI?

Yes. Large language models assist with searching for and summarizing papers, drafting technique descriptions, and suggesting population and focus-facet tags. All AI-generated content is reviewed before publication. See the [Terms of Use](/terms) for more details.
