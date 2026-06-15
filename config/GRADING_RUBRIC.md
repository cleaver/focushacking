# Focus Hacking Evidence Grading Rubric

---

## Grade Scale: A → D (+ "Insufficient")

| Grade | Label | Criteria |
|-------|-------|----------|
| **A** | Strong evidence | ≥3 RCTs or ≥1 large meta-analysis (n≥500), consistent results (≥70% agreement), moderate-to-large effect size (Cohen's d ≥0.5 or significant p<0.01) |
| **B** | Good evidence | ≥2 RCTs or 1 meta-analysis (n≥100), mostly consistent (≥60% agreement), small-to-moderate effect (d≥0.3) |
| **C** | Limited evidence | 1–2 RCTs or mixed results, inconsistent findings, small effects (d<0.3) or methodological limitations |
| **D** | Weak/theoretical evidence | Primarily observational, self-report, no RCTs, or single underpowered study (n<30) |
| **NI** | No/insufficient evidence | No studies directly testing this outcome, or technique is entirely theory/logic-based |

## Study Quality Hierarchy (highest → lowest)
1. Pre-registered RCT with active control, blinding, large n
2. RCT (non-blinded or small n)
3. Systematic review / meta-analysis of observational studies
4. Prospective cohort study
5. Cross-sectional or retrospective study
6. Expert consensus / theoretical framework

## Outcome Dimensions (per technique, not all apply to all)

For behavioural/cognitive focus techniques we measure:

| Outcome | Description |
|---------|-------------|
| **Sustained Attention** | Ability to maintain focus on a task over time |
| **Working Memory** | Capacity to hold and manipulate information in mind |
| **Task Completion** | Rate of completing defined tasks or goals |
| **Stress Reduction** | Measurable reduction in cortisol, self-reported stress, or anxiety |
| **Cognitive Flexibility** | Ability to switch between tasks or mental sets |
| **Sleep Quality** | Improvements to sleep onset, duration, or quality (where relevant) |
| **Reaction Time** | Speed of mental processing |
| **Mood / Affect** | Positive affect, reduced negative mood, well-being |

Not all outcomes apply to all techniques. Each technique gets graded only on
outcomes that have been directly studied.

## Evidence Type Preference
- Primary: Human RCTs only get full grade weight
- Secondary: Meta-analyses of RCTs
- Tertiary: Observational/correlational (noted, but capped at grade C)
- Excluded from grade: Animal studies, purely theoretical

## Study Card Fields (per study)
- title (full paper title)
- authors (first author + et al. if >2)
- year
- n (sample size)
- design ("RCT", "Meta-analysis", "Cohort", "Cross-sectional")
- finding (1 sentence key result)
- effect ("Large increase", "Moderate increase", "Small increase", "No effect", "Mixed")
- pubmed_url OR doi_url (direct link)

## Design Notes
1. We grade BEHAVIOURAL interventions (not pills), so blinding is often impossible → we note this
2. We include observational evidence but cap it at grade C and flag it
3. We show 2–4 studies per technique (not 170) but make each one real and linked
4. We add a "Mechanism" note explaining WHY it works
5. We use the A–D + NI scale with criteria calibrated for behavioural science

---

*See `config/grading-rules.yaml` for the machine-readable rules used by the pipeline.*
