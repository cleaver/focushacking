#!/usr/bin/env python3
"""
Update technique markdown files with new papers from tagging step.

Usage: python3 scripts/update_markdown.py

Reads .hermes/tagged_candidates.json (papers tagged by agent or mesh)
and appends them to each technique's markdown file. Also updates
data/papers_index.json with new entries.

Detection: if .hermes/tagged_candidates.json exists, use it.
Otherwise check .hermes/new_candidates.json (raw from search).
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TECHNIQUES_DIR = os.path.join(BASE_DIR, "techniques")
DATA_DIR = os.path.join(BASE_DIR, "data")
HERMES_DIR = os.path.join(BASE_DIR, ".hermes")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_candidates():
    """Load tagged candidates (preferred) or raw candidates."""
    # Check for tagged first
    tagged_path = os.path.join(HERMES_DIR, "tagged_candidates.json")
    raw_path = os.path.join(HERMES_DIR, "new_candidates.json")

    if os.path.exists(tagged_path):
        with open(tagged_path) as f:
            return json.load(f)
    elif os.path.exists(raw_path):
        with open(raw_path) as f:
            return json.load(f)
    else:
        return None


def load_papers_index():
    path = os.path.join(DATA_DIR, "papers_index.json")
    if not os.path.exists(path):
        return {"metadata": {"version": 1, "papers": {}}, "papers": {}}
    with open(path) as f:
        return json.load(f)


def save_papers_index(index):
    path = os.path.join(DATA_DIR, "papers_index.json")
    with open(path, "w") as f:
        json.dump(index, f, indent=2, default=str)


def read_technique_md(slug):
    """Read a technique markdown file, return (frontmatter_dict, body_str, full_content)."""
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
    return frontmatter, body, content


def write_technique_md(slug, content):
    path = os.path.join(TECHNIQUES_DIR, f"{slug}.md")
    with open(path, "w") as f:
        f.write(content)


def papers_section_exists(body):
    """Check if the markdown body already has a ## Papers section."""
    return "## Papers" in body


def append_papers(body, papers_by_year):
    """Append new papers to the Papers section."""
    lines = body.split("\n")

    # Find where the Papers section ends
    papers_start = None
    papers_end = len(lines)

    for i, line in enumerate(lines):
        if line.strip().startswith("## Papers"):
            papers_start = i
        elif papers_start is not None and line.strip().startswith("## ") and i > papers_start:
            papers_end = i
            break

    if papers_start is None:
        # No Papers section — append one
        new_section = ["", "## Papers", ""]
        for year in sorted(papers_by_year.keys(), reverse=True):
            new_section.append(f"### {year}")
            new_section.append("")
            for paper in papers_by_year[year]:
                new_section.extend(format_paper(paper))
                new_section.append("")
        result = body.rstrip() + "\n" + "\n".join(new_section)
        return result

    # Papers section exists — insert before the next ## heading or end
    before = lines[:papers_end]
    after = lines[papers_end:]

    # Check existing years
    existing_years = set()
    for line in lines[papers_start:papers_end]:
        m = re.match(r"^### (\d{4})$", line.strip())
        if m:
            existing_years.add(int(m.group(1)))

    new_section = []
    for year in sorted(papers_by_year.keys(), reverse=True):
        if year in existing_years:
            log(f"    Year {year} already in markdown — skipping (papers may need manual merge)")
            continue
        new_section.append(f"### {year}")
        new_section.append("")
        for paper in papers_by_year[year]:
            new_section.extend(format_paper(paper))
            new_section.append("")

    if not new_section:
        return body

    result = "\n".join(before) + "\n" + "\n".join(new_section) + "\n" + "\n".join(after)
    return result


def format_paper(candidate):
    """Format a paper candidate as markdown lines."""
    lines = []
    title = candidate.get("title", "Untitled")
    pubtypes = candidate.get("pubtypes", [])
    pt_label = pubtypes[0] if pubtypes else "Study"

    lines.append(f"1. **{title}** — *{pt_label}*")

    authors = candidate.get("authors", [])
    if authors:
        lines.append(f"   - Authors: {', '.join(authors[:3])}{' et al.' if len(authors) > 3 else ''}")

    n = candidate.get("sample_size", candidate.get("n", 0))
    if n:
        lines.append(f"   - N={n}")

    doi = candidate.get("doi")
    pmid = candidate.get("pmid")
    if doi and str(doi).startswith("10."):
        lines.append(f"   - DOI: {doi}")
    if pmid and str(pmid).isdigit():
        lines.append(f"   - [PubMed](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")

    # Populations and facets (from tagging)
    pops = candidate.get("populations_suggested", [])
    facets = candidate.get("focus_facets_suggested", [])
    if pops or facets:
        notes = []
        if pops:
            notes.append(f"Population: {', '.join(pops)}")
        if facets:
            notes.append(f"Facets: {', '.join(facets)}")
        lines.append(f"   - {'; '.join(notes)}")

    return lines


def main():
    log("Updating technique markdown files...")

    candidates_data = load_candidates()
    if not candidates_data:
        log("No candidates found — nothing to update.")
        return

    candidates = candidates_data.get("candidates", [])
    if not candidates:
        log("No candidates to process.")
        return

    log(f"Processing {len(candidates)} candidate papers")

    index = load_papers_index()
    papers = index.get("papers", {})
    updated_slugs = set()
    new_papers_count = 0

    # Group candidates by technique slug and year
    by_slug = {}
    for c in candidates:
        slug = c.get("technique_slug", "")
        year = c.get("year", datetime.now().year)
        by_slug.setdefault(slug, {}).setdefault(year, []).append(c)

    total_techniques = len(by_slug)
    log(f"Affects {total_techniques} techniques")

    for slug, years_dict in by_slug.items():
        frontmatter, body, full_content = read_technique_md(slug)
        if frontmatter is None:
            log(f"  WARNING: {slug}.md not found, skipping")
            continue

        # Append papers to markdown
        new_body = append_papers(body, years_dict)
        if new_body != body:
            # Update frontmatter counters
            total_new = sum(len(papers_list) for year_papers in years_dict.values() for papers_list in [year_papers])
            frontmatter["new_papers_this_run"] = frontmatter.get("new_papers_this_run", 0) + total_new
            frontmatter["total_papers"] = frontmatter.get("total_papers", 0) + total_new

            # Rebuild with updated frontmatter
            fm_lines = ["---"]
            for key, value in frontmatter.items():
                if isinstance(value, list):
                    fm_lines.append(f"{key}:")
                    for v in value:
                        fm_lines.append(f"  - {v}")
                elif isinstance(value, str) and "\n" in value:
                    fm_lines.append(f"{key}: |")
                    for line in value.split("\n"):
                        fm_lines.append(f"  {line}")
                elif isinstance(value, bool):
                    fm_lines.append(f"{key}: {'true' if value else 'false'}")
                else:
                    import json as j
                    fm_lines.append(f"{key}: {j.dumps(value)}")
            fm_lines.append("---")

            new_content = "\n".join(fm_lines) + new_body
            write_technique_md(slug, new_content)
            updated_slugs.add(slug)
            log(f"  {slug}.md: +{total_new} papers")

        # Add to papers index
        for year, papers_list in years_dict.items():
            for c in papers_list:
                pmid = c.get("pmid", "")
                if not pmid:
                    continue

                pid_key = str(pmid)
                if pid_key not in papers:
                    papers[pid_key] = {
                        "pmid": pid_key,
                        "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "technique_slugs": [slug],
                        "title": c.get("title", ""),
                        "doi": c.get("doi"),
                        "year": year,
                        "pubtypes": c.get("pubtypes", []),
                        "populations": c.get("populations_suggested", ["general_adults"]),
                        "populations_source": c.get("populations_reason", "text"),
                        "focus_facets": c.get("focus_facets_suggested", ["distraction_resistance"]),
                        "facets_source": c.get("facets_reason", "text"),
                        "sample_size": c.get("sample_size", 0),
                        "effect_direction": c.get("effect_direction"),
                        "effect_magnitude": c.get("effect_magnitude"),
                        "effect_size_note": c.get("effect_size_note", ""),
                    }
                    new_papers_count += 1
                else:
                    # Update existing
                    if slug not in papers[pid_key]["technique_slugs"]:
                        papers[pid_key]["technique_slugs"].append(slug)
                    papers[pid_key]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Save updated index
    index["metadata"]["last_full_search"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    index["metadata"]["total_papers"] = len(papers)
    save_papers_index(index)

    log(f"\nDone. Updated {len(updated_slugs)} technique files, {new_papers_count} new papers in index")

    # Write summary for the agent
    summary_path = os.path.join(HERMES_DIR, "update_summary.json")
    os.makedirs(HERMES_DIR, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump({
            "techniques_updated": sorted(list(updated_slugs)),
            "new_papers": new_papers_count,
            "total_techniques_affected": total_techniques,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)


if __name__ == "__main__":
    main()
