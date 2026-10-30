import { defineCollection, type SchemaContext } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const schema = ({ image }: SchemaContext) => z.object({
  articleId: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
  lang: z.enum(['en', 'zh']),
  title: z.string().min(1),
  summary: z.string().min(1),
  date: z.coerce.date(),
  kind: z.enum(['technical', 'paper-note']),
  tags: z.array(z.string().min(1)).min(1),
  published: z.boolean().default(false),
  cover: z.object({ src: image(), alt: z.string().min(1) }).optional(),
});

const articles = defineCollection({
  loader: glob({ base: './src/content/articles', pattern: '**/*.{md,mdx}' }),
  schema,
});
// Review manuscripts never enter an ordinary build or its content cache.
const reviewArticles = defineCollection({
  loader: process.env.REVIEW_CONTENT === 'true'
    ? glob({ base: './tests/fixtures/articles', pattern: '**/*.{md,mdx}' })
    : async () => [],
  schema,
});
export const collections = { articles, reviewArticles };
