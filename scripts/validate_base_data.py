#!/usr/bin/env python3
"""
Validate that base (editorial) data in technique markdown files is
consistent with the POC source of truth.

Usage: python3 scripts/validate_base_data.py

Checks:
  1. Every POC technique has a matching .md file
  2. Every .md file has a ## Outcomes section
  3. session_time is present in frontmatter
  4. how_to_do_it step count matches POC steps[] length
  5. mechanism field is present and non-empty
  6. Grade drift: frontmatter grade vs POC grade (warning only)

Output: JSON report + human-readable summary.
Exit code 1 if critical issues found.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

POC_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "POC", "techniques_v2.json"
)
TECHNIQUES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "techniques"
)
HERMES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".hermes"
)


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


def read_md(slug):
    """Read technique .md, return (frontmatter, body, path)."""
    path = os.path.join(TECHNIQUES_DIR, f"{slug}.md")
    if not os.path.exists(path):
        return None, None, None

    with open(path) as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None, content, path

    import yaml
    frontmatter = yaml.safe_load(match.group(1))
    body = content[match.end():]
    return frontmatter, body, path


def validate(poc_techniques):
    """Run all validation checks. Returns (issues, warnings, summary)."""
    issues = []    # Critical — fix needed
    warnings = []  # Advisory — worth reviewing
    stats = {
        "total_poc": len(poc_techniques),
        "total_md": 0,
        "with_outcomes": 0,
        "with_session_time": 0,
        "with_mechanism": 0,
        "step_count_match": 0,
        "grade_match": 0,
        "grade_drift": 0,
        "missing_md": 0,
    }

    # Get all existing .md slugs
    md_slugs = set()
    for fname in os.listdir(TECHNIQUES_DIR):
        if fname.endswith(".md"):
            md_slugs.add(fname[:-3])
    stats["total_md"] = len(md_slugs)

    for poc in poc_techniques:
        name = poc.get("name", "Unknown")
        slug = slugify(name)

        frontmatter, body, path = read_md(slug)

        # ── Check 1: .md exists ─────────────────────────
        if frontmatter is None:
            issues.append({
                "technique": name,
                "slug": slug,
                "check": "md_exists",
                "detail": f"No .md file found for '{name}' (slug={slug})"
            })
            stats["missing_md"] += 1
            continue

        # ── Check 2: ## Outcomes section ──────────────────
        has_outcomes = bool(re.search(r"^## Outcomes\s*$", body, re.MULTILINE))
        if has_outcomes:
            stats["with_outcomes"] += 1
        else:
            issues.append({
                "technique": name,
                "slug": slug,
                "check": "has_outcomes",
                "detail": "Missing ## Outcomes section in body"
            })

        # ── Check 3: session_time ────────────────────────
        if frontmatter.get("session_time"):
            stats["with_session_time"] += 1
        else:
            issues.append({
                "technique": name,
                "slug": slug,
                "check": "has_session_time",
                "detail": "Missing session_time in frontmatter"
            })

        # ── Check 4: mechanism present ───────────────────
        if frontmatter.get("mechanism"):
            stats["with_mechanism"] += 1
        else:
            issues.append({
                "technique": name,
                "slug": slug,
                "check": "has_mechanism",
                "detail": "Missing mechanism in frontmatter"
            })

        # ── Check 5: step count match ────────────────────
        poc_steps = poc.get("steps", [])
        how_to = frontmatter.get("how_to_do_it", "")
        if how_to:
            # Count numbered lines in how_to_do_it
            md_step_count = len(re.findall(r"^\s*\d+\.", how_to, re.MULTILINE))
            if md_step_count == len(poc_steps):
                stats["step_count_match"] += 1
            else:
                warnings.append({
                    "technique": name,
                    "slug": slug,
                    "check": "step_count",
                    "detail": f"POC has {len(poc_steps)} steps, .md has {md_step_count} steps"
                })
        elif poc_steps:
            warnings.append({
                "technique": name,
                "slug": slug,
                "check": "step_count",
                "detail": "POC has steps but how_to_do_it is empty in .md"
            })

        # ── Check 6: Grade drift (warning only) ──────────
        poc_grade = poc.get("evidence_grade", "?")
        md_grade = frontmatter.get("grade", "?")
        if poc_grade == md_grade:
            stats["grade_match"] += 1
        else:
            stats["grade_drift"] += 1
            warnings.append({
                "technique": name,
                "slug": slug,
                "check": "grade_drift",
                "detail": f"POC grade={poc_grade}, .md grade={md_grade}"
            })

    stats["total_issues"] = len(issues)
    stats["total_warnings"] = len(warnings)

    return issues, warnings, stats


def print_report(issues, warnings, stats):
    """Print human-readable validation report."""
    print()
    print("=" * 60)
    print("  BASE DATA VALIDATION REPORT")
    print("=" * 60)
    print()

    print("─ Summary ─")
    print(f"  POC techniques:       {stats['total_poc']}")
    print(f"  .md files:            {stats['total_md']}")
    print(f"  Missing .md:          {stats['missing_md']}")
    print(f"  With ## Outcomes:     {stats['with_outcomes']}")
    print(f"  With session_time:    {stats['with_session_time']}")
    print(f"  With mechanism:       {stats['with_mechanism']}")
    print(f"  Step count match:     {stats['step_count_match']}")
    print(f"  Grade match:          {stats['grade_match']}")
    print(f"  Grade drift:          {stats['grade_drift']}")
    print()

    if issues:
        print(f"─ {len(issues)} Critical Issues ─")
        for i in issues:
            print(f"  [{i['check']}] {i['technique']}: {i['detail']}")
        print()

    if warnings:
        print(f"─ {len(warnings)} Warnings ─")
        for w in warnings:
            print(f"  [{w['check']}] {w['technique']}: {w['detail']}")
        print()

    if not issues and not warnings:
        print("✓ All checks passed. No issues found.")
        print()

    return len(issues)


def main():
    if not os.path.exists(POC_DEFAULT):
        log(f"ERROR: POC file not found: {POC_DEFAULT}")
        sys.exit(1)

    with open(POC_DEFAULT) as f:
        poc_techniques = json.load(f)

    log(f"Validating {len(poc_techniques)} techniques against {TECHNIQUES_DIR}")

    issues, warnings, stats = validate(poc_techniques)

    # Write JSON report
    os.makedirs(HERMES_DIR, exist_ok=True)
    report_path = os.path.join(HERMES_DIR, "validation_report.json")
    report = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": stats,
        "issues": issues,
        "warnings": warnings,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"JSON report written to {report_path}")

    print_report(issues, warnings, stats)

    # Exit code 1 if critical issues
    if issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
