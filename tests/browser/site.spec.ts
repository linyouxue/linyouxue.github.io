import { expect, test } from '@playwright/test';

test('a visitor enters Writing and changes its language without returning to the cover', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: 'Linyouxue', exact: true })).toBeVisible();
  await expect(page.getByRole('img', { name: 'Linyouxue’s avatar', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Blog', exact: true }).click();
  await expect(page).toHaveURL(/\/writing\/$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Writing', exact: true })).toBeVisible();
  await expect(page.getByText('No articles published yet.', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: '切换到中文' }).click();
  await expect(page).toHaveURL(/\/zh\/writing\/$/);
  await expect(page.getByRole('heading', { level: 1, name: '文章', exact: true })).toBeVisible();
  await expect(page.getByText('目前还没有发布文章。', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Switch to English' }).click();
  await expect(page).toHaveURL(/\/writing\/$/);
});

test('a visitor opens Work and About in either language and finds the real contact destinations', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Research', exact: true }).click();
  await expect(page).toHaveURL(/\/work\/$/);
  await expect(page.getByText('No work published yet.', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: '切换到中文' }).click();
  await expect(page).toHaveURL(/\/zh\/work\/$/);
  await expect(page.getByText('目前还没有发布个人工作。', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: '关于', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1, name: '林元靖', exact: true })).toBeVisible();
  await expect(page.getByRole('img', { name: '林元靖的网头', exact: true })).toBeVisible();
  await expect(page.getByText('徐特立英才班 · 人工智能本科（在读）', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'GitHub', exact: true })).toHaveAttribute('href', 'https://github.com/linyouxue');
  await expect(page.getByRole('link', { name: '小红书', exact: true })).toHaveAttribute('href', 'https://www.xiaohongshu.com/user/profile/685a58ce000000001b01899f');
  await expect(page.getByRole('link', { name: 'linyuanjing@bit.edu.cn', exact: true })).toHaveAttribute('href', 'mailto:linyuanjing@bit.edu.cn');
  await page.getByRole('link', { name: 'Switch to English' }).click();
  await expect(page).toHaveURL(/\/about\/$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Yuanjing Lin', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Xiaohongshu', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Linyouxue — Home', exact: true }).click();
  await expect(page.getByRole('link', { name: 'GitHub', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Email', exact: true })).toHaveAttribute('href', 'mailto:linyuanjing@bit.edu.cn');
});

test('the Chinese cover keeps its language across all four destinations', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: '切换到中文' }).click();
  await expect(page).toHaveURL(/\/zh\/$/);
  const navigation = page.getByRole('navigation', { name: '主导航', exact: true });
  await navigation.getByRole('link', { name: '首页', exact: true }).click();
  await expect(page).toHaveURL(/\/zh\/$/);
  for (const [label, path, heading] of [
    ['博客', 'writing', '文章'],
    ['研究与项目', 'work', '研究与项目'],
    ['关于', 'about', '林元靖'],
  ]) {
    await navigation.getByRole('link', { name: label, exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/zh/${path}/$`));
    await expect(page.getByRole('heading', { level: 1, name: heading, exact: true })).toBeVisible();
    await page.getByRole('link', { name: '林元靖 — 首页', exact: true }).click();
  }
  await page.getByRole('link', { name: 'Switch to English' }).click();
  await expect.poll(() => new URL(page.url()).pathname).toBe('/');
  await expect(page.getByRole('navigation', { name: 'Main navigation', exact: true }).getByRole('link')).toHaveCount(4);
});

test('reduced motion presents an immediately usable static cover on a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/zh/');
  await expect(page.getByRole('img', { name: '林元靖的网头', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { level: 1, name: '林元靖', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '重播', exact: true }).click();
  await expect.poll(() => page.evaluate(() => document.getAnimations().length)).toBe(0);
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('link', { name: '博客', exact: true }).click();
  await expect(page.getByText('目前还没有发布文章。', { exact: true })).toBeVisible();
});

test('the first two shooting stars travel from the same offscreen side to the other', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const tracks = await page.evaluate(() => new Promise<Array<{ start: number; end: number; time: number }>>(resolve => {
    const paths = new Map<Element, { start: number; end: number; time: number }>();
    const completed: Array<{ start: number; end: number; time: number }> = [];
    const onStart = (event: AnimationEvent) => {
      const element = event.target;
      if (!(element instanceof Element) || !element.closest('[aria-hidden="true"]')) return;
      const rect = element.getBoundingClientRect();
      if (rect.width > 16 || rect.height > 16 || rect.width === 0) return;
      paths.set(element, { start: rect.x, end: rect.x, time: performance.now() });
    };
    const onEnd = (event: AnimationEvent) => {
      const element = event.target;
      if (!(element instanceof Element)) return;
      const path = paths.get(element);
      if (!path) return;
      path.end = element.getBoundingClientRect().x;
      completed.push(path);
      if (completed.length === 2) {
        document.removeEventListener('animationstart', onStart, true);
        document.removeEventListener('animationend', onEnd, true);
        resolve(completed);
      }
    };
    document.addEventListener('animationstart', onStart, true);
    document.addEventListener('animationend', onEnd, true);
  }));
  expect(tracks).toHaveLength(2);
  const direction = Math.sign(tracks[0].end - tracks[0].start);
  for (const track of tracks) {
    expect(Math.sign(track.end - track.start)).toBe(direction);
    expect(Math.min(track.start, track.end)).toBeLessThan(-60);
    expect(Math.max(track.start, track.end)).toBeGreaterThan(450);
  }
  expect(Math.abs(tracks[1].time - tracks[0].time)).toBeGreaterThan(500);
});
