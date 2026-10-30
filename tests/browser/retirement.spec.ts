import { expect, test } from '@playwright/test';

test.use({ reducedMotion: 'reduce' });

test('old article bookmarks explain their retirement and lead to current Writing', async ({ page }) => {
  for (const [path, name] of [
    ['/blog/cs336-byte-level-bpe.html', 'Byte-Level BPE note'],
    ['/blog/mcm-2026-dwts.html', '2026 MCM / ICM project'],
  ]) {
    const response = await page.goto(path);
    expect(response?.status()).toBe(200);
    await expect(page.getByRole('heading', { level: 1, name: 'This page has been retired', exact: true })).toBeVisible();
    await expect(page.getByText(name, { exact: true })).toBeVisible();
    expect(new URL(page.url()).pathname.replace(/\/$/, '')).toBe(path);
    await page.getByRole('link', { name: 'Browse Writing', exact: true }).click();
    await expect(page).toHaveURL(/\/writing\/$/);
    await expect(page.getByRole('main')).toBeVisible();
  }
});

test('old AI and cached-reader links explain the retired service in either language', async ({ page }) => {
  const cacheRequests: string[] = [];
  page.on('request', request => {
    if (/\/data\/(ai-news|readers)\.json/.test(request.url())) cacheRequests.push(request.url());
  });
  for (const path of ['/ai-news.html', '/reader.html?id=jacobian-fable-20260720']) {
    const response = await page.goto(path);
    expect(response?.status()).toBe(200);
    await expect(page.getByText('The AI news feed and its cached reader are no longer maintained on this site.', { exact: true })).toBeVisible();
    expect(new URL(page.url()).pathname).toBe(path.split('?')[0]);
    await page.getByRole('link', { name: '切换到中文' }).click();
    expect(new URL(page.url()).pathname).toBe(`/zh${path.split('?')[0]}`);
    await expect(page.getByRole('heading', { level: 1, name: '此页面已退出新版', exact: true })).toBeVisible();
    await expect(page.getByText('旧版 AI 情报与缓存阅读功能已退出，本站不再维护这项功能。', { exact: true })).toBeVisible();
    await page.getByRole('link', { name: '返回首页', exact: true }).click();
    await expect(page).toHaveURL(/\/zh\/$/);
  }
  expect(cacheRequests).toEqual([]);
});

test('a missing page or retired download returns an honest 404 with working recovery navigation', async ({ page }) => {
  for (const path of ['/a-page-that-does-not-exist/', '/notes/BPE.py']) {
    const response = await page.goto(path);
    expect(response?.status()).toBe(404);
    await expect(page.getByRole('heading', { level: 1, name: 'Page not found', exact: true })).toBeVisible();
    expect(new URL(page.url()).pathname).toBe(path);
    await page.getByRole('link', { name: '切换到中文' }).click();
    await expect(page.getByRole('heading', { level: 1, name: '找不到此页面', exact: true })).toBeVisible();
    await page.getByRole('link', { name: '关于我', exact: true }).click();
    await expect(page).toHaveURL(/\/zh\/about\/$/);
    await expect(page.getByRole('heading', { level: 1, name: '林元靖', exact: true })).toBeVisible();
  }
});
