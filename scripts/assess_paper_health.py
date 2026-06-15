#!/usr/bin/env python3
"""
Health check on the papers data across all techniques.

Usage: python3 scripts/assess_paper_health.py

Checks:
  1. Count consistency — frontmatter total_papers vs papers_index.json
  2. Evidence depth — papers per technique (flag sparse ones)
  3. Evidence freshness — most recent paper year per technique
  4. Stagnation — techniques with no new papers in 2+ years
  5. Grade drift — current grade vs POC baseline grade
  6. Study type mix — RCT count vs observational per technique
  7. Overall index health — total papers, coverage

Output: .hermes/paper_health_report.json + human-readable summary.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TECHNIQUES_DIR = os.path.join(BASE_DIR, "techniques")
HERMES_DIR = os.path.join(BASE_DIR, ".hermes")
POC_PATH = os.path.join(BASE_DIR, "POC", "techniques_v2.json")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def slugify(name):
    s = name.lower()
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace("'", "").replace('"', "")
    s = s.replace("(", "").replace(")", "")
    s = s.replace("/", "-").replace("\\", "-")
    s = s.replace(",", "").replace(".", "")
    s = s.replace(":", "").replace(";", "")
    s = s.replace(" ", "-")
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def load_all_md_frontmatter():
    """Load frontmatter from all technique .md files. Returns {slug: frontmatter}."""
    result = {}
    for fname in os.listdir(TECHNIQUES_DIR):
        if not fname.endswith(".md"):
            continue
        slug = fname[:-3]
        path = os.path.join(TECHNIQUES_DIR, fname)
        with open(path) as f:
            content = f.read()
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if match:
            import yaml
            result[slug] = yaml.safe_load(match.group(1))
    return result


def load_poc_grades():
    """Load POC grades as baseline. Returns {slug: grade}."""
    poc = load_json(POC_PATH)
    grades = {}
    for t in poc:
        slug = slugify(t.get("name", ""))
        grade = t.get("evidence_grade", "?")
        if slug:
            grades[slug] = grade
    return grades


def analyze():
    papers_index = load_json(os.path.join(DATA_DIR, "papers_index.json"))
    papers = papers_index.get("papers", {})
    md_frontmatter = load_all_md_frontmatter()
    poc_grades = load_poc_grades()

    # Build paper stats per technique slug
    papers_by_slug = defaultdict(list)
    for pid, paper in papers.items():
        for slug in paper.get("technique_slugs", []):
            papers_by_slug[slug].append(paper)

    issues = []
    stats = {
        "total_techniques_with_md": len(md_frontmatter),
        "total_techniques_with_papers": len([s for s, ps in papers_by_slug.items() if ps]),
        "total_papers_indexed": len(papers),
        "avg_papers_per_technique": 0,
        "techniques_with_0_papers": 0,
        "techniques_with_1_2_papers": 0,
        "techniques_stagnant_2yr": 0,
        "techniques_growing": 0,
        "count_mismatches": 0,
        "grade_improved": 0,
        "grade_declined": 0,
        "grade_unchanged": 0,
    }

    current_year = datetime.now().year
    paper_counts = []
    per_technique = []

    for slug, fm in sorted(md_frontmatter.items()):
        md_count = fm.get("total_papers", 0) or 0
        technique_papers = papers_by_slug.get(slug, [])
        idx_count = len(technique_papers)
        md_grade = fm.get("grade", "?")
        poc_grade = poc_grades.get(slug, "?")

        paper_counts.append(idx_count)

        years = sorted(set(p.get("year", 0) for p in technique_papers if p.get("year")))
        latest_year = max(years) if years else 0
        earliest_year = min(years) if years else 0

        # Count study types
        rct_count = 0
        meta_count = 0
        obs_count = 0
        for p in technique_papers:
            pts = [t.lower() for t in p.get("pubtypes", [])]
            joined = " ".join(pts)
            if "randomized" in joined:
                rct_count += 1
            elif "meta" in joined or "systematic" in joined:
                meta_count += 1
            else:
                obs_count += 1

        entry = {
            "slug": slug,
            "name": fm.get("title", slug),
            "category": fm.get("category", ""),
            "grade": md_grade,
            "poc_grade": poc_grade,
            "md_count": md_count,
            "idx_count": idx_count,
            "count_ok": md_count == idx_count,
            "latest_year": latest_year,
            "earliest_year": earliest_year,
            "rct_count": rct_count,
            "meta_count": meta_count,
            "obs_count": obs_count,
            "new_papers_this_run": fm.get("new_papers_this_run", 0),
            "last_searched": fm.get("last_searched", ""),
        }
        per_technique.append(entry)

        # ── Issues ──────────────────────────────────────
        if md_count != idx_count:
            stats["count_mismatches"] += 1
            issues.append({
                "technique_slug": slug,
                "type": "count_mismatch",
                "severity": "warning",
                "detail": f"Frontmatter says {md_count} papers, index has {idx_count}"
            })

        if idx_count == 0:
            stats["techniques_with_0_papers"] += 1
            issues.append({
                "technique_slug": slug,
                "type": "no_papers",
                "severity": "warning",
                "detail": "No papers in index"
            })
        elif idx_count <= 2:
            stats["techniques_with_1_2_papers"] += 1

        if latest_year and latest_year < current_year - 1:
            stats["techniques_stagnant_2yr"] += 1
            issues.append({
                "technique_slug": slug,
                "type": "stagnant",
                "severity": "info",
                "detail": f"Most recent paper is from {latest_year} ({current_year - latest_year} years ago)"
            })

        if latest_year and latest_year >= current_year - 1:
            stats["techniques_growing"] += 1

        # Grade drift vs POC baseline
        if poc_grade != "?" and md_grade != "?":
            grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "?": 4}
            md_rank = grade_order.get(md_grade, 4)
            poc_rank = grade_order.get(poc_grade, 4)
            if md_rank < poc_rank:
                stats["grade_improved"] += 1
            elif md_rank > poc_rank:
                stats["grade_declined"] += 1
            else:
                stats["grade_unchanged"] += 1

    if paper_counts:
        stats["avg_papers_per_technique"] = round(sum(paper_counts) / len(paper_counts), 1)

    # Sort per_technique by paper count (ascending) for sparse-first view
    per_technique.sort(key=lambda x: x["idx_count"])

    return issues, stats, per_technique


def print_report(issues, stats, per_technique):
    print()
    print("=" * 65)
    print("  PAPER HEALTH REPORT")
    print("=" * 65)
    print()

    print("─ Index Overview ─")
    print(f"  Total papers indexed:        {stats['total_papers_indexed']}")
    print(f"  Techniques with .md files:   {stats['total_techniques_with_md']}")
    print(f"  Techniques with papers:      {stats['total_techniques_with_papers']}")
    print(f"  Avg papers per technique:    {stats['avg_papers_per_technique']}")
    print()

    print("─ Evidence Depth ─")
    print(f"  Techniques with 0 papers:    {stats['techniques_with_0_papers']}")
    print(f"  Techniques with 1–2 papers:  {stats['techniques_with_1_2_papers']}")
    print(f"  Stagnant (no papers 2+ yr):  {stats['techniques_stagnant_2yr']}")
    print(f"  Growing (papers this year):  {stats['techniques_growing']}")
    print()

    print("─ Data Consistency ─")
    print(f"  Count mismatches (md vs idx): {stats['count_mismatches']}")
    print()

    print("─ Grade Drift (vs POC baseline) ─")
    print(f"  Improved:  {stats['grade_improved']}")
    print(f"  Declined:  {stats['grade_declined']}")
    print(f"  Unchanged: {stats['grade_unchanged']}")
    print()

    # Sparse techniques (most at-risk)
    sparse = [t for t in per_technique if t["idx_count"] <= 2]
    if sparse:
        print(f"─ {len(sparse)} Techniques with Sparse Evidence (≤2 papers) ─")
        print(f"  {'Technique':<40} {'Papers':>6} {'Grade':>5} {'Last':>6} {'RCT':>4} {'Meta':>5}")
        print(f"  {'-'*40} {'-'*6} {'-'*5} {'-'*6} {'-'*4} {'-'*5}")
        for t in sparse:
            print(f"  {t['name'][:39]:<40} {t['idx_count']:>6} {t['grade']:>5} {str(t['latest_year']):>6} {t['rct_count']:>4} {t['meta_count']:>5}")
        print()

    # Top evidence (most papers)
    rich = sorted(per_technique, key=lambda x: -x["idx_count"])[:10]
    print(f"─ Top 10 Techniques by Paper Count ─")
    print(f"  {'Technique':<40} {'Papers':>6} {'Grade':>5} {'Last':>6} {'RCT':>4} {'Meta':>5}")
    print(f"  {'-'*40} {'-'*6} {'-'*5} {'-'*6} {'-'*4} {'-'*5}")
    for t in rich:
        print(f"  {t['name'][:39]:<40} {t['idx_count']:>6} {t['grade']:>5} {str(t['latest_year']):>6} {t['rct_count']:>4} {t['meta_count']:>5}")
    print()

    # Issues
    warnings = [i for i in issues if i["severity"] == "warning"]
    infos = [i for i in issues if i["severity"] == "info"]

    if infos:
        print(f"─ {len(infos)} Stagnation Flags ─")
        for i in infos:
            print(f"  [{i['type']}] {i['technique_slug']}: {i['detail']}")
        print()

    if warnings:
        print(f"─ {len(warnings)} Warnings ─")
        for i in warnings:
            print(f"  [{i['type']}] {i['technique_slug']}: {i['detail']}")
        print()

    if not infos and not warnings:
        print("All checks passed. Papers data looks healthy.")
        print()


def main():
    log("Assessing paper health...")
    issues, stats, per_technique = analyze()

    # Write JSON report
    os.makedirs(HERMES_DIR, exist_ok=True)
    report_path = os.path.join(HERMES_DIR, "paper_health_report.json")
    report = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": stats,
        "issues": issues,
        "per_technique": per_technique,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"JSON report written to {report_path}")
    print_report(issues, stats, per_technique)


if __name__ == "__main__":
    main()
