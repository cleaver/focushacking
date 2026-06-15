#!/usr/bin/env python3
"""
Import base (editorial) data from POC JSON into technique markdown files
and outcomes index.

Usage: python3 scripts/import_base_data.py

Reads the POC techniques_v2.json and injects long-term editorial data:

  data/outcomes_index.json:
    - outcomes[] per slug   per-outcome grade, effect, note

  techniques/*.md frontmatter:
    - session_time           (e.g. "30 min per cycle")

Outcomes live in data/outcomes_index.json as the single source of truth
for the Astro site. Session time stays in markdown frontmatter.

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


def import_technique(poc_data, outcomes_index, force=False):
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

    # ── outcomes → outcomes_index.json ────────────────────
    outcomes = poc_data.get("outcomes", [])
    if outcomes and (force or slug not in outcomes_index):
        outcomes_index[slug] = outcomes
        changes.append(f"outcomes ({len(outcomes)} items) → index")

    if not changes:
        return "skip", f"{name}: already up to date"

    # Write markdown if frontmatter changed
    if any(c.startswith("session_time") for c in changes):
        write_md(path, frontmatter, body)

    return "updated", f"{name}: +{', '.join(changes)}"


def main():
    DATA_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data"
    )
    OUTCOMES_PATH = os.path.join(DATA_DIR, "outcomes_index.json")

    parser = argparse.ArgumentParser(
        description="Import base editorial data from POC JSON into technique .md files and outcomes index"
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

    # Load existing outcomes index (if any)
    outcomes_index = {}
    if os.path.exists(OUTCOMES_PATH):
        with open(OUTCOMES_PATH) as f:
            outcomes_index = json.load(f)

    log(f"Loaded {len(poc_techniques)} techniques from POC")
    log(f"Existing outcomes index: {len(outcomes_index)} slugs")
    log(f"Force mode: {args.force}")
    log(f"Dry run: {args.dry_run}")

    updated = 0
    skipped = 0
    errors = 0

    for poc in poc_techniques:
        status, msg = import_technique(poc, outcomes_index, force=args.force)
        if status == "updated":
            updated += 1
            log(f"  UPDATE {msg}")
        elif status == "skip":
            skipped += 1
        else:
            errors += 1
            log(f"  ERROR  {msg}")

    # Save outcomes index
    if not args.dry_run and updated > 0:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(OUTCOMES_PATH, "w") as f:
            json.dump(outcomes_index, f, indent=2)
        log(f"Saved outcomes_index.json ({len(outcomes_index)} slugs)")

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
