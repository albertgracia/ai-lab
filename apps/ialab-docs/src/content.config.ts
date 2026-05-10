import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const blog = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/blog" }),
  schema: z.object({
    title: z.string(),
    date: z.string(),
    summary: z.string(),
    tags: z.array(z.string()).default([]),
  }),
});

const docs = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/docs" }),
  schema: z.object({
    title: z.string(),
    summary: z.string(),
    order: z.number().default(999),
  }),
});

const runbooks = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/runbooks" }),
  schema: z.object({
    title: z.string(),
    summary: z.string(),
    severity: z.string().default("info"),
  }),
});

export const collections = {
  blog,
  docs,
  runbooks,
};
