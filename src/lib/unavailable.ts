import baseStyles from '../styles/site.css?inline';
import { site } from '../data/site';
import { pathFor, ui, type Lang } from './i18n';

interface RetiredEntry { path: string; kind: 'article' | 'ai'; name: Record<Lang, string>; }

export function unavailableHtml(lang: Lang, entry?: RetiredEntry) {
  const t = ui[lang];
  const copy = {
    en: {
      eyebrow: 'Earlier version', title: 'This page has been retired',
      description: 'This content belongs to an earlier version of this site and is no longer part of the current site.',
      home: 'Go to homepage', writing: 'Browse Writing', about: 'About me',
    },
    zh: {
      eyebrow: '旧站页面', title: '此页面已退出新版',
      description: '这项内容属于旧版网站，未迁入当前版本。你可以通过下面的入口浏览新版网站。',
      home: '返回首页', writing: '查看文章', about: '关于我',
    },
  }[lang];
  const title = entry ? copy.title : lang === 'en' ? 'Page not found' : '找不到此页面';
  const description = !entry
    ? lang === 'en' ? 'This address does not point to a page on the current site. You can explore the site using the links below.' : '当前网站中没有这个页面。你可以通过下面的入口继续浏览。'
    : entry.kind === 'ai'
    ? lang === 'en' ? 'The AI news feed and its cached reader are no longer maintained on this site.' : '旧版 AI 情报与缓存阅读功能已退出，本站不再维护这项功能。'
    : copy.description;
  const otherLang = lang === 'en' ? 'zh' : 'en';
  return `<!doctype html>
<html lang="${lang === 'zh' ? 'zh-CN' : 'en'}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="${description}">
  <link rel="icon" type="image/svg+xml" href="/site-icon.svg">
  <title>${title} — ${site.name[lang]}</title>
  <style>${baseStyles}
    .unavailable-page { width: min(760px, calc(100% - 48px)); margin: 70px auto 100px; }
    .unavailable-eyebrow { margin-bottom: 20px; color: var(--muted); font-size: 14px; }
    .unavailable-page h1 { max-width: 700px; font-size: clamp(42px, 5vw, 64px); line-height: 1.15; letter-spacing: -.035em; text-wrap: balance; }
    .unavailable-name { margin-top: 28px; color: var(--accent); font: 24px/1.5 var(--serif); }
    .unavailable-description { margin-top: 18px; max-width: 650px; color: var(--muted); font-size: 19px; line-height: 1.8; }
    .recovery-navigation { display: flex; flex-wrap: wrap; gap: 8px 30px; margin-top: 32px; padding-top: 22px; border-top: 1px solid var(--line); }
    .recovery-navigation a { padding-block: 10px; }
    @media (max-width: 600px) {
      .unavailable-page { margin-top: 48px; }
      .unavailable-name { font-size: 22px; }
      .unavailable-description { font-size: 18px; }
    }
  </style>
</head>
<body data-page-kind="content">
  <a class="skip-link" href="#main">${lang === 'en' ? 'Skip to content' : '跳到内容'}</a>
  <header class="site-header">
    <a class="site-name" href="${pathFor(lang)}" aria-label="${lang === 'en' ? 'Linyouxue — Home' : '林元靖 — 首页'}">${site.name[lang]}</a>
    <nav class="site-nav" aria-label="${lang === 'en' ? 'Main navigation' : '主导航'}">
      <a href="${pathFor(lang, '/writing/')}">${t.writing}</a>
      <a href="${pathFor(lang, '/work/')}">${t.work}</a>
      <a href="${pathFor(lang, '/about/')}">${t.about}</a>
    </nav>
    <nav class="language-switch" aria-label="${lang === 'en' ? 'Language' : '语言'}">
      <span aria-current="true">${lang === 'en' ? 'EN' : '中文'}</span>
      <span class="language-divider" aria-hidden="true">/</span>
      <a href="${pathFor(otherLang, entry?.path || '/404/')}" lang="${otherLang === 'zh' ? 'zh-CN' : 'en'}" hreflang="${otherLang === 'zh' ? 'zh-CN' : 'en'}" aria-label="${lang === 'en' ? '切换到中文' : 'Switch to English'}">${lang === 'en' ? '中文' : 'EN'}</a>
    </nav>
  </header>
  <main class="unavailable-page" id="main">
    <p class="unavailable-eyebrow">${entry ? copy.eyebrow : '404'}</p>
    <h1>${title}</h1>
    ${entry ? `<p class="unavailable-name">${entry.name[lang]}</p>` : ''}
    <p class="unavailable-description">${description}</p>
    <nav class="recovery-navigation" aria-label="${lang === 'en' ? 'Explore the current site' : '浏览新版网站'}">
      <a href="${pathFor(lang)}">${copy.home}</a>
      <a href="${pathFor(lang, '/writing/')}">${copy.writing}</a>
      <a href="${pathFor(lang, '/about/')}">${copy.about}</a>
    </nav>
  </main>
</body>
</html>`;
}
