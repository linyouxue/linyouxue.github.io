import { getCollection, type CollectionEntry } from 'astro:content';
import { pathFor, type Lang } from './i18n';

export type Article = CollectionEntry<'articles' | 'reviewArticles'>;

export function articlePath(articleId: string, lang: Lang) {
  return pathFor(lang, `/writing/${articleId}/`);
}

function assertPairs(articles: Article[]) {
  const identities = new Map<string, Set<Lang>>();
  for (const { data } of articles) {
    const editions = identities.get(data.articleId) ?? new Set<Lang>();
    if (editions.has(data.lang)) throw new Error(`Duplicate ${data.lang} edition: ${data.articleId}`);
    editions.add(data.lang);
    identities.set(data.articleId, editions);
  }
  for (const [id, editions] of identities) {
    if (!editions.has('en') || !editions.has('zh')) throw new Error(`Article ${id} requires published English and Chinese editions.`);
  }
}

/** Public content boundary, also used by lists and future Work references. */
export async function getArticles(): Promise<Article[]> {
  const published = await getCollection('articles', entry => entry.data.published);
  assertPairs(published);
  const review = process.env.REVIEW_CONTENT === 'true' ? await getCollection('reviewArticles') : [];
  const visible: Article[] = [...published, ...review];
  assertPairs(visible);
  return visible.sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
}

export async function articleRoutes(lang: Lang) {
  return (await getArticles()).filter(entry => entry.data.lang === lang).map(article => ({
    params: { articleId: article.data.articleId }, props: { article },
  }));
}
