import { expect, test } from '@playwright/test';

test('a bilingual Markdown article is reachable from Writing and renders technical content', async ({ page }) => {
  await page.goto('/writing/');
  await page.getByRole('link', { name: 'A small language model, one token at a time', exact: true }).click({ timeout: 5000 });
  await expect(page).toHaveURL(/\/writing\/small-language-model\/$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('A small language model, one token at a time');
  await expect(page.getByRole('code').filter({ hasText: 'distribution' })).toBeVisible();
  await expect(page.getByRole('table')).toBeVisible();
  await expect(page.locator('math')).toHaveCount(2);
  await expect(page.getByRole('img', { name: 'A sequence of tokens flowing into a probability distribution' })).toBeVisible();
  await page.getByRole('link', { name: '切换到中文' }).click();
  await expect(page).toHaveURL(/\/zh\/writing\/small-language-model\/$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('从一个词元开始，理解小型语言模型如何预测下一个词');
  await page.getByRole('link', { name: 'Switch to English' }).click();
  await expect(page).toHaveURL(/\/writing\/small-language-model\/$/);
  await page.getByRole('link', { name: 'Back to Writing', exact: true }).first().click();
  await expect(page).toHaveURL(/\/writing\/$/);
});

test('a reader enlarges an article image and returns focus to its place', async ({ page }) => {
  await page.goto('/writing/small-language-model/');
  const image = page.getByRole('button', { name:'Enlarge image: A sequence of tokens flowing into a probability distribution', exact:true });
  await image.click({ timeout:5000 });
  const viewer = page.getByRole('dialog', { name:'Image',exact:true });
  await expect(viewer.getByRole('img')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(viewer).toBeHidden();
  await expect(image).toBeFocused();
});

test('a manual night theme preserves reading geometry, survives refresh and works without storage', async ({ page, context }) => {
  await page.goto('/writing/small-language-model/#inspect-one-prediction');
  const paragraph = page.getByRole('paragraph').filter({ hasText:'The following code keeps the selection step explicit.' });
  await expect(paragraph).toBeVisible();
  const before = await paragraph.boundingBox();
  await page.getByRole('button', { name:'Switch to night', exact:true }).click({ timeout:5000 });
  await expect(page.getByRole('button', { name:'Switch to day', exact:true })).toBeVisible();
  const after = await paragraph.boundingBox();
  expect(Math.abs(after!.y - before!.y)).toBeLessThan(2);
  expect(after!.width).toBe(before!.width);
  expect(after!.height).toBe(before!.height);
  await page.reload();
  await expect(page.getByRole('button', { name:'Switch to day', exact:true })).toBeVisible();
  await context.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new Error('Storage unavailable'); };
    Storage.prototype.setItem = () => { throw new Error('Storage unavailable'); };
  });
  await page.reload();
  await page.getByRole('button', { name:'Switch to night', exact:true }).click();
  await expect(page.getByRole('button', { name:'Switch to day', exact:true })).toBeVisible();
});

test('the desktop contents follows anchors, manual reading, history and the end of the article', async ({ page }) => {
  await page.goto('/writing/small-language-model/');
  const contents = page.getByRole('navigation', { name:'On this page', exact:true });
  await contents.getByRole('link', { name:'Inspect one prediction', exact:true }).click();
  await expect(contents.locator('[aria-current="location"]')).toHaveText('Inspect one prediction');
  await expect.poll(async () => (await page.getByRole('heading', { name:'Inspect one prediction', exact:true }).boundingBox())!.y).toBeGreaterThan(0);
  await contents.getByRole('link', { name:'Design a comparison', exact:true }).click();
  await page.goBack();
  await expect(page).toHaveURL(/#inspect-one-prediction$/);
  await expect(contents.locator('[aria-current="location"]')).toHaveText('Inspect one prediction');
  await page.getByRole('heading', { name:'Read the failure carefully', exact:true }).scrollIntoViewIfNeeded();
  await page.mouse.wheel(0, (await page.getByRole('heading', { name:'Read the failure carefully', exact:true }).boundingBox())!.y - 50);
  await expect(contents.locator('[aria-current="location"]')).toHaveText('Read the failure carefully');
  await page.getByRole('link', { name:'Back to Writing', exact:true }).last().scrollIntoViewIfNeeded();
  await expect(contents.locator('[aria-current="location"]')).toHaveText('What to carry forward');
  await expect(contents.locator('[aria-current="location"]')).toHaveCount(1);
  await page.goto('/writing/small-language-model/#design-a-comparison');
  await expect(contents.locator('[aria-current="location"]')).toHaveText('Design a comparison');
});

test('Writing filters real bilingual identities and an MDX note embeds an interactive explanation', async ({ page }) => {
  await page.goto('/writing/');
  await expect(page.getByRole('article')).toHaveCount(2, { timeout:5000 });
  await page.getByRole('button', { name: 'Paper notes', exact:true }).click();
  await expect(page.getByRole('article').filter({ visible:true })).toHaveCount(1);
  await page.getByRole('button', { name:'Search articles',exact:true }).click({ timeout:3000 });
  await page.getByRole('searchbox').fill('not-a-topic');
  await expect(page.getByText('No matching articles.', { exact:true })).toBeVisible();
  await page.getByRole('button', { name:'Clear filters', exact:true }).click();
  await page.getByRole('navigation', { name:'Topics', exact:true }).getByRole('button', { name:'Attention', exact:true }).click();
  await expect(page.getByRole('article').filter({ visible:true })).toHaveCount(1);
  await page.getByRole('link', { name:'Reading attention as a weighted conversation', exact:true }).click();
  await expect(page).toHaveURL(/\/writing\/reading-attention\/$/);
  await page.getByRole('slider', { name:'Temperature', exact:true }).press('End');
  await expect(page.getByRole('status', { name:'Leading candidate probability', exact:true })).toHaveText('0.73');
  await page.getByRole('link', { name:'切换到中文' }).click();
  await expect(page).toHaveURL(/\/zh\/writing\/reading-attention\/$/);
  await expect(page.getByRole('slider', { name:'温度', exact:true })).toBeVisible();
});
