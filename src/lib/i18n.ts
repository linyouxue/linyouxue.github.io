export type Lang = 'en' | 'zh';

/** The path is the English, unprefixed route for the same page. */
export function pathFor(lang: Lang, path = '/') {
  const route = path.startsWith('/') ? path : `/${path}`;
  return lang === 'zh' ? `/zh${route}` : route;
}

export const ui = {
  en: {
    home: 'Home', writing: 'Writing', work: 'Research & Projects', about: 'About',
    enter: 'Enter Writing', technical: 'Technical articles', notes: 'Paper notes',
    writingIntro: 'Technical articles and notes from reading papers.',
    writingEmpty: 'No articles published yet.',
    workIntro: 'Research and projects I have taken part in.',
    workEmpty: 'No work published yet.',
    socialLabel: 'Find me elsewhere',
    contact: 'Get in touch',
  },
  zh: {
    home: '首页', writing: '文章', work: '研究与项目', about: '关于',
    enter: '进入文章', technical: '技术文章', notes: '论文阅读笔记',
    writingIntro: '关于技术的文章，以及阅读论文时的理解与思考。',
    writingEmpty: '目前还没有发布文章。',
    workIntro: '我实际参与的研究与项目。',
    workEmpty: '目前还没有发布个人工作。',
    socialLabel: '社交与联系',
    contact: '与我联系',
  },
} as const;
