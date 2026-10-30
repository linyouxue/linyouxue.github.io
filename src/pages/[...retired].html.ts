import type { APIRoute } from 'astro';
import { retiredPages } from '../data/retired';
import { unavailableHtml } from '../lib/unavailable';

export function getStaticPaths() {
  return retiredPages.flatMap(entry => (['en', 'zh'] as const).map(lang => ({
    params: { retired: `${lang === 'zh' ? 'zh/' : ''}${entry.path.slice(1, -'.html'.length)}` },
    props: { lang, entry },
  })));
}

// HTML endpoints preserve old .html bookmarks without changing the site's slash policy.
export const GET: APIRoute = ({ props }) => new Response(unavailableHtml(props.lang, props.entry), {
  headers: { 'Content-Type': 'text/html; charset=utf-8' },
});
