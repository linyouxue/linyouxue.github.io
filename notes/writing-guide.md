# Writing 与双语文章

正式稿放在 `src/content/articles/<article-id>/`，例如 `en.md` 与 `zh.md`。普通文章使用 Markdown，确需嵌入组件时使用 MDX；正文由 Astro 官方内容集合和 Markdown/MDX 渲染器处理。

每个语言版本的 frontmatter 如下。两版 `articleId` 相同，且只能有一个英文版、一个中文版。内容身份同时用于 `/writing/<articleId>/` 与 `/zh/writing/<articleId>/`，不要随标题调整它。

```yaml
articleId: understanding-attention
lang: en
title: Understanding attention
summary: A short description of the question this article examines.
date: 2026-10-30
kind: technical
tags: [Attention, Language models]
published: false
cover:
  src: ./cover.png
  alt: Describe the information shown in the cover
```

中文版本将 `lang` 改成 `zh`，提供中文标题、摘要、标签和完整正文。`kind` 只使用 `technical`（技术文章）或 `paper-note`（论文阅读笔记）。日期使用年月日；封面可整项省略，无图时自然排版文字。图片放在文章旁边，用相对路径引用；正文图片提供有意义的替代文字。

两版经过作者确认后，一起设置 `published: true`。默认不发布，缺任一已发布语言版本、重复身份与语言时构建失败；草稿不出现在正式列表，也不生成可直接访问的正式阅读路由。英文列表每个身份只出现一次，中文列表展示对应中文版。

Markdown 支持标题、列表、引用、脚注、GFM 表格和代码围栏；数学使用 `$...$` 与 `$$...$$`。MDX 可以 import 本地 Astro 组件，例如 `src/components/ProbabilityExample.astro`。标题目录直接来自渲染器，正文不要手写重复的标题 ID。链接、公式、代码和表格都有独立的阅读样式。

## 审核长文

`npm run build` 生成 `dist/`：仅包含已发布的正式双语稿，当前零篇。不要用 `REVIEW_CONTENT=true` 构建正式发布产物。

`npm run build:review` 生成独立 `dist-review/`：把 `tests/fixtures/articles/` 中的未发布长文加载到同样的 Writing 和阅读路由，用于桌面、手机审核。它包含双语 Markdown、MDX、数学、长代码、表格、图片和交互组件。没有外部运行 API，普通构建不包含该集合或这些样例路由。

`npm run dev:review -- --host 127.0.0.1 --port 4324` 启动审核开发服务。静态审核产物可用 `npm run preview -- --outDir dist-review --host 127.0.0.1 --port 4324` 查看；普通产物以相同命令选择 `dist`。同一工作树的 Astro preview 一次只运行一个实例，切换产物前先停止旧实例；需要同时查看时，可把另一份产物交给独立静态服务。

公开空库测试：对普通站点运行 `tests/browser/writing.spec.ts`；阅读行为测试：对审核站点运行 `tests/browser/reading.spec.ts` 和 `tests/browser/reading-mobile.spec.ts`。`SITE_URL` 可指定已运行的本地站点地址。

手机正文短按呼出／收起工具；目录选章后回正文；键盘 Tab 可发现“显示阅读工具”入口。首次日间，主题和手动字号在可用时保存在本机。存储不可用时，本次阅读仍可切换。主题只改颜色，字号变化保留当前段落附近的位置。
