import { expect, test } from '@playwright/test';

test('the empty Writing library offers type, topic and text filters without publishing placeholders', async ({ page }) => {
  await page.goto('/writing/');
  await expect(page.getByRole('heading', { level: 1, name: 'Writing', exact: true })).toBeVisible();
  await expect(page.getByText('No articles published yet.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Paper notes', exact: true }).click();
  await page.getByRole('button', { name: 'Search articles', exact:true }).click();
  await page.getByRole('searchbox', { name: 'Search articles' }).fill('transformer');
  await expect(page.getByText('No matching articles.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click();
  await expect(page.getByRole('searchbox')).toHaveValue('');
  await expect(page.getByText('No articles published yet.', { exact: true })).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(0);
  expect((await page.request.get('/writing/small-language-model/')).status()).toBe(404);
  await page.getByRole('link', { name: '切换到中文' }).click();
  await expect(page).toHaveURL(/\/zh\/writing\/$/);
  await expect(page.getByText('目前还没有发布文章。', { exact: true })).toBeVisible();
});
