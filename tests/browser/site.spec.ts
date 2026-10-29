import { expect, test } from '@playwright/test';

test('a visitor enters Writing and changes its language without returning to the cover', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: 'Linyouxue', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Enter Writing' }).click();
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
  await page.getByRole('link', { name: 'Research & Projects', exact: true }).click();
  await expect(page).toHaveURL(/\/work\/$/);
  await expect(page.getByText('No work published yet.', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: '切换到中文' }).click();
  await expect(page).toHaveURL(/\/zh\/work\/$/);
  await expect(page.getByText('目前还没有发布个人工作。', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: '关于', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1, name: '关于', exact: true })).toBeVisible();
  await expect(page.getByText('北京理工大学 · 徐特立英才班', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'GitHub', exact: true })).toHaveAttribute('href', 'https://github.com/linyouxue');
  await expect(page.getByRole('link', { name: '小红书', exact: true })).toHaveAttribute('href', 'https://www.xiaohongshu.com/user/profile/685a58ce000000001b01899f');
  await expect(page.getByRole('link', { name: 'linyuanjing@bit.edu.cn', exact: true })).toHaveAttribute('href', 'mailto:linyuanjing@bit.edu.cn');
  await page.getByRole('link', { name: 'Switch to English' }).click();
  await expect(page).toHaveURL(/\/about\/$/);
  await expect(page.getByRole('heading', { level: 1, name: 'About', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Xiaohongshu', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Linyouxue — Home', exact: true }).click();
  await expect(page.getByRole('link', { name: 'GitHub', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Email', exact: true })).toHaveAttribute('href', 'mailto:linyuanjing@bit.edu.cn');
});
