import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const techniques = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./techniques" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    category: z.string(),
    grade: z.string(),
    grade_detail: z.string().optional(),
    last_searched: z.coerce.string().optional(),
    total_papers: z.coerce.number().optional(),
    new_papers_this_run: z.coerce.number().optional(),
    difficulty: z.string().optional(),
    time_to_benefit: z.string().optional(),
    populations: z.array(z.string()).optional(),
    focus_facets: z.array(z.string()).optional(),
    summary: z.string().optional(),
    // Allow unknown fields from the markdown frontmatter
  }),
});

export const collections = { techniques };
