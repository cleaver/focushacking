#!/usr/bin/env python3
"""
Recalculate evidence grades for all techniques.

Usage: python3 scripts/grade_technique.py

Reads data/papers_index.json and config/grading-rules.yaml.
Updates frontmatter grade in each technique's .md file.
"""

import json
import os
import sys
import yaml
import re
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TECHNIQUES_DIR = os.path.join(BASE_DIR, "techniques")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
HERMES_DIR = os.path.join(BASE_DIR, ".hermes")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_grading_rules():
    """Load grading rules from config."""
    path = os.path.join(CONFIG_DIR, "grading-rules.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def load_papers_index():
    """Load the papers index."""
    path = os.path.join(DATA_DIR, "papers_index.json")
    with open(path) as f:
        return json.load(f)


def load_techniques_config():
    """Load techniques config."""
    path = os.path.join(CONFIG_DIR, "techniques.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def get_markdown_frontmatter(path):
    """Extract YAML frontmatter from a markdown file."""
    with open(path) as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}, content

    frontmatter = yaml.safe_load(match.group(1))
    body = content[match.end():]
    return frontmatter, body


def write_markdown_frontmatter(path, frontmatter, body):
    """Write frontmatter + body back to a markdown file."""
    lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for v in value:
                lines.append(f"  - {v}")
        elif isinstance(value, str) and "\n" in value:
            lines.append(f"{key}: |")
            for line in value.split("\n"):
                lines.append(f"  {line}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {json.dumps(value)}")
    lines.append("---")

    content = "\n".join(lines) + body
    with open(path, "w") as f:
        f.write(content)


def get_study_type_priority(pubtypes, priority_list):
    """Return the highest-priority study type for a paper."""
    for pt in priority_list:
        if pt in pubtypes:
            return pt
    return "Unknown"


def calculate_grade(papers, rules):
    """Calculate the best grade for a set of papers using the PoC rubric.

    Factors:
    - Study type counts (with priority ordering)
    - Total sample size per study type
    - Effect size direction/magnitude (LLM-extracted from abstracts)
    - Consistency (proportion of studies showing positive effects)
    - Observational-only evidence capped at Grade C
    """
    grades_config = rules.get("grades", {})
    priority_list = rules.get("study_type_priority", [])
    grade_order = ["A", "B", "C", "D", "?"]

    # ── Aggregate paper data ──────────────────────────────────────
    type_counts = {}
    type_samples = {}  # total sample per pubtype
    effect_directions = []  # all effect directions across papers
    has_observational_only = True  # becomes False if an RCT/meta is present
    has_any_study = False
    highest_type = None  # best study type seen

    for pid, paper in papers.items():
        if not isinstance(paper, dict):
            continue
        pubtypes = paper.get("pubtypes", [])
        sample = paper.get("sample_size", 0) or 0

        for pt in pubtypes:
            type_counts[pt] = type_counts.get(pt, 0) + 1
            type_samples[pt] = type_samples.get(pt, 0) + sample

        # Track highest-priority type for this paper
        best_type = get_study_type_priority(pubtypes, priority_list)
        type_counts[f"__best_{best_type}"] = type_counts.get(f"__best_{best_type}", 0) + 1
        type_samples[f"__best_{best_type}"] = type_samples.get(f"__best_{best_type}", 0) + sample

        # Track if any non-observational study exists
        for high_type in ["Meta-Analysis", "Systematic Review",
                          "Randomized Controlled Trial", "Controlled Clinical Trial"]:
            if high_type in pubtypes:
                has_observational_only = False
                break

        # Track highest study type across all papers
        pt_rank = get_study_type_priority(pubtypes, priority_list)
        pt_idx = priority_list.index(pt_rank) if pt_rank in priority_list else 99
        best_idx = priority_list.index(highest_type) if highest_type in priority_list else 99
        if pt_idx < best_idx:
            highest_type = pt_rank

        has_any_study = True

        # Collect effect direction
        ed = paper.get("effect_direction")
        if ed:
            effect_directions.append(ed)

    if not has_any_study:
        return "?"

    # ── Consistency: proportion of studies with positive effects ──
    if effect_directions:
        positive_count = sum(1 for d in effect_directions if d == "positive")
        consistency = positive_count / len(effect_directions)
    else:
        consistency = None  # unknown

    # ── Check each grade level (highest first) ────────────────────
    for grade in grade_order:
        if grade not in grades_config:
            continue
        gcfg = grades_config[grade]
        requirements = gcfg.get("requires", [])
        if not requirements:
            continue

        # Observational-only cap: if we only have obs studies and grade > C, cap
        if has_observational_only and grade in ("A", "B"):
            continue

        satisfied = True
        for req in requirements:
            req_types = req.get("types", [])
            min_count = req.get("min_count", 1)
            min_sample = req.get("min_total_sample", 0)
            or_alt = req.get("OR")

            # Count matching types (both exact and __best_ prefix)
            count = 0
            sample_total = 0
            for t in req_types:
                count += type_counts.get(t, 0)
                count += type_counts.get(f"__best_{t}", 0)
                sample_total += type_samples.get(t, 0)
                sample_total += type_samples.get(f"__best_{t}", 0)

            # Check primary requirement
            passed = count >= min_count and sample_total >= min_sample

            # Check alternate (OR) if primary failed
            if not passed and or_alt:
                or_types = or_alt.get("types", [])
                or_min = or_alt.get("min_count", 1)
                or_sample = or_alt.get("min_total_sample", 0)
                or_count = 0
                or_sample_total = 0
                for t in or_types:
                    or_count += type_counts.get(t, 0)
                    or_count += type_counts.get(f"__best_{t}", 0)
                    or_sample_total += type_samples.get(t, 0)
                    or_sample_total += type_samples.get(f"__best_{t}", 0)
                if or_count >= or_min and or_sample_total >= or_sample:
                    passed = True

            if not passed:
                satisfied = False
                break

        if not satisfied:
            continue

        # ── Effect size check ────────────────────────────────
        effect_required = gcfg.get("effect_required")
        if effect_required and effect_directions:
            # Count positive-direction studies
            pos = sum(1 for d in effect_directions if d == "positive")
            # Check magnitude for A/B grades
            if effect_required == "moderate_or_large":
                # Need mostly moderate/large positive effects
                mags = []
                for pid, paper in papers.items():
                    if not isinstance(paper, dict):
                        continue
                    mag = paper.get("effect_magnitude")
                    if mag:
                        mags.append(mag)
                if mags:
                    large_or_mod = sum(1 for m in mags if m in ("large", "moderate"))
                    if large_or_mod / len(mags) < 0.5:
                        satisfied = False
            elif effect_required == "small_positive":
                # Need mostly positive direction
                if pos / len(effect_directions) < 0.5:
                    satisfied = False

        if not satisfied:
            continue

        # ── Consistency check ─────────────────────────────────
        consistency_min = gcfg.get("consistency_min")
        if consistency_min is not None and consistency is not None:
            if consistency < consistency_min:
                continue

        return grade

    return "?"


def slugify(name):
    s = name.lower()
    for ch in ["–", "—", "/", "\\", "'", '"', "(", ")", ",", ".", ":", ";"]:
        s = s.replace(ch, "-" if ch in ["–", "—", "/", "\\"] else "")
    s = s.replace(" ", "-")
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def main():
    log("Recalculating grades...")

    rules = load_grading_rules()
    papers_index = load_papers_index()
    config = load_techniques_config()
    papers = papers_index.get("papers", {})

    # Check if there are new candidates — only recalculate if yes
    candidates_path = os.path.join(HERMES_DIR, "tagged_candidates.json")
    raw_candidates_path = os.path.join(HERMES_DIR, "new_candidates.json")
    has_new_papers = False
    for p in [candidates_path, raw_candidates_path]:
        if os.path.exists(p):
            with open(p) as f:
                cd = json.load(f)
                if cd.get("candidates"):
                    has_new_papers = True
                    break

    if not has_new_papers:
        log("No new papers detected — preserving existing grades.")
        # Still update timestamps in frontmatter
        for technique in config.get("techniques", []):
            slug = technique.get("slug", "")
            path = os.path.join(TECHNIQUES_DIR, f"{slug}.md")
            if not os.path.exists(path):
                continue
            frontmatter, body = get_markdown_frontmatter(path)
            frontmatter["last_searched"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            write_markdown_frontmatter(path, frontmatter, body)
        return

    changes = []

    for technique in config.get("techniques", []):
        slug = technique.get("slug", "")
        name = technique.get("name", "")
        path = os.path.join(TECHNIQUES_DIR, f"{slug}.md")

        if not os.path.exists(path):
            log(f"  WARNING: {slug}.md not found, skipping")
            continue

        # Get papers for this technique
        tech_papers = {}
        for pid, paper in papers.items():
            if not isinstance(paper, dict):
                continue
            if slug in paper.get("technique_slugs", []):
                tech_papers[pid] = paper

        if not tech_papers:
            log(f"  {name}: No papers found")
            continue

        # Read existing frontmatter first (preserves PoC manual grades)
        frontmatter, body = get_markdown_frontmatter(path)
        old_grade = frontmatter.get("grade", "?")
        new_grade = calculate_grade(tech_papers, rules)

        log(f"  {name}: {old_grade} → {new_grade} ({len(tech_papers)} papers)")

        # Only update if grade actually changes
        if new_grade != old_grade:
            frontmatter["grade"] = new_grade
            frontmatter["total_papers"] = len(tech_papers)
            frontmatter["last_searched"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            write_markdown_frontmatter(path, frontmatter, body)
            changes.append(f"  {name}: {old_grade} → {new_grade}")
        else:
            # Still update timestamps
            frontmatter["last_searched"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            frontmatter["total_papers"] = len(tech_papers)
            write_markdown_frontmatter(path, frontmatter, body)

    # Summary
    if changes:
        log(f"\nGrade changes:")
        for c in changes:
            log(c)
    else:
        log(f"\nNo grade changes this run.")

    # Write grade changes marker for the agent
    hermes_dir = os.path.join(BASE_DIR, ".hermes")
    os.makedirs(hermes_dir, exist_ok=True)
    with open(os.path.join(hermes_dir, "grade_changes.json"), "w") as f:
        json.dump({
            "changes": [{"technique": c.split(":")[0].strip(), "change": c.split(":")[1].strip()} for c in changes],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)


if __name__ == "__main__":
    main()
