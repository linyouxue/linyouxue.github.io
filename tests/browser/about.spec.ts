import { expect, test } from '@playwright/test';

test('About introduces the author and their current interests in both language editions', async ({ page }) => {
  await page.goto('/about/');
  await expect(page.getByRole('heading', { level: 1, name: 'Yuanjing Lin', exact: true })).toBeVisible();
  await expect(page.getByText('Born in 2007', { exact: true })).toBeVisible();
  for (const heading of ['Agents & Skills', 'Scaling & Architectures', 'Diffusion', 'Education', 'Learning by doing', 'Beyond the screen']) {
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
  }
  await expect(page.getByText('2025 — Present', { exact: true })).toBeVisible();
  await expect(page.getByText('Xu Teli Honors Class · Undergraduate in Artificial Intelligence (in progress)', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'UIE fine-tuning', exact: true })).toBeVisible();
  await expect(page.getByText('I love spin and looping with inverted rubber on both sides.', { exact: true })).toBeVisible();
  await expect(page.getByText('Xinjiang and New Zealand are on my wish list.', { exact: true })).toBeVisible();

  await page.getByRole('link', { name: '切换到中文' }).click();
  await expect(page).toHaveURL(/\/zh\/about\/$/);
  await expect(page.getByRole('heading', { level: 1, name: '林元靖', exact: true })).toBeVisible();
  await expect(page.getByText('2007 年生', { exact: true })).toBeVisible();
  for (const heading of ['Agent 与 Skills', '规模与架构', '扩散模型', '教育', '在实践中学习', '屏幕之外']) {
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
  }
  await expect(page.getByText('2025 — 至今', { exact: true })).toBeVisible();
  await expect(page.getByText('徐特立英才班 · 人工智能本科（在读）', { exact: true })).toBeVisible();
  await expect(page.getByText('喜欢旋转，也喜欢双面反胶的弧圈打法。', { exact: true })).toBeVisible();
  await expect(page.getByText('新疆和新西兰，都在我想去的地方清单里。', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Switch to English' }).click();
  await expect(page).toHaveURL(/\/about\/$/);
});

test('About keeps the homepage portrait composition above the centered author identity', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const coverPortrait = page.getByRole('img', { name: 'Linyouxue’s avatar', exact: true });
  const coverImage = await coverPortrait.evaluate(image => {
    const style = getComputedStyle(image);
    return { source: image.getAttribute('src'), fit: style.objectFit, position: style.objectPosition };
  });
  await page.getByRole('link', { name: 'About', exact: true }).click();
  const portrait = page.getByRole('img', { name: 'Linyouxue’s avatar', exact: true });
  await expect(portrait).toHaveAttribute('src', '/assets/avatar.webp');
  const aboutImage = await portrait.evaluate(image => {
    const style = getComputedStyle(image);
    return { source: image.getAttribute('src'), fit: style.objectFit, position: style.objectPosition };
  });
  expect(aboutImage).toEqual(coverImage);
  await expect(portrait).toHaveCSS('transform', 'none');
  const portraitBounds = await portrait.boundingBox();
  const nameBounds = await page.getByRole('heading', { level: 1, name: 'Yuanjing Lin', exact: true }).boundingBox();
  expect(portraitBounds).not.toBeNull();
  expect(nameBounds).not.toBeNull();
  expect(Math.abs(portraitBounds!.x + portraitBounds!.width / 2 - page.viewportSize()!.width / 2)).toBeLessThan(1);
  expect(portraitBounds!.y + portraitBounds!.height).toBeLessThan(nameBounds!.y);
  expect(portraitBounds!.width).toBe(portraitBounds!.height);
});
