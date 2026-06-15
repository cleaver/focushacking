#!/usr/bin/env python3
"""
Migration script: reads techniques_v2.json from the PoC site and generates:
  - techniques/*.md  — one markdown file per technique
  - data/papers_index.json  — persistent paper database
  - config/techniques.yaml  — per-technique search config (seeded)
  - config/grading-rules.yaml

Usage: python3 scripts/migrate_from_poc.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

POC_PATH = "/home/cleaver/fhpoc/techniques_v2.json"
TECHNIQUES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "techniques")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

# ── Facet mapping rules ───────────────────────────────────────────────
# Derived from technique category + outcomes + mechanism
FACET_BY_CATEGORY = {
    "Time Management": ["distraction_resistance", "deep_work_flow"],
    "Mindfulness": ["distraction_resistance", "deep_work_flow"],
    "Physical": ["energy_recovery", "studying_learning"],
    "Breathing": ["distraction_resistance", "energy_recovery"],
    "Environment": ["distraction_resistance", "energy_recovery"],
    "Cognitive": ["studying_learning", "deep_work_flow"],
    "Technology": ["distraction_resistance"],
}

FACET_BY_OUTCOME_KEYWORD = {
    "Sustained Attention": "distraction_resistance",
    "Task Completion": "deep_work_flow",
    "Stress Reduction": "energy_recovery",
    "Memory": "studying_learning",
    "Learning": "studying_learning",
    "Cognitive Performance": "deep_work_flow",
    "Focus": "distraction_resistance",
    "Procrastination": "distraction_resistance",
    "Fatigue": "energy_recovery",
    "Productivity": "deep_work_flow",
    "Anxiety": "energy_recovery",
    "Processing Speed": "deep_work_flow",
    "Executive Function": "deep_work_flow",
    "Academic Performance": "studying_learning",
}

# ── Population mapping rules ──────────────────────────────────────────
# Default is general_adults. Specific keywords trigger additional tags.
POPULATION_KEYWORDS = {
    "students": ["student", "university", "college", "classroom", "academic", "school", "undergraduate"],
    "clinical": ["patient", "clinical", "disorder", "anxiety", "depression", "PTSD",
                  "chronic pain", "insomnia", "ADHD", "therapeutic", "treatment"],
    "athletes": ["athlete", "sport", "exercise performance", "physical performance"],
    "knowledge_workers": ["office", "workplace", "professional", "employee", "knowledge worker",
                          "manager", "executive", "software developer"],
    "children_adolescents": ["children", "adolescent", "teen", "youth", "pediatric", "child"],
}


def slugify(name):
    s = name.lower()
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("'", "").replace('"', "")
    s = s.replace("(", "").replace(")", "")
    s = s.replace("/", "-").replace("\\", "-")
    s = s.replace(",", "").replace(".", "")
    s = s.replace(":", "").replace(";", "")
    s = s.replace(" ", "-")
    s = re.sub(r"-+", "-", s)  # collapse multiple hyphens
    s = s.strip("-")
    return s


def design_to_pubtype(design_str):
    """Map study design strings to PubMed publication types for grading."""
    if not design_str:
        return ["Unknown"]
    d = design_str.lower()
    if "meta-analysis" in d or "meta analysis" in d:
        return ["Meta-Analysis"]
    if "systematic review" in d:
        return ["Systematic Review"]
    if "rct" in d or "randomized controlled" in d or "randomized crossover" in d:
        return ["Randomized Controlled Trial"]
    if "controlled trial" in d or "controlled study" in d:
        return ["Controlled Clinical Trial"]
    if "randomized" in d:
        return ["Randomized Controlled Trial"]
    if "cohort" in d or "longitudinal" in d:
        return ["Observational Study"]
    if "case" in d.lower():
        return ["Case Study"]
    if "survey" in d or "correlational" in d or "observational" in d:
        return ["Observational Study"]
    if "review" in d:
        return ["Review"]
    return ["Journal Article"]


def infer_populations(technique):
    """Infer population tags from study data."""
    pops = set()
    pops.add("general_adults")

    for study in technique.get("studies", []):
        text = f"{study.get('title', '')} {study.get('finding', '')}"
        text_lower = text.lower()
        for pop, keywords in POPULATION_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    pops.add(pop)
                    break

    # Also check technique description and steps
    desc_text = f"{technique.get('description', '')} {' '.join(technique.get('steps', []))} {technique.get('example', '')}"
    desc_lower = desc_text.lower()
    for pop, keywords in POPULATION_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                pops.add(pop)
                break

    return sorted(pops, key=lambda x: (x != "general_adults", x))


def infer_facets(technique):
    """Infer focus facet tags from category, outcomes, and studies."""
    facets = set()
    category = technique.get("category", "")

    # Category-based baseline
    base = FACET_BY_CATEGORY.get(category, ["distraction_resistance"])
    facets.update(base)

    # Outcome-based refinement
    for outcome in technique.get("outcomes", []):
        oname = outcome.get("outcome", "")
        for kw, facet in FACET_BY_OUTCOME_KEYWORD.items():
            if kw.lower() in oname.lower():
                facets.add(facet)

    # Study finding-based refinement
    for study in technique.get("studies", []):
        text = f"{study.get('title', '')} {study.get('finding', '')}"
        text_lower = text.lower()
        for kw, facet in {
            "memory": "studying_learning",
            "retention": "studying_learning",
            "recall": "studying_learning",
            "academic": "studying_learning",
            "exam": "studying_learning",
            "distraction": "distraction_resistance",
            "mind-wandering": "distraction_resistance",
            "interruption": "distraction_resistance",
            "flow": "deep_work_flow",
            "absorption": "deep_work_flow",
            "deep work": "deep_work_flow",
            "recovery": "energy_recovery",
            "rest": "energy_recovery",
            "fatigue": "energy_recovery",
            "break": "energy_recovery",
        }.items():
            if kw in text_lower:
                facets.add(facet)

    return sorted(facets)


def extract_pmid_from_url(url):
    """Try to extract PMID or DOI from a URL."""
    if not url:
        return None
    m = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', url)
    if m:
        return int(m.group(1))
    m = re.search(r'doi\.org/(10\.\S+)', url)
    if m:
        return m.group(1)
    m = re.search(r'10\.(\d+)/\S+', url)
    if m:
        return f"doi:{m.group(0)}"
    return url  # fallback: use raw URL as identifier


def generate_markdown(technique):
    """Generate a complete .md file for a technique from its JSON data."""
    name = technique["name"]
    slug = slugify(name)
    category = technique.get("category", "Uncategorized")
    grade = technique.get("evidence_grade", "?")
    grade_detail = technique.get("grade_rationale", "")
    difficulty = technique.get("difficulty", "Beginner").lower()
    time_to_benefit = technique.get("time_to_benefit", "Unknown")
    description = technique.get("description", "")
    mechanism = technique.get("mechanism", "")
    steps = technique.get("steps", [])
    example = technique.get("example", "")

    populations = infer_populations(technique)
    facets = infer_facets(technique)
    studies = technique.get("studies", [])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = []
    lines.append("---")
    lines.append(f'title: "{name}"')
    lines.append(f"slug: {slug}")
    lines.append(f'category: "{category}"')
    lines.append(f"grade: {grade}")
    lines.append(f'grade_detail: "{grade_detail}"')
    lines.append(f"last_searched: {now}")
    lines.append(f"total_papers: {len(studies)}")
    lines.append(f"new_papers_this_run: 0")
    lines.append(f"difficulty: {difficulty}")
    lines.append(f'time_to_benefit: "{time_to_benefit}"')
    lines.append(f"populations:")
    for p in populations:
        lines.append(f"  - {p}")
    lines.append(f"focus_facets:")
    for f in facets:
        lines.append(f"  - {f}")
    summary = description.replace("\n", " ").strip()[:300]
    lines.append(f'summary: "{summary}"')
    lines.append(f'what_it_is: |')
    for line in wrap_text(summary, 72):
        lines.append(f"  {line}")
    lines.append("how_to_do_it: |")
    for i, step in enumerate(steps, 1):
        clean = step.strip()
        lines.append(f"  {i}. {clean}")
    lines.append(f'mechanism: "{mechanism}"')
    lines.append("---")
    lines.append("")
    lines.append(f"## {name}")
    lines.append("")
    lines.append(description)
    lines.append("")

    if example:
        lines.append("### Example")
        lines.append("")
        lines.append(example)
        lines.append("")

    # Papers are now stored in data/papers_index.json — not duplicated into markdown body.
    # Use scripts/update_markdown.py to populate the index from POC studies.

    return "\n".join(lines), populations, facets


def wrap_text(text, width=72):
    """Simple text wrapper that preserves line breaks."""
    if not text:
        return [""]
    words = text.split()
    lines = []
    current = ""
    for w in words:
        if len(current) + len(w) + 1 > width:
            lines.append(current)
            current = w
        else:
            current = (current + " " + w).strip()
    if current:
        lines.append(current)
    return lines if lines else [""]


def build_papers_index(techniques_data):
    """Build the persistent papers index from all technique data."""
    index = {}
    pmid_counter = 1  # Use sequential IDs for papers without PMIDs

    for technique in techniques_data:
        slug = slugify(technique["name"])
        populations = infer_populations(technique)
        facets = infer_facets(technique)

        for s in technique.get("studies", []):
            pmid = s.get("pubmed_url", "")
            if not pmid:
                continue

            # Generate a stable ID from the URL if possible
            paper_id = extract_pmid_from_url(pmid)
            if not paper_id:
                paper_id = f"local-{pmid_counter}"
                pmid_counter += 1

            if paper_id not in index:
                pubtypes = design_to_pubtype(s.get("design", ""))
                # Map PoC effect labels to direction + magnitude
                effect_label = s.get("effect", "")
                effect_direction = "positive"
                effect_magnitude = "small"
                if effect_label == "Large increase":
                    effect_direction, effect_magnitude = "positive", "large"
                elif effect_label == "Moderate increase":
                    effect_direction, effect_magnitude = "positive", "moderate"
                elif effect_label == "Small increase":
                    effect_direction, effect_magnitude = "positive", "small"
                elif effect_label == "Mixed":
                    effect_direction, effect_magnitude = "mixed", "small"
                elif effect_label == "No effect":
                    effect_direction, effect_magnitude = "null", "none"

                index[paper_id] = {
                    "pmid": paper_id if isinstance(paper_id, int) else str(paper_id),
                    "first_seen": str(s.get("year", datetime.now().year)),
                    "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "technique_slugs": [slug],
                    "title": s.get("title", ""),
                    "doi": paper_id if isinstance(paper_id, str) and paper_id.startswith("doi:") else None,
                    "year": s.get("year", 0),
                    "pubtypes": pubtypes,
                    "populations": populations if populations else ["general_adults"],
                    "populations_source": "keyword",
                    "focus_facets": facets,
                    "facets_source": "keyword",
                    "sample_size": s.get("n", 0) if isinstance(s.get("n", 0), int) else 0,
                    "effect_direction": effect_direction,
                    "effect_magnitude": effect_magnitude,
                    "effect_size_note": s.get("finding", "")[:200],
                }
            else:
                # Paper already indexed — add technique slug if not present
                if slug not in index[paper_id]["technique_slugs"]:
                    index[paper_id]["technique_slugs"].append(slug)

    return index


def generate_techniques_yaml(techniques_data):
    """Generate config/techniques.yaml with PubMed search strategies."""
    lines = ["# Focus Hacking — Technique Search Configuration"]
    lines.append("# Each entry defines how the pipeline searches PubMed for new papers.")
    lines.append(f"# Auto-generated from PoC data on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append("techniques:")
    lines.append("")

    for t in techniques_data:
        slug = slugify(t["name"])
        name = t["name"]
        category = t.get("category", "")
        facets = infer_facets(t)

        # Build a sensible PubMed query from the technique name + category
        query_terms = [f'"{name}"[Title/Abstract]']
        cat_keywords = {
            "Mindfulness": '("mindfulness"[MeSH] OR "meditation"[MeSH])',
            "Physical": '("exercise"[MeSH] OR "physical activity"[Title/Abstract])',
            "Breathing": '("breathing exercises"[MeSH] OR "respiratory therapy"[MeSH])',
            "Cognitive": '("cognition"[MeSH] OR "cognitive training"[Title/Abstract])',
        }
        if category in cat_keywords:
            query_terms.append(cat_keywords[category])
        query_terms.append('("attention"[MeSH] OR "focus"[Title/Abstract] OR "executive function"[MeSH])')
        pubmed_query = " AND ".join(query_terms)

        # MeSH terms
        mesh_mapping = {
            "Time Management": ["Attention", "Time Management", "Executive Function"],
            "Mindfulness": ["Mindfulness", "Attention", "Meditation"],
            "Physical": ["Exercise", "Attention", " Cognition"],
            "Breathing": ["Breathing Exercises", "Attention", "Relaxation"],
            "Environment": ["Environment", "Attention", "Cognition"],
            "Cognitive": ["Cognition", "Learning", "Memory"],
            "Technology": ["Attention", "Cell Phone Use", "Technology"],
        }
        mesh_terms = mesh_mapping.get(category, ["Attention"])

        lines.append(f"  - name: \"{name}\"")
        lines.append(f"    slug: {slug}")
        # Use single-quoted YAML to avoid escaping issues with PubMed quotes
        escaped_query = pubmed_query.replace("'", "''")
        lines.append(f"    pubmed_query: '{escaped_query}'")
        lines.append(f"    mesh_terms: {json.dumps(mesh_terms)}")
        lines.append(f"    populations_hint: {json.dumps(infer_populations(t))}")
        lines.append(f"    facets_hint: {json.dumps(facets)}")
        lines.append("")

    return "\n".join(lines)


def main():
    print("Loading PoC data...")
    with open(POC_PATH) as f:
        techniques = json.load(f)

    print(f"Loaded {len(techniques)} techniques from PoC data")

    # Create directories
    os.makedirs(TECHNIQUES_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Generate markdown files
    print("\nGenerating technique markdown files...")
    all_pops = {}
    all_facets = {}
    for t in techniques:
        slug = slugify(t["name"])
        md_content, pops, facets = generate_markdown(t)
        path = os.path.join(TECHNIQUES_DIR, f"{slug}.md")
        with open(path, "w") as f:
            f.write(md_content)
        all_pops[slug] = pops
        all_facets[slug] = facets
        print(f"  {slug}.md — Grade {t.get('evidence_grade','?')} — {len(t.get('studies',[]))} papers — pops={pops} — facets={facets}")

    # Build papers index
    print("\nBuilding papers index...")
    index = build_papers_index(techniques)
    total_papers = len(index)

    index_doc = {
        "metadata": {
            "version": 1,
            "last_full_search": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "techniques_tracked": len(techniques),
            "total_papers": total_papers,
        },
        "papers": index,
    }

    index_path = os.path.join(DATA_DIR, "papers_index.json")
    with open(index_path, "w") as f:
        json.dump(index_doc, f, indent=2, default=str)
    print(f"  {total_papers} papers indexed across {len(techniques)} techniques")
    print(f"  Written to data/papers_index.json")

    # Generate config/techniques.yaml
    print("\nGenerating config/techniques.yaml...")
    yaml_content = generate_techniques_yaml(techniques)
    yaml_path = os.path.join(CONFIG_DIR, "techniques.yaml")
    with open(yaml_path, "w") as f:
        f.write(yaml_content)
    print(f"  Written to config/techniques.yaml")

    print("\nMigration complete!")
    print(f"  Techniques: {len(techniques)} markdown files in techniques/")
    print(f"  Papers: {total_papers} in data/papers_index.json")
    print(f"  Config: config/techniques.yaml")


if __name__ == "__main__":
    main()
