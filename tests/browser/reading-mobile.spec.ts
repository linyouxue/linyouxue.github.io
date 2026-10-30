import { expect, test } from '@playwright/test';

test.use({ viewport:{ width:390,height:844 }, hasTouch:true });

test('a phone reader reveals overlay tools, chooses a chapter and keeps typography and position', async ({ page }) => {
  await page.goto('/zh/writing/small-language-model/#检查一次真实预测');
  const paragraph = page.getByRole('paragraph').filter({ hasText:'下面的代码把选择步骤单独写出来' });
  await expect(paragraph).toBeVisible();
  await expect(page.getByRole('button', { name:'目录',exact:true })).toBeHidden();
  const before = await paragraph.boundingBox();
  await paragraph.tap();
  await expect(page.getByRole('button', { name:'目录',exact:true })).toBeVisible({ timeout:3000 });
  const after = await paragraph.boundingBox();
  expect(after).toEqual(before);
  await page.getByRole('button', { name:'切换夜间',exact:true }).tap();
  await expect(page.getByRole('button', { name:'切换日间',exact:true })).toBeVisible();
  await page.getByRole('button', { name:/字号/ }).tap();
  await expect(page.getByRole('button', { name:/112%/ })).toBeVisible();
  await page.getByRole('button', { name:'目录',exact:true }).tap();
  const contents = page.getByRole('dialog', { name:'目录',exact:true });
  await contents.getByRole('link', { name:'把问题变成可比较的实验',exact:true }).tap();
  await expect(contents).toBeHidden();
  await expect(page.getByRole('button', { name:'目录',exact:true })).toBeHidden();
  await expect(page.getByRole('heading', { name:'把问题变成可比较的实验',exact:true })).toBeFocused();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('touch scrolling, a held press, selection and a body link keep their native actions', async ({ page, context }) => {
  await page.goto('/writing/small-language-model/#inspect-one-prediction');
  const tools = page.getByRole('button', { name:'Contents',exact:true });
  const paragraph = page.getByRole('paragraph').filter({ hasText:'The following code keeps the selection step explicit.' });
  await expect(paragraph).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const cdp = await context.newCDPSession(page);
  const scrollBefore = await page.evaluate(() => scrollY);
  await cdp.send('Input.dispatchTouchEvent', { type:'touchStart',touchPoints:[{ x:190,y:620 }] });
  await page.evaluate(() => new Promise(requestAnimationFrame));
  await cdp.send('Input.dispatchTouchEvent', { type:'touchMove',touchPoints:[{ x:190,y:490 }] });
  await page.evaluate(() => new Promise(requestAnimationFrame));
  await cdp.send('Input.dispatchTouchEvent', { type:'touchMove',touchPoints:[{ x:190,y:330 }] });
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(scrollBefore + 100);
  await cdp.send('Input.dispatchTouchEvent', { type:'touchEnd',touchPoints:[] });
  await expect(tools).toBeHidden();
  await page.goto('/writing/small-language-model/#inspect-one-prediction');
  const rect = (await paragraph.boundingBox())!;
  const started = await page.evaluate(() => performance.now());
  await cdp.send('Input.dispatchTouchEvent', { type:'touchStart',touchPoints:[{ x:rect.x + 70,y:rect.y + 20 }] });
  // A held gesture needs elapsed input time; no assertion relies on a fixed rendering delay.
  await page.waitForFunction(start => performance.now() - start >= 600, started);
  await cdp.send('Input.dispatchTouchEvent', { type:'touchEnd',touchPoints:[] });
  await expect(tools).toBeHidden();
  await paragraph.dblclick();
  await expect.poll(() => page.evaluate(() => getSelection()?.toString().length ?? 0)).toBeGreaterThan(0);
  await paragraph.tap();
  await expect(tools).toBeHidden();
  await page.evaluate(() => getSelection()?.removeAllRanges());
  await cdp.send('Input.dispatchTouchEvent', { type:'touchStart',touchPoints:[{ x:190,y:400 }] });
  await cdp.send('Input.dispatchTouchEvent', { type:'touchCancel',touchPoints:[] });
  await expect(tools).toBeHidden();
  await paragraph.tap();
  await expect(tools).toBeVisible();
  await paragraph.tap();
  await expect(tools).toBeHidden();
  const footnote = page.getByRole('link', { name:'1',exact:true });
  await footnote.tap();
  await expect(page).toHaveURL(/#user-content-fn-scope$/);
  await expect(tools).toBeHidden();
});

test('a keyboard user discovers the hidden tools and can close the contents under reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion:'reduce' });
  await page.goto('/writing/small-language-model/');
  const trigger = page.getByRole('button', { name:'Show reading tools',exact:true });
  for (let count = 0; count < 15; count++) {
    await page.keyboard.press('Tab');
    if (await trigger.evaluate(element => element === document.activeElement)) break;
  }
  await expect(trigger).toBeFocused();
  await expect(trigger).toBeInViewport();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name:'Hide reading tools',exact:true })).toBeFocused();
  await page.getByRole('button', { name:'Contents',exact:true }).click();
  const dialog = page.getByRole('dialog', { name:'Contents',exact:true });
  await expect(dialog).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('button', { name:'Contents',exact:true })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
  await expect(page.getByRole('button', { name:'Contents',exact:true })).toBeHidden();
});
