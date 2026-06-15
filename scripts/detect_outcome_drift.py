#!/usr/bin/env python3
"""
Detect drift between outcomes data and the latest papers index.

Usage: python3 scripts/detect_outcome_drift.py

Cross-references data/outcomes_index.json against data/papers_index.json
and flags outcomes that may need human review:

  - New papers since outcomes were last reviewed
  - Paper effect directions that conflict with stated outcome effects
  - Outcomes with no supporting papers
  - Techniques with papers but no outcomes at all

Does NOT modify any files. Generates a report for human review.
Run after the weekly pipeline to surface stale outcomes.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
HERMES_DIR = os.path.join(BASE_DIR, ".hermes")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def effect_conflicts(outcome_effect, paper_direction, paper_magnitude):
    """
    Check if a paper's effect conflicts with a stated outcome effect.
    Returns True if there's a potential conflict worth flagging.
    """
    if not paper_direction:
        return False

    oe = outcome_effect.lower()
    pd = paper_direction.lower()
    pm = (paper_magnitude or "").lower()

    # Strong conflicts: outcome says positive, paper says negative/none/mixed
    if "increase" in oe or "improve" in oe:
        if pd in ("negative", "none", "mixed"):
            return True
    # Outcome says mixed, paper says strong positive or negative
    if "mixed" in oe:
        if pd == "positive" and pm in ("large", "moderate"):
            return True
        if pd == "negative" and pm in ("large", "moderate"):
            return True
    # Outcome says no effect, paper says positive
    if "no effect" in oe or "insufficient" in oe:
        if pd == "positive" and pm in ("large", "moderate"):
            return True

    return False


def analyze():
    papers_index = load_json(os.path.join(DATA_DIR, "papers_index.json"))
    outcomes_index = load_json(os.path.join(DATA_DIR, "outcomes_index.json"))

    papers = papers_index.get("papers", {})
    last_search = papers_index.get("metadata", {}).get("last_full_search", "unknown")

    flags = []  # Items needing human review
    stats = {
        "total_techniques_with_outcomes": len(outcomes_index),
        "total_papers": len(papers),
        "outcomes_with_new_papers": 0,
        "conflicting_effects": 0,
        "outcomes_without_papers": 0,
        "techniques_without_outcomes": 0,
    }

    # Build paper lookup by slug
    papers_by_slug = {}
    for pid, paper in papers.items():
        for slug in paper.get("technique_slugs", []):
            papers_by_slug.setdefault(slug, []).append(paper)

    # ── Check each technique with outcomes ──────────────────
    for slug, outcomes in outcomes_index.items():
        technique_papers = papers_by_slug.get(slug, [])

        if not technique_papers:
            stats["outcomes_without_papers"] += 1
            flags.append({
                "technique_slug": slug,
                "type": "outcomes_without_papers",
                "severity": "warning",
                "detail": f"Has {len(outcomes)} outcomes but no papers in index"
            })
            continue

        paper_years = sorted(set(p.get("year", 0) for p in technique_papers if p.get("year")))
        latest_paper_year = max(paper_years) if paper_years else 0
        paper_count = len(technique_papers)

        # Flag if there are recent papers (last 2 years) that may not be reflected
        current_year = datetime.now().year
        recent_papers = [p for p in technique_papers if p.get("year", 0) >= current_year - 1]

        if recent_papers:
            stats["outcomes_with_new_papers"] += 1
            flags.append({
                "technique_slug": slug,
                "type": "recent_papers",
                "severity": "info",
                "detail": f"{len(recent_papers)} papers from {current_year - 1}-{current_year} may not be reflected in outcomes",
                "recent_paper_titles": [p.get("title", "")[:80] for p in recent_papers[:3]]
            })

        # Check each outcome against papers
        for outcome in outcomes:
            outcome_name = outcome.get("outcome", "")
            outcome_effect = outcome.get("effect", "")

            for paper in technique_papers:
                direction = paper.get("effect_direction")
                magnitude = paper.get("effect_magnitude")

                if effect_conflicts(outcome_effect, direction, magnitude):
                    stats["conflicting_effects"] += 1
                    flags.append({
                        "technique_slug": slug,
                        "type": "effect_conflict",
                        "severity": "warning",
                        "detail": (
                            f"Outcome '{outcome_name}' claims '{outcome_effect}', "
                            f"but paper '{paper.get('title', '')[:60]}' "
                            f"reports {direction}/{magnitude}"
                        ),
                        "outcome": outcome_name,
                        "paper_title": paper.get("title", ""),
                    })

    # ── Check techniques with papers but no outcomes ────────
    for slug in papers_by_slug:
        if slug not in outcomes_index:
            stats["techniques_without_outcomes"] += 1
            flags.append({
                "technique_slug": slug,
                "type": "no_outcomes",
                "severity": "warning",
                "detail": f"Has {len(papers_by_slug[slug])} papers but no outcomes in index"
            })

    return flags, stats


def print_report(flags, stats):
    print()
    print("=" * 60)
    print("  OUTCOME DRIFT DETECTION REPORT")
    print("=" * 60)
    print()
    print("─ Summary ─")
    print(f"  Techniques with outcomes:    {stats['total_techniques_with_outcomes']}")
    print(f"  Total papers indexed:        {stats['total_papers']}")
    print(f"  Outcomes with recent papers: {stats['outcomes_with_new_papers']}")
    print(f"  Conflicting effects:         {stats['conflicting_effects']}")
    print(f"  Outcomes without papers:     {stats['outcomes_without_papers']}")
    print(f"  Techniques without outcomes: {stats['techniques_without_outcomes']}")
    print()

    if not flags:
        print("No drift detected. All outcomes appear consistent with latest papers.")
        print()
        return

    # Group by severity
    warnings = [f for f in flags if f["severity"] == "warning"]
    infos = [f for f in flags if f["severity"] == "info"]

    if infos:
        print(f"─ {len(infos)} Info Items (recent papers, worth reviewing) ─")
        for f in infos:
            print(f"  [{f['type']}] {f['technique_slug']}: {f['detail']}")
        print()

    if warnings:
        print(f"─ {len(warnings)} Warnings (potential issues) ─")
        for f in warnings:
            print(f"  [{f['type']}] {f['technique_slug']}: {f['detail']}")
        print()


def main():
    log("Detecting outcome drift...")
    flags, stats = analyze()

    # Write JSON report
    os.makedirs(HERMES_DIR, exist_ok=True)
    report_path = os.path.join(HERMES_DIR, "outcome_drift_report.json")
    report = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": stats,
        "flags": flags,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"JSON report written to {report_path}")
    print_report(flags, stats)


if __name__ == "__main__":
    main()
