import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import { unified } from '@astrojs/markdown-remark';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import readingFootnotes from './src/lib/reading-footnotes.mjs';

export default defineConfig({
  site: 'https://linyouxue.github.io',
  output: 'static',
  trailingSlash: 'always',
  devToolbar: { enabled: false },
  integrations: [mdx()],
  markdown: {
    processor: unified({ remarkPlugins: [remarkMath], rehypePlugins: [rehypeKatex, readingFootnotes] }),
    shikiConfig: { themes: { light: 'github-light', dark: 'github-dark' } },
  },
});
