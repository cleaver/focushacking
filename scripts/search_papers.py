#!/usr/bin/env python3
"""
Search PubMed for new papers on known techniques.

Usage: python3 scripts/search_papers.py

1. Reads config/techniques.yaml for per-technique search queries
2. Loads data/papers_index.json for existing paper PMIDs
3. Queries PubMed for papers from the last 7 days
4. Deduplicates against known papers
5. Writes new candidates to .hermes/new_candidates.json for agent tagging

Rate limiting: 0.5s between calls (well within 3 req/s no-key limit)
Retries: exponential backoff on 429 (1s, 2s, 4s)
"""

import json
import os
import sys
import time
import re
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
HERMES_DIR = os.path.join(BASE_DIR, ".hermes")

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
RATE_LIMIT_SECONDS = 0.5  # 2 req/s — safe without API key
MAX_RETRIES = 3


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def pubmed_request(url, max_retries=MAX_RETRIES):
    """Make PubMed API call with rate limiting and exponential backoff."""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt  # 1s, 2s, 4s
                log(f"  Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
            elif e.code == 503:
                wait = 5 * (attempt + 1)  # 5s, 10s, 15s
                log(f"  Service unavailable (503), waiting {wait}s...")
                time.sleep(wait)
            else:
                log(f"  HTTP {e.code}: {e.reason}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)
        except (urllib.error.URLError, ConnectionError) as e:
            log(f"  Network error: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(5)
    raise Exception(f"PubMed request failed after {max_retries} retries: {url}")


def esearch(term, mindate, maxdate, retmax=30):
    """Search PubMed and return list of PMIDs."""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": term,
        "mindate": mindate,
        "maxdate": maxdate,
        "datetype": "pdat",
        "retmax": retmax,
        "retmode": "json",
    })
    url = f"{PUBMED_BASE}/esearch.fcgi?{params}"
    time.sleep(RATE_LIMIT_SECONDS)
    data = pubmed_request(url)
    result = json.loads(data)
    return result.get("esearchresult", {}).get("idlist", [])


def efetch_details(pmids):
    """Fetch article details (title, abstract, pubtype, etc.) for PMIDs."""
    if not pmids:
        return {}

    ids = ",".join(str(p) for p in pmids)
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": ids,
        "retmode": "xml",
    })
    url = f"{PUBMED_BASE}/efetch.fcgi?{params}"
    time.sleep(RATE_LIMIT_SECONDS)
    xml_data = pubmed_request(url)

    return parse_pubmed_xml(xml_data)


def parse_pubmed_xml(xml_data):
    """Parse PubMed XML response into structured article data."""
    root = ET.fromstring(xml_data)
    articles = {}

    for article_elem in root.findall(".//PubmedArticle"):
        try:
            pmid_elem = article_elem.find(".//PMID")
            if pmid_elem is None:
                continue
            pmid = pmid_elem.text

            medline = article_elem.find(".//MedlineCitation")
            if medline is None:
                continue

            # Title
            title_elem = article_elem.find(".//ArticleTitle")
            title = "".join(title_elem.itertext()) if title_elem is not None else ""

            # Abstract
            abstract_parts = []
            for abs_text in article_elem.findall(".//AbstractText"):
                label = abs_text.get("Label", "")
                text = "".join(abs_text.itertext())
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = "\n".join(abstract_parts)

            # Publication types
            pubtypes = []
            for pt in article_elem.findall(".//PublicationType"):
                pubtypes.append(pt.text)

            # Authors
            authors = []
            for author in article_elem.findall(".//Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                if last is not None and fore is not None:
                    authors.append(f"{last.text} {fore.text}")
                elif last is not None:
                    authors.append(last.text)

            # Year
            year_elem = article_elem.find(".//PubDate/Year")
            year = int(year_elem.text) if year_elem is not None else 0

            # Journal
            journal_elem = article_elem.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""

            # DOI
            doi = None
            for eid in article_elem.findall(".//ELocationID"):
                if eid.get("EIdType") == "doi":
                    doi = eid.text
                    break

            # MeSH terms
            mesh_terms = []
            for desc in article_elem.findall(".//MeshHeading/DescriptorName"):
                mesh_terms.append(desc.text)

            # Author keywords
            keywords = []
            for kw in article_elem.findall(".//Keyword"):
                keywords.append(kw.text)

            # Article attributes (Has Abstract, etc.)
            attributes = []
            for attr in article_elem.findall(".//ArticleId"):
                if attr.get("IdType") == "pubmed":
                    continue
                attributes.append(attr.text)

            articles[pmid] = {
                "pmid": pmid,
                "title": title,
                "abstract": abstract[:2000],  # Keep abstract to ~2000 chars
                "authors": authors[:5],  # First 5 authors
                "year": year,
                "journal": journal,
                "doi": doi,
                "pubtypes": pubtypes,
                "mesh_terms": mesh_terms,
                "keywords": keywords,
                "tags_source": "mesh" if mesh_terms else "none",
            }

        except Exception as e:
            log(f"  Error parsing article: {e}")
            continue

    return articles


def load_papers_index():
    """Load the existing papers index."""
    path = os.path.join(DATA_DIR, "papers_index.json")
    if not os.path.exists(path):
        return {"metadata": {"version": 1}, "papers": {}}
    with open(path) as f:
        return json.load(f)


def load_techniques_config():
    """Load config/techniques.yaml (simple YAML parsing — just the slug list)."""
    import yaml
    path = os.path.join(CONFIG_DIR, "techniques.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def get_known_pmids(papers_index):
    """Get set of all known paper identifiers from the index."""
    known = set()
    for pid, paper in papers_index.get("papers", {}).items():
        if str(pid).isdigit():
            known.add(str(pid))
        # Also add doi-based ones
        doi = paper.get("doi")
        if doi:
            known.add(doi)
    return known


def main():
    log("Starting paper search...")

    # Load config and index
    config = load_techniques_config()
    papers_index = load_papers_index()
    known_ids = get_known_pmids(papers_index)
    log(f"Loaded {len(known_ids)} known papers across {len(config.get('techniques', []))} techniques")

    # Date range: last 7 days
    today = datetime.now(timezone.utc)
    week_ago = today - timedelta(days=7)
    mindate = week_ago.strftime("%Y/%m/%d")
    maxdate = today.strftime("%Y/%m/%d")
    log(f"Search window: {mindate} to {maxdate}")

    all_candidates = []
    techniques = config.get("techniques", [])

    for technique in techniques:
        slug = technique.get("slug", "")
        name = technique.get("name", "")
        query = technique.get("pubmed_query", f'"{name}"[Title/Abstract]')
        facets_hint = technique.get("facets_hint", [])
        pops_hint = technique.get("populations_hint", [])

        log(f"  Searching: {name} ({slug})")

        try:
            pmids = esearch(query, mindate, maxdate)
        except Exception as e:
            log(f"    ERROR searching: {e}")
            continue

        if not pmids:
            log(f"    No new papers found")
            continue

        # Filter out known papers
        new_pmids = [p for p in pmids if p not in known_ids]

        if not new_pmids:
            log(f"    {len(pmids)} papers, all already known")
            continue

        log(f"    {len(new_pmids)} new papers (of {len(pmids)} total)")

        # Fetch details
        try:
            details = efetch_details(new_pmids)
        except Exception as e:
            log(f"    ERROR fetching details: {e}")
            continue

        for pmid, article in details.items():
            candidate = {
                "pmid": pmid,
                "title": article["title"],
                "abstract": article["abstract"],
                "pubtypes": article["pubtypes"],
                "year": article["year"],
                "journal": article["journal"],
                "doi": article["doi"],
                "authors": article["authors"],
                "sample_size": 0,
                "effect_direction": None,
                "effect_magnitude": None,
                "effect_size_note": "",
                "technique_slug": slug,
                "technique_name": name,
                "mesh_terms": article["mesh_terms"],
                "keywords": article["keywords"],
                "tags_source": article["tags_source"],
                "populations_suggested": [],
                "populations_reason": "",
                "focus_facets_suggested": [],
                "facets_reason": "",
                "confidence": "",
            }

            # If MeSH is available, extract populations and facets automatically
            if article["mesh_terms"]:
                candidate["populations_suggested"] = extract_populations_from_mesh(
                    article["mesh_terms"], article["keywords"], article["title"], article["abstract"]
                )
                candidate["populations_reason"] = "mesh"
                candidate["focus_facets_suggested"] = extract_facets_from_mesh(
                    article["mesh_terms"], article["keywords"], article["title"], article["abstract"]
                )
                candidate["facets_reason"] = "mesh"
                candidate["confidence"] = "high"
            else:
                # No MeSH — mark for LLM tagging
                candidate["populations_suggested"] = extract_populations_from_text(
                    article["title"], article["abstract"], article["keywords"]
                )
                candidate["populations_reason"] = "text"
                candidate["focus_facets_suggested"] = extract_facets_from_text(
                    article["title"], article["abstract"], article["keywords"]
                )
                candidate["facets_reason"] = "text"
                candidate["confidence"] = "low"

            all_candidates.append(candidate)

    # Write candidates
    os.makedirs(HERMES_DIR, exist_ok=True)
    output_path = os.path.join(HERMES_DIR, "new_candidates.json")
    with open(output_path, "w") as f:
        json.dump({
            "generated": today.isoformat(),
            "search_window": f"{mindate} to {maxdate}",
            "candidates": all_candidates,
        }, f, indent=2)

    log(f"\nDone. {len(all_candidates)} candidate papers written to {output_path}")

    # Print summary for the agent
    if all_candidates:
        print("\n--- NEW CANDIDATES ---")
        for c in all_candidates:
            tag_status = "mesh" if c["tags_source"] == "mesh" else "NEEDS LLM"
            print(f"  PMID {c['pmid']}: {c['title'][:70]} [{tag_status}]")
        print("--- END CANDIDATES ---")


# ── Population extraction from MeSH ──────────────────────────────────
POPULATION_MESH_MAP = {
    "Adult": "general_adults",
    "Young Adult": "general_adults",
    "Middle Aged": "general_adults",
    "Aged": "general_adults",
    "Child": "children_adolescents",
    "Adolescent": "children_adolescents",
    "Infant": "children_adolescents",
    "Students": "students",
    "Athletes": "athletes",
    "Occupational Groups": "knowledge_workers",
}

POPULATION_TEXT_KEYWORDS = {
    "students": ["student", "university", "college", "undergraduate", "graduate", "academic"],
    "clinical": ["patient", "clinical", "disorder", "anxiety", "depression", "PTSD",
                  "chronic pain", "insomnia", "ADHD", "therapeutic"],
    "athletes": ["athlete", "sport", "athletic", "sports"],
    "knowledge_workers": ["office", "workplace", "professional", "employee", "worker",
                          "knowledge worker", "manager", "executive"],
    "children_adolescents": ["children", "adolescent", "teen", "youth", "pediatric", "child", "adolescents"],
}


def extract_populations_from_mesh(mesh_terms, keywords, title, abstract):
    """Extract population tags from MeSH terms."""
    pops = set()
    for term in mesh_terms:
        for mesh_val, pop_val in POPULATION_MESH_MAP.items():
            if mesh_val.lower() in term.lower():
                pops.add(pop_val)

    # Also check keywords for specific populations
    for kw in keywords:
        kw_lower = kw.lower()
        for pop, kws in POPULATION_TEXT_KEYWORDS.items():
            for pk in kws:
                if pk in kw_lower:
                    pops.add(pop)

    if not pops:
        pops.add("general_adults")
    return sorted(pops)


def extract_populations_from_text(title, abstract, keywords):
    """Extract population tags from text when no MeSH available."""
    pops = set()
    text = f"{title} {abstract} {' '.join(keywords)}".lower()
    for pop, kws in POPULATION_TEXT_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                pops.add(pop)
                break
    if not pops:
        pops.add("general_adults")
    return sorted(pops)


# ── Facet extraction ─────────────────────────────────────────────────
FACET_MESH_MAP = {
    "Attention": "distraction_resistance",
    "Mindfulness": "distraction_resistance",
    "Executive Function": "deep_work_flow",
    "Cognition": "deep_work_flow",
    "Memory": "studying_learning",
    "Memory, Short-Term": "studying_learning",
    "Learning": "studying_learning",
    "Mental Recall": "studying_learning",
    "Rest": "energy_recovery",
    "Sleep": "energy_recovery",
    "Relaxation": "energy_recovery",
    "Relaxation Therapy": "energy_recovery",
    "Breathing Exercises": "energy_recovery",
    "Exercise": "energy_recovery",
    "Physical Activity": "energy_recovery",
}

FACET_TEXT_KEYWORDS = {
    "distraction_resistance": ["distraction", "attention", "focus", "mind-wandering",
                                "mind wandering", "interruption", "concentration",
                                "sustained attention", "selective attention"],
    "studying_learning": ["memory", "learning", "retention", "recall", "study",
                          "academic", "exam", "test performance", "grade"],
    "deep_work_flow": ["flow", "deep work", "absorption", "engagement", "immersion",
                       "cognitive performance", "executive function", "productivity"],
    "energy_recovery": ["recovery", "rest", "fatigue", "break", "relaxation",
                        "sleep", "nap", "stress reduction", "cortisol", "restoration"],
}


def extract_facets_from_mesh(mesh_terms, keywords, title, abstract):
    """Extract focus facet tags from MeSH terms."""
    facets = set()
    for term in mesh_terms:
        for mesh_val, facet_val in FACET_MESH_MAP.items():
            if mesh_val.lower() in term.lower():
                facets.add(facet_val)

    # Also check keywords
    for kw in keywords:
        kw_lower = kw.lower()
        for facet, kws in FACET_TEXT_KEYWORDS.items():
            for fk in kws:
                if fk in kw_lower:
                    facets.add(facet)

    if not facets:
        facets.add("distraction_resistance")
    return sorted(facets)


def extract_facets_from_text(title, abstract, keywords):
    """Extract focus facet tags from text when no MeSH available."""
    facets = set()
    text = f"{title} {abstract[:1500]} {' '.join(keywords)}".lower()
    for facet, kws in FACET_TEXT_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                facets.add(facet)
                break
    if not facets:
        facets.add("distraction_resistance")
    return sorted(facets)


if __name__ == "__main__":
    main()
