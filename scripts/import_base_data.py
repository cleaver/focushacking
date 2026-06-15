#!/usr/bin/env python3
"""
Import base (editorial) data from POC JSON into technique markdown files.

Usage: python3 scripts/import_base_data.py

Reads the POC techniques_v2.json and injects long-term editorial data
into each technique's .md file:

  Frontmatter:
    - session_time          (e.g. "30 min per cycle")

  Body (new ## Outcomes section):
    - outcomes[]             per-outcome grade, effect, note

These fields are separate from the pipeline-managed fields (grade,
grade_detail, last_searched, total_papers, new_papers_this_run, and
the ## Papers body section). The pipeline never touches ## Outcomes.

Idempotent — safe to re-run. Won't overwrite existing data unless
--force is passed.
"""

import json
import os
import re
import sys
import argparse
from datetime import datetime, timezone

POC_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "POC", "techniques_v2.json"
)
TECHNIQUES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "techniques"
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
    """Read a technique markdown file, return (frontmatter_dict, body_str)."""
    path = os.path.join(TECHNIQUES_DIR, f"{slug}.md")
    if not os.path.exists(path):
        return None, None, None

    with open(path) as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None, None, content

    import yaml
    frontmatter = yaml.safe_load(match.group(1))
    body = content[match.end():]
    return frontmatter, body, path


def write_md(path, frontmatter, body):
    """Write frontmatter + body back to a markdown file."""
    lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for v in value:
                if isinstance(v, dict):
                    # Nested dict — use yaml dump for proper formatting
                    import yaml
                    dumped = yaml.dump([v], default_flow_style=False).strip()
                    # indent the dumped content
                    for dl in dumped.split("\n"):
                        lines.append(f"  {dl}")
                else:
                    lines.append(f"  - {v}")
        elif isinstance(value, str) and "\n" in value:
            lines.append(f"{key}: |")
            for line in value.split("\n"):
                lines.append(f"  {line}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, dict):
            import yaml
            dumped = yaml.dump(value, default_flow_style=False).strip()
            lines.append(f"{key}:")
            for dl in dumped.split("\n"):
                lines.append(f"  {dl}")
        else:
            lines.append(f"{key}: {json.dumps(value)}")
    lines.append("---")

    content = "\n".join(lines) + body
    with open(path, "w") as f:
        f.write(content)


def build_outcomes_section(outcomes):
    """Build a ## Outcomes markdown section from POC outcomes data."""
    if not outcomes:
        return ""

    lines = ["", "## Outcomes", ""]
    for o in outcomes:
        name = o.get("outcome", "Unknown")
        grade = o.get("grade", "?")
        effect = o.get("effect", "")
        note = o.get("note", "")

        lines.append(f"- **{name}** · Evidence: {grade} · Effect: {effect}")
        if note:
            lines.append(f"  {note}")
        lines.append("")

    return "\n".join(lines)


def has_outcomes_section(body):
    """Check if body already has a ## Outcomes section."""
    return bool(re.search(r"^## Outcomes\s*$", body, re.MULTILINE))


def import_technique(poc_data, force=False):
    """Import base data for one technique. Returns (status, message)."""
    name = poc_data["name"]
    slug = slugify(name)

    frontmatter, body, path = read_md(slug)
    if frontmatter is None:
        return "skip", f"{name}: .md not found (slug={slug})"

    changes = []

    # ── session_time ──────────────────────────────────────
    session_time = poc_data.get("session_time", "")
    if session_time and (force or "session_time" not in frontmatter):
        frontmatter["session_time"] = session_time
        changes.append(f"session_time = {session_time!r}")

    # ── outcomes ──────────────────────────────────────────
    outcomes = poc_data.get("outcomes", [])
    if outcomes and (force or not has_outcomes_section(body)):
        outcomes_section = build_outcomes_section(outcomes)
        if outcomes_section:
            body = body.rstrip() + "\n" + outcomes_section + "\n"
            changes.append(f"outcomes ({len(outcomes)} items)")

    if not changes:
        return "skip", f"{name}: already up to date"

    # Write
    write_md(path, frontmatter, body)
    return "updated", f"{name}: +{', '.join(changes)}"


def main():
    parser = argparse.ArgumentParser(
        description="Import base editorial data from POC JSON into technique .md files"
    )
    parser.add_argument(
        "--poc", default=POC_DEFAULT,
        help=f"Path to techniques_v2.json (default: {POC_DEFAULT})"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing data (default: skip if already present)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would change without writing"
    )
    args = parser.parse_args()

    if not os.path.exists(args.poc):
        log(f"ERROR: POC file not found: {args.poc}")
        sys.exit(1)

    with open(args.poc) as f:
        poc_techniques = json.load(f)

    log(f"Loaded {len(poc_techniques)} techniques from POC")
    log(f"Force mode: {args.force}")
    log(f"Dry run: {args.dry_run}")

    updated = 0
    skipped = 0
    errors = 0

    for poc in poc_techniques:
        status, msg = import_technique(poc, force=args.force)
        if status == "updated":
            updated += 1
            log(f"  UPDATE {msg}")
        elif status == "skip":
            skipped += 1
        else:
            errors += 1
            log(f"  ERROR  {msg}")

    log(f"\nDone. {updated} updated, {skipped} skipped, {errors} errors")

    if args.dry_run:
        log("DRY RUN — no files were written.")


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        # Override write_md globally for dry-run
        original_write = write_md

        def dry_write(path, frontmatter, body):
            log(f"  WOULD WRITE {path}")

        import __main__
        __main__.write_md = dry_write

    main()
