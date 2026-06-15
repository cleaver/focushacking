/**
 * Outcomes data utilities.
 *
 * Loads outcomes_index.json at build time and provides helpers
 * to query outcomes by technique slug.
 */

import outcomesIndex from "../data/outcomes_index.json";

export interface Outcome {
    outcome: string;
    grade: string;
    effect: string;
    note: string;
}

/** Get outcomes for a given technique slug. */
export function getOutcomesBySlug(slug: string): Outcome[] {
    const outcomes = (outcomesIndex as Record<string, Outcome[]>)[slug];
    return outcomes || [];
}

/** Map an outcome evidence grade to a CSS class for grade pips. */
export function outcomeGradeClass(grade: string): string {
    return `outcome-grade-${grade}`;
}

/** Map an effect string to a CSS class for effect chips. */
export function outcomeEffectClass(effect: string): string {
    const e = effect.toLowerCase();
    if (e.includes("moderate") || e.includes("large")) return "effect-positive";
    if (e.includes("small")) return "effect-small";
    if (e.includes("mixed")) return "effect-mixed";
    if (e.includes("no effect") || e.includes("insufficient")) return "effect-none";
    return "effect-none";
}
