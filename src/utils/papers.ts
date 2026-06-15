/**
 * Papers data utilities.
 *
 * Loads papers_index.json at build time and provides helpers
 * to query papers by technique slug, grouped by year.
 */

import papersIndex from "../data/papers_index.json";

export interface Paper {
    pmid: string;
    first_seen: string;
    last_updated: string;
    technique_slugs: string[];
    title: string;
    doi: string | null;
    year: number;
    pubtypes: string[];
    populations: string[];
    populations_source: string;
    focus_facets: string[];
    facets_source: string;
    sample_size: number;
    effect_direction: string | null;
    effect_magnitude: string | null;
    effect_size_note: string;
}

export interface PapersByYear {
    [year: number]: Paper[];
}

/** Get all papers for a given technique slug, grouped by year (descending). */
export function getPapersBySlug(slug: string): PapersByYear {
    const byYear: PapersByYear = {};

    for (const [, paper] of Object.entries(papersIndex.papers)) {
        const p = paper as Paper;
        if (p.technique_slugs.includes(slug)) {
            const year = p.year || 0;
            if (!byYear[year]) byYear[year] = [];
            byYear[year].push(p);
        }
    }

    return byYear;
}

/** Format a pubtype string for display. */
export function pubtypeLabel(pubtypes: string[]): string {
    if (!pubtypes || pubtypes.length === 0) return "Study";
    const pt = pubtypes[0];
    // Shorten common types
    if (pt === "Randomized Controlled Trial") return "RCT";
    if (pt === "Randomized crossover") return "RCT";
    if (pt === "Controlled Clinical Trial") return "Controlled Trial";
    return pt;
}

/** Map effect direction to a display label for chips. */
export function effectLabel(
    direction: string | null,
    magnitude: string | null
): string {
    if (!direction && !magnitude) return "\u2014";
    const parts: string[] = [];
    if (magnitude) {
        parts.push(magnitude.charAt(0).toUpperCase() + magnitude.slice(1));
    }
    if (direction === "positive") parts.push("increase");
    else if (direction === "negative") parts.push("decrease");
    else if (direction === "mixed") return "Mixed";
    else if (direction === "none") return "No effect";
    return parts.join(" ") || "\u2014";
}

/** CSS class for effect chip coloring. */
export function effectCssClass(
    direction: string | null,
    magnitude: string | null
): string {
    if (!direction && !magnitude) return "effect-none";
    if (direction === "positive") {
        if (magnitude === "large" || magnitude === "moderate") return "effect-positive";
        if (magnitude === "small") return "effect-small";
        return "effect-positive";
    }
    if (direction === "negative") return "effect-negative";
    if (direction === "mixed") return "effect-mixed";
    if (direction === "none") return "effect-none";
    return "effect-none";
}
