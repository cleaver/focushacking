#!/usr/bin/env python3
"""
Detect grade drift — which grades changed, why, and which are close to changing.

Usage: python3 scripts/detect_grade_drift.py

Reads:
  - techniques/*.md           current grades in frontmatter
  - data/papers_index.json     paper data per technique
  - config/grading-rules.yaml  thresholds for each grade
  - .hermes/grade_history.json past grades (creates on first run)

Produces:
  - Grade change log          which techniques changed, why, what papers caused it
  - Near-miss list            techniques one paper away from a grade bump/drop
  - Stored history            appends current state for future comparison

Output: .hermes/grade_drift_report.json + human-readable summary.
"""

import json
import os
import re
import sys
import yaml
from datetime import datetime, timezone
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
TECHNIQUES_DIR = os.path.join(BASE_DIR, "techniques")
HERMES_DIR = os.path.join(BASE_DIR, ".hermes")
HISTORY_PATH = os.path.join(HERMES_DIR, "grade_history.json")
RULES_PATH = os.path.join(CONFIG_DIR, "grading-rules.yaml")
PAPERS_PATH = os.path.join(DATA_DIR, "papers_index.json")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_md_grades():
    """Load current grades from all technique markdown frontmatter. Returns {slug: {grade, grade_detail, total_papers}}."""
    result = {}
    for fname in sorted(os.listdir(TECHNIQUES_DIR)):
        if not fname.endswith(".md"):
            continue
        slug = fname[:-3]
        path = os.path.join(TECHNIQUES_DIR, fname)
        with open(path) as f:
            content = f.read()
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if match:
            fm = yaml.safe_load(match.group(1))
            result[slug] = {
                "grade": fm.get("grade", "?"),
                "grade_detail": fm.get("grade_detail", ""),
                "total_papers": fm.get("total_papers", 0),
                "new_papers_this_run": fm.get("new_papers_this_run", 0),
            }
    return result


def load_history():
    """Load grade history (creates empty dict if none)."""
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH) as f:
            return json.load(f)
    return {"runs": [], "latest_grades": {}}


def save_history(history, current_grades):
    """Append current state to history."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot = {
        "timestamp": now,
        "grades": {slug: data["grade"] for slug, data in current_grades.items()},
        "paper_counts": {slug: data["total_papers"] for slug, data in current_grades.items()},
    }
    history["runs"].append(snapshot)
    # Keep last 52 runs (one year of weekly)
    if len(history["runs"]) > 52:
        history["runs"] = history["runs"][-52:]
    history["latest_grades"] = snapshot["grades"]

    os.makedirs(HERMES_DIR, exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def load_papers_by_slug():
    """Load papers from index, grouped by technique slug. Returns {slug: [paper]}."""
    if not os.path.exists(PAPERS_PATH):
        return {}
    with open(PAPERS_PATH) as f:
        idx = json.load(f)
    by_slug = defaultdict(list)
    for pid, paper in idx.get("papers", {}).items():
        for slug in paper.get("technique_slugs", []):
            by_slug[slug].append(paper)
    return by_slug


def compute_grade_factors(papers, rules):
    """
    Compute the factors that determine a grade.
    Returns {grade: {satisfied: bool, missing: [str]}} for each grade level.
    """
    priority = rules.get("study_type_priority", [])
    grades_config = rules.get("grades", {})

    # Aggregate paper data
    type_counts = defaultdict(int)
    type_samples = defaultdict(int)
    effect_directions = []
    has_obs_only = True

    for paper in papers:
        pubtypes = paper.get("pubtypes", [])
        sample = paper.get("sample_size", 0) or 0

        for pt in pubtypes:
            type_counts[pt] += 1
            type_samples[pt] += sample

        # Track best type per paper
        best = "Unknown"
        for pt in priority:
            if pt in pubtypes:
                best = pt
                break
        type_counts[f"_best_{best}"] += 1
        type_samples[f"_best_{best}"] += sample

        # Observational-only check
        for high_type in ["Meta-Analysis", "Systematic Review",
                          "Randomized Controlled Trial", "Controlled Clinical Trial"]:
            if high_type in pubtypes:
                has_obs_only = False
                break

        ed = paper.get("effect_direction")
        if ed:
            effect_directions.append(ed)

    # Consistency
    if effect_directions:
        consistency = sum(1 for d in effect_directions if d == "positive") / len(effect_directions)
    else:
        consistency = None

    # Effect magnitude (simplified: check if any large/moderate)
    magnitudes = [paper.get("effect_magnitude", "") for paper in papers if paper.get("effect_magnitude")]
    has_large_or_moderate = any(m in ("large", "moderate") for m in magnitudes)
    has_small_or_better = has_large_or_moderate or any(m == "small" for m in magnitudes)

    # Check each grade
    grade_order = ["A", "B", "C", "D", "?"]
    result = {}
    for grade in grade_order:
        if grade not in grades_config:
            continue
        gcfg = grades_config[grade]
        reqs = gcfg.get("requires", [])
        if not reqs:
            result[grade] = {"satisfied": True, "missing": []}
            continue

        # Observational cap
        if has_obs_only and grade in ("A", "B"):
            result[grade] = {
                "satisfied": False,
                "missing": ["Evidence is observational-only (capped at C)"],
                "obs_capped": True,
            }
            continue

        missing = []
        satisfied = True

        for req in reqs:
            req_types = req.get("types", [])
            min_count = req.get("min_count", 1)
            min_sample = req.get("min_total_sample", 0)
            or_alt = req.get("OR")

            count = sum(type_counts.get(t, 0) + type_counts.get(f"_best_{t}", 0) for t in req_types)
            sample_total = sum(type_samples.get(t, 0) + type_samples.get(f"_best_{t}", 0) for t in req_types)

            passed = count >= min_count and sample_total >= min_sample

            if not passed and or_alt:
                or_types = or_alt.get("types", [])
                or_min = or_alt.get("min_count", 1)
                or_sample = or_alt.get("min_total_sample", 0)
                or_count = sum(type_counts.get(t, 0) for t in or_types)
                or_samples = sum(type_samples.get(t, 0) for t in or_types)
                passed = or_count >= or_min and or_samples >= or_sample

            if not passed:
                satisfied = False
                # Describe what's missing
                if count < min_count:
                    missing.append(f"Need {min_count - count} more of {', '.join(req_types[:2])} (have {count})")
                elif sample_total < min_sample:
                    missing.append(f"Need {min_sample - sample_total} more total sample (have {sample_total})")

        # Effect check
        eff_req = gcfg.get("effect_required")
        if eff_req == "moderate_or_large" and not has_large_or_moderate:
            satisfied = False
            missing.append("Need moderate or large effect (no such effects found)")
        elif eff_req == "small_positive" and not has_small_or_better:
            satisfied = False
            missing.append("Need at least small positive effect (none found)")

        # Consistency check
        cons_min = gcfg.get("consistency_min")
        if cons_min and consistency is not None and consistency < cons_min:
            satisfied = False
            missing.append(f"Need consistency >= {int(cons_min*100)}% (have {int(consistency*100)}%)")

        result[grade] = {"satisfied": satisfied, "missing": missing}

    return result


def detect_changes(current_grades, history):
    """Compare current grades against last recorded snapshot. Returns list of changes."""
    prev_grades = history.get("latest_grades", {})
    if not prev_grades:
        return []  # First run, no baseline

    changes = []
    for slug, data in sorted(current_grades.items()):
        current = data["grade"]
        previous = prev_grades.get(slug, "?")
        if current != previous:
            changes.append({
                "technique_slug": slug,
                "previous_grade": previous,
                "current_grade": current,
                "direction": "up" if _grade_rank(current) < _grade_rank(previous) else "down",
                "grade_detail": data["grade_detail"],
                "total_papers": data["total_papers"],
                "new_papers_this_run": data["new_papers_this_run"],
            })
    return changes


def _grade_rank(g):
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "?": 4}
    return order.get(g, 4)


def find_near_misses(current_grades, papers_by_slug, rules):
    """
    Find techniques where one more paper could change the grade.
    Returns list of {slug, current_grade, bump_to, what_needed}.
    """
    near_misses = []
    grade_order = ["A", "B", "C", "D", "?"]

    for slug, data in sorted(current_grades.items()):
        current = data["grade"]
        papers = papers_by_slug.get(slug, [])

        if not papers:
            continue

        factors = compute_grade_factors(papers, rules)

        # Check if current grade is satisfied (it should be)
        # Then check the NEXT HIGHER grade — what's missing?
        current_idx = grade_order.index(current) if current in grade_order else 4

        # Look for near-miss upward (one grade higher)
        if current_idx > 0:
            higher_grade = grade_order[current_idx - 1]
            higher_factors = factors.get(higher_grade, {})
            if not higher_factors.get("satisfied") and not higher_factors.get("obs_capped"):
                missing = higher_factors.get("missing", [])
                if missing:
                    near_misses.append({
                        "technique_slug": slug,
                        "current_grade": current,
                        "bump_to": higher_grade,
                        "direction": "up",
                        "what_needed": missing,
                        "total_papers": len(papers),
                    })

        # Look for near-miss downward (one grade lower, i.e. current grade barely met)
        if current_idx < len(grade_order) - 1:
            current_factors = factors.get(current, {})
            # If current grade requirement is barely satisfied, flag it
            missing = current_factors.get("missing", [])
            if not current_factors.get("satisfied", True):
                # Current grade requirements NOT met — this is a problem
                pass  # Handled separately
            elif current_factors.get("satisfied"):
                # Check if any requirement is barely met (close to threshold)
                # This is harder to compute precisely, skip for now
                pass

    return near_misses


def print_report(changes, near_misses):
    print()
    print("=" * 65)
    print("  GRADE DRIFT REPORT")
    print("=" * 65)
    print()

    if changes:
        print(f"─ {len(changes)} Grade Changes Since Last Run ─")
        for c in changes:
            arrow = "↑" if c["direction"] == "up" else "↓"
            print(f"  {arrow} {c['technique_slug']}: {c['previous_grade']} → {c['current_grade']}")
            print(f"    Papers: {c['total_papers']} total, +{c['new_papers_this_run']} new this run")
            print(f"    {c['grade_detail'][:120]}")
            print()
    else:
        print("No grade changes since last run.")
        print()

    if near_misses:
        print(f"─ {len(near_misses)} Near-Miss Grades (close to bumping up) ─")
        for nm in near_misses:
            print(f"  ↗ {nm['technique_slug']}: {nm['current_grade']} → {nm['bump_to']} (possible)")
            for need in nm["what_needed"]:
                print(f"    • {need}")
            print()
    else:
        print("No near-miss grades found.")
        print()


def main():
    log("Detecting grade drift...")

    current_grades = load_md_grades()
    history = load_history()
    papers_by_slug = load_papers_by_slug()

    with open(RULES_PATH) as f:
        rules = yaml.safe_load(f)

    changes = detect_changes(current_grades, history)
    near_misses = find_near_misses(current_grades, papers_by_slug, rules)

    # Save current state to history
    save_history(history, current_grades)

    # Write report
    os.makedirs(HERMES_DIR, exist_ok=True)
    report_path = os.path.join(HERMES_DIR, "grade_drift_report.json")
    report = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "changes": changes,
        "near_misses": near_misses,
        "history_runs": len(history["runs"]),
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"JSON report written to {report_path}")
    log(f"Grade history: {len(history['runs'])} runs stored")
    print_report(changes, near_misses)


if __name__ == "__main__":
    main()
