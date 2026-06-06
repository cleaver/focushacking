#!/usr/bin/env python3
"""
Build a git branch, commit changes, and create a PR.

Usage: python3 scripts/build_pr.py

Must be run inside the git repo.
Uses `gh` CLI for PR creation if available, otherwise prints instructions.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERMES_DIR = os.path.join(BASE_DIR, ".hermes")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def run(cmd, cwd=BASE_DIR):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def git_is_clean():
    """Check if the working tree is clean."""
    rc, out, _ = run("git status --porcelain")
    return rc == 0 and out == ""


def git_has_changes():
    """Check if there are uncommitted changes."""
    rc, out, _ = run("git status --porcelain")
    return rc == 0 and len(out) > 0


def get_current_week():
    """Get ISO week string like '2026-W24'."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-W%W")


def get_current_date():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_summaries():
    """Load pipeline outputs for the PR body."""
    summaries = {}

    candidate_path = os.path.join(HERMES_DIR, "new_candidates.json")
    tagged_path = os.path.join(HERMES_DIR, "tagged_candidates.json")
    grade_path = os.path.join(HERMES_DIR, "grade_changes.json")
    update_path = os.path.join(HERMES_DIR, "update_summary.json")

    if os.path.exists(candidate_path):
        with open(candidate_path) as f:
            summaries["candidates"] = json.load(f)

    if os.path.exists(tagged_path):
        with open(tagged_path) as f:
            summaries["tagged"] = json.load(f)

    if os.path.exists(grade_path):
        with open(grade_path) as f:
            summaries["grades"] = json.load(f)

    if os.path.exists(update_path):
        with open(update_path) as f:
            summaries["update"] = json.load(f)

    return summaries


def generate_pr_body(summaries):
    """Generate the PR body text."""
    week = get_current_week()
    date = get_current_date()

    lines = []
    lines.append(f"## Focus Hacking Research Digest — {week}")
    lines.append(f"")
    lines.append(f"*Generated: {date}*")
    lines.append("")

    # Grade changes
    grades = summaries.get("grades", {})
    grade_changes = grades.get("changes", [])
    if grade_changes:
        lines.append("### Grade Changes")
        lines.append("")
        for c in grade_changes:
            change = c.get("change", "")
            technique = c.get("technique", "")
            lines.append(f"- **{technique}**: {change}")
        lines.append("")
    else:
        lines.append("*(No grade changes this week)*")
        lines.append("")

    # New papers
    update = summaries.get("update", {})
    new_papers = update.get("new_papers", 0)
    techniques_affected = update.get("total_techniques_affected", 0)
    techniques_updated = update.get("techniques_updated", [])

    lines.append(f"### New Papers Found ({new_papers} total)")
    lines.append("")
    lines.append(f"Affected {techniques_affected} techniques.")
    if techniques_updated:
        lines.append("")
        for slug in techniques_updated:
            lines.append(f"- {slug.replace('-', ' ').title()}")
    lines.append("")

    # Candidates detail
    candidates_data = summaries.get("tagged") or summaries.get("candidates")
    if candidates_data:
        candidates = candidates_data.get("candidates", [])
        if candidates:
            lines.append("### New Papers Detail")
            lines.append("")
            lines.append("| PMID | Technique | Title | Tags Source | Populations | Facets |")
            lines.append("|------|-----------|-------|-------------|-------------|--------|")
            for c in candidates:
                pmid = c.get("pmid", "?")
                tech = c.get("technique_name", c.get("technique_slug", "?"))
                title = (c.get("title", "") or "")[:60]
                tag_src = c.get("tags_source", c.get("populations_reason", "?"))
                pops = ", ".join(c.get("populations_suggested", []))
                facets = ", ".join(c.get("focus_facets_suggested", []))
                lines.append(f"| {pmid} | {tech} | {title} | {tag_src} | {pops} | {facets} |")
            lines.append("")

    # Papers needing LLM review
    if candidates_data:
        needs_llm = [c for c in candidates_data.get("candidates", [])
                     if c.get("tags_source") == "none" or c.get("confidence") == "low"]
        if needs_llm:
            lines.append("### ⚠ Papers Needing Tag Review")
            lines.append("")
            lines.append("These papers lack MeSH terms — tags were assigned by text matching.")
            lines.append("Review the suggested populations and facets below:")
            lines.append("")
            for c in needs_llm:
                pmid = c.get("pmid", "?")
                title = (c.get("title", "") or "")[:80]
                pops = ", ".join(c.get("populations_suggested", []))
                facets = ", ".join(c.get("focus_facets_suggested", []))
                lines.append(f"- **{title}**")
                lines.append(f"  - PMID: {pmid}")
                lines.append(f"  - Suggested populations: {pops}")
                lines.append(f"  - Suggested facets: {facets}")
            lines.append("")

    # Review instructions
    lines.append("---")
    lines.append("")
    lines.append("### Review Checklist")
    lines.append("")
    lines.append("- [ ] Verify new paper entries are accurate")
    lines.append("- [ ] Confirm grade changes make sense")
    lines.append("- [ ] Review population/facet tags (especially for non-MeSH papers)")
    lines.append("- [ ] Check if any technique's `populations` or `focus_facets` frontmatter should be updated")
    lines.append("- [ ] Merge when ready")

    return "\n".join(lines)


def main():
    log("Building PR...")

    if not git_has_changes():
        log("No changes to commit. Nothing to PR.")
        return

    week = get_current_week()
    branch_name = f"research-digest/{week}"
    date = get_current_date()

    summaries = load_summaries()
    pr_body = generate_pr_body(summaries)

    # Count changes
    rc, diff_stat, _ = run("git diff --stat")
    files_changed = diff_stat.count("\n") if diff_stat else 0

    log(f"Changes detected across ~{files_changed} files")

    # Stage, branch, commit
    log("Staging changes...")
    run("git add techniques/ data/papers_index.json")

    # Check if there's anything staged
    rc, staged, _ = run("git diff --cached --stat")
    if not staged:
        log("No changes staged (techniques and data unchanged). Skipping PR.")
        return

    # Create branch
    rc, out, err = run(f"git checkout -b {branch_name}")
    if rc != 0:
        log(f"Branch creation failed: {err}")
        # Might already exist
        rc2, out2, _ = run(f"git checkout {branch_name}")
        if rc2 != 0:
            log("Could not create or switch to branch. Aborting.")
            return

    # Count new papers
    update = summaries.get("update", {})
    new_count = update.get("new_papers", 0)

    # Commit
    commit_msg = f"research digest: {week} ({new_count} new papers)"
    rc, out, err = run(f'git commit -m "{commit_msg}"')
    if rc != 0:
        log(f"Commit failed: {err}")
        return

    log(f"Committed: {commit_msg}")

    # Push
    rc, out, err = run(f"git push -u origin {branch_name}")
    if rc != 0:
        log(f"Push failed (remote may not be configured yet): {err}")
        log("Local branch created. Push manually when remote is ready:")
        log(f"  git push -u origin {branch_name}")
        # Print the PR body for manual creation
        print("\n--- PR Body ---")
        print(pr_body)
        print("---")
        return

    log("Push successful")

    # Create PR via gh CLI
    title = f"Research Digest: {week}"
    rc, out, err = run(
        f'gh pr create --title "{title}" --body "{pr_body}" --label "research-update"'
    )

    if rc == 0:
        log(f"PR created: {out}")
        print(f"\nPR URL: {out}")
    else:
        log(f"PR creation failed: {err}")
        log("Create PR manually with:")
        log(f'  gh pr create --title "{title}" --body "{pr_body}" --label "research-update"')

    # Save the PR body to a file for reference
    pr_body_path = os.path.join(HERMES_DIR, f"pr_body_{week}.md")
    with open(pr_body_path, "w") as f:
        f.write(pr_body)
    log(f"PR body saved to {pr_body_path}")


if __name__ == "__main__":
    main()
