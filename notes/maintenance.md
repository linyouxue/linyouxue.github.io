# 网站维护

这是 Astro 静态个人站点。首版正式文章库和个人工作区均为空；日常内容在本地确认后，再按当次发布安排更新。

## 启动、检查与构建

在项目根目录使用 Node.js 与 npm，首次安装或锁文件更新后运行 `npm ci`。

```sh
npm run dev -- --host 127.0.0.1 --port 4321
npm run check
npm run build
npm run preview -- --host 127.0.0.1 --port 4321
```

`dev` 启动本地开发站点；`check` 检查 Astro 与类型；`build` 生成正式静态产物 `dist/`；`preview` 查看已经生成的产物，不能代替构建。当前正式内容集合没有已发布文章，普通构建生成零篇阅读内容。

审核长文使用独立命令和目录：

```sh
npm run dev:review -- --host 127.0.0.1 --port 4324
npm run build:review
npm run preview -- --outDir dist-review --host 127.0.0.1 --port 4324
```

审核模式读取 `tests/fixtures/articles/`，用于检查双语长文、公式、代码、表格和交互。它不把样例写入正式文章集合；`dist-review/` 与正常的 `dist/` 分开，不把审核样例作为正式内容发布。普通开发和构建不要启用 `REVIEW_CONTENT=true`。同一工作树的 Astro preview 一次只运行一个实例，切换产物前先停止旧实例。

浏览器测试面向已经启动的站点。通过环境变量 `SITE_URL` 指定地址，再使用 `npm run test:browser -- <测试文件>` 运行对应检查。正式空库使用 `tests/browser/site.spec.ts`、`writing.spec.ts`；阅读行为使用审核站点和阅读测试。具体写作与审核操作见 [Writing 与双语文章](writing-guide.md)。

## 主要结构

- `src/pages/`：英文根入口、`zh/` 中文入口与静态路由。
- `src/views/`：主页、Writing、阅读、Work、About 的页面内容。
- `src/components/`：顶栏、语言切换、社交链接及文章中的本地组件。
- `src/styles/`、`src/scripts/`：页面样式和少量交互。
- `src/data/`：作者资料与旧入口记录；`src/lib/`：语言路径、文章读取和退休页面生成。
- `src/content/articles/`：正式 Markdown / MDX 文章；`tests/fixtures/articles/`：独立审核样例。
- `public/`：头像、银河背景、图标和本地字体等静态资源。
- `notes/`：维护与写作说明。

## 写文章与修改个人资料

文章按稳定 `articleId` 维护英文与中文版本，使用 `en.md` / `zh.md` 或 MDX，成对确认后再一起发布。frontmatter、图片、草稿、内容配对及审核方式见 [写作说明](writing-guide.md)，以实际内容模型为准。

`src/data/site.ts` 集中维护站点姓名、首页简介、真实学校邮箱、GitHub 与小红书主页。`src/data/about.ts` 保存 About 的中英个人介绍、研究兴趣、教育、学习实践和生活兴趣。修改资料时同步维护两种语言，不把探索中的问题写成已完成成果。

主页与 About 共同使用 `public/assets/avatar.webp`。更新头像时保持这两个页面使用同一张完整图，不分别截脸或生成替代头像。银河背景和本地社交图标也位于 `public/assets/`。

## 个人工作区的当前范围

Work 目前只有中英空库页，All／Papers／Projects（全部／论文／项目）选择更新选中状态及相应空状态；没有工作内容集合、详情路由、占位作品或文章关联模型。

未来已选方向为按年份统一列表，可筛选本人参与的论文与项目。等作者有真实内容并确认公开范围后，再接入条目、详情、背景、结果、贡献及相关文章。阅读外部论文不等于参与该论文，不能把论文阅读笔记当作个人科研成果。

## 旧功能与发布边界

旧 BPE、美赛文章及下载、播放器、AI 情报数据与缓存链已从本地重构交付树退出，原始内容保留在既有 Git 历史。需要查看时，通过 Git 日志找到删除前的提交再读取文件，不在当前树并排保存旧版副本。

四个旧 `.html` 入口提供退休说明及有效导航，未知地址提供 404 恢复入口。旧 AI 自动更新工作流源码也已在本地删除；这不等于原 GitHub 官网的线上定时计划已停用。

当前工作保存在本地重构分支；已获授权的独立 Sites 预览用于手机审核，与原 GitHub Pages 官网分开。原官网替换、远端推送、PR 和线上旧计划停用，按后续当次明确发布指令执行。不要把本地构建或独立预览的完成视为原官网已经替换。
