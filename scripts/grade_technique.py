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
    """Calculate the best grade for a set of papers."""
    grades_config = rules.get("grades", {})
    priority_list = rules.get("study_type_priority", [])
    grade_order = ["A", "B", "C", "D", "?"]

    # Count study types
    type_counts = {}
    total_sample = 0
    for pid, paper in papers.items():
        if not isinstance(paper, dict):
            continue
        pubtypes = paper.get("pubtypes", [])
        sample = paper.get("sample_size", 0) or 0
        total_sample += sample

        for pt in pubtypes:
            type_counts[pt] = type_counts.get(pt, 0) + 1

        # Also track the highest-priority type
        best_type = get_study_type_priority(pubtypes, priority_list)
        type_counts[f"__best_{best_type}"] = type_counts.get(f"__best_{best_type}", 0) + 1

    log(f"  Study type counts: {type_counts}")
    log(f"  Total sample size: {total_sample}")

    # Check each grade level (highest first)
    for grade in grade_order:
        if grade not in grades_config:
            continue
        requirements = grades_config[grade].get("requires", [])
        if not requirements:
            continue

        satisfied = True
        for req in requirements:
            req_types = req.get("types", [])
            min_count = req.get("min_count", 1)
            or_alt = req.get("OR")

            # Check primary requirement
            count = sum(type_counts.get(t, 0) for t in req_types)
            if count >= min_count:
                continue

            # Check alternate (OR)
            if or_alt:
                or_types = or_alt.get("types", [])
                or_min = or_alt.get("min_count", 1)
                or_count = sum(type_counts.get(t, 0) for t in or_types)
                if or_count >= or_min:
                    continue

            satisfied = False
            break

        if satisfied:
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

        old_grade = technique.get("evidence_grade", technique.get("grade", "?"))
        new_grade = calculate_grade(tech_papers, rules)

        log(f"  {name}: {old_grade} → {new_grade} ({len(tech_papers)} papers)")

        # Update the markdown frontmatter
        frontmatter, body = get_markdown_frontmatter(path)
        frontmatter["grade"] = new_grade
        frontmatter["total_papers"] = len(tech_papers)
        frontmatter["last_searched"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Update grade_detail with rationale
        detail = rules.get("grades", {}).get(new_grade, {})
        frontmatter["grade_detail"] = detail.get("description", "")

        write_markdown_frontmatter(path, frontmatter, body)

        if new_grade != old_grade:
            changes.append(f"  {name}: {old_grade} → {new_grade}")

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
