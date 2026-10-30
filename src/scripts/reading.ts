const body = document.querySelector<HTMLElement>('.article-body');
const chapterLinks = [...document.querySelectorAll<HTMLAnchorElement>('[data-chapter]')];
const headings = [...new Set(chapterLinks.map(link => document.getElementById(decodeURIComponent(link.hash.slice(1)))))].filter((heading): heading is HTMLElement => Boolean(heading));
let scheduled = false;

function updateChapter() {
  scheduled = false;
  let current: HTMLElement | undefined = headings[0];
  for (const heading of headings) {
    if (heading.getBoundingClientRect().top <= 100) current = heading;
  }
  if (scrollY + innerHeight >= document.documentElement.scrollHeight - 4) current = headings.at(-1);
  chapterLinks.forEach(link => {
    if (decodeURIComponent(link.hash.slice(1)) === current?.id) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
}
function scheduleChapter() {
  if (!scheduled) { scheduled = true; requestAnimationFrame(updateChapter); }
}
addEventListener('scroll', scheduleChapter, { passive:true });
addEventListener('resize', scheduleChapter);
addEventListener('hashchange', scheduleChapter);
addEventListener('pageshow', scheduleChapter);
if (body) new ResizeObserver(scheduleChapter).observe(body);
document.fonts.ready.then(scheduleChapter);
scheduleChapter();

const themeButtons = [...document.querySelectorAll<HTMLButtonElement>('[data-theme-toggle]')];
const isChinese = document.documentElement.lang.startsWith('zh');
function describeTheme() {
  const night = document.documentElement.dataset.readingTheme === 'night';
  themeButtons.forEach(button => { button.textContent = isChinese ? (night ? '切换日间' : '切换夜间') : (night ? 'Switch to day' : 'Switch to night'); });
}
themeButtons.forEach(button => button.addEventListener('click', () => {
  const theme = document.documentElement.dataset.readingTheme === 'night' ? 'day' : 'night';
  document.documentElement.dataset.readingTheme = theme;
  try { localStorage.setItem('reading-theme', theme); } catch { /* The current session remains usable. */ }
  describeTheme();
}));
describeTheme();

const mobile = matchMedia('(max-width: 800px)');
const toolbars = [...document.querySelectorAll<HTMLElement>('.mobile-reading-top, .mobile-reading-bottom')];
const toolsTrigger = document.querySelector<HTMLButtonElement>('.reading-tools-trigger');
const main = document.querySelector<HTMLElement>('.reading-main');
let toolsOpen = false;
function showTools(open: boolean) {
  toolsOpen = open && mobile.matches;
  toolbars.forEach(toolbar => { toolbar.hidden = !toolsOpen; });
  toolsTrigger?.setAttribute('aria-expanded', String(toolsOpen));
  if (!toolsOpen && toolbars.some(toolbar => toolbar.contains(document.activeElement))) main?.focus({ preventScroll:true });
}
toolsTrigger?.addEventListener('click', () => {
  showTools(true);
  document.querySelector<HTMLButtonElement>('[data-tools-close]')?.focus({ preventScroll:true });
});
document.querySelector('[data-tools-close]')?.addEventListener('click', () => { showTools(false); toolsTrigger?.focus({ preventScroll:true }); });
mobile.addEventListener('change', () => showTools(false));

// Native scrolling and selection keep ownership of a gesture once it moves or lasts.
let press: { id:number; x:number; y:number; started:number; scroll:number; valid:boolean } | undefined;
const interactive = (target:EventTarget | null) => target instanceof Element && Boolean(target.closest('a, button, input, select, textarea, label, summary, [contenteditable], [role="button"]'));
const hasSelection = () => Boolean(getSelection()?.toString());
body?.addEventListener('pointerdown', event => {
  if (!mobile.matches || !event.isPrimary || event.button !== 0 || interactive(event.target) || hasSelection()) return;
  press = { id:event.pointerId, x:event.clientX, y:event.clientY, started:performance.now(), scroll:scrollY, valid:true };
});
body?.addEventListener('pointermove', event => {
  if (press?.id === event.pointerId && Math.hypot(event.clientX - press.x, event.clientY - press.y) > 10) press.valid = false;
});
body?.addEventListener('pointerup', event => {
  const finished = press;
  press = undefined;
  if (finished?.id === event.pointerId && finished.valid && performance.now() - finished.started < 450 && Math.abs(scrollY - finished.scroll) < 3 && !hasSelection() && !interactive(event.target)) showTools(!toolsOpen);
});
body?.addEventListener('pointercancel', () => { press = undefined; });
addEventListener('scroll', () => { if (press) press.valid = false; }, { passive:true });
addEventListener('blur', () => { press = undefined; });
document.addEventListener('selectionchange', () => {
  if (!hasSelection()) return;
  if (press) press.valid = false;
  // A native word selection can follow the first click of a double click.
  if (mobile.matches && toolsOpen) showTools(false);
});

const contents = document.querySelector<HTMLDialogElement>('#reading-contents');
const contentsButton = document.querySelector<HTMLButtonElement>('[data-contents-open]');
contentsButton?.addEventListener('click', () => contents?.showModal());
document.querySelector('[data-contents-close]')?.addEventListener('click', () => contents?.close());
contents?.querySelectorAll<HTMLAnchorElement>('a').forEach(link => link.addEventListener('click', event => {
  event.preventDefault();
  const heading = document.getElementById(decodeURIComponent(link.hash.slice(1)));
  contents.close();
  showTools(false);
  if (heading) {
    history.pushState(null, '', link.hash);
    heading.setAttribute('tabindex', '-1');
    heading.scrollIntoView({ block:'start', behavior:'instant' });
    heading.focus({ preventScroll:true });
    scheduleChapter();
  }
}));
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && toolsOpen && !contents?.open) {
    showTools(false);
    toolsTrigger?.focus({ preventScroll:true });
  }
});

const fontButton = document.querySelector<HTMLButtonElement>('[data-font-size]');
const scales = [1,1.12,1.25];
function describeFont() {
  const scale = Number(document.documentElement.style.getPropertyValue('--reading-scale')) || 1;
  if (fontButton) fontButton.textContent = `${isChinese ? '字号：' : 'Text size: '}${Math.round(scale * 100)}%`;
}
fontButton?.addEventListener('click', () => {
  const readingTop = document.querySelector<HTMLElement>('#mobile-reading-top:not([hidden])')?.getBoundingClientRect().bottom ?? 0;
  // A point can hit whitespace or a table cell; retain the first visible reading block.
  const block = [...(body?.querySelectorAll<HTMLElement>('p, li, h2, h3, pre, table') ?? [])].find(element => {
    const bounds = element.getBoundingClientRect();
    return bounds.bottom > readingTop && bounds.top < innerHeight;
  });
  const previousTop = block?.getBoundingClientRect().top;
  const current = Number(document.documentElement.style.getPropertyValue('--reading-scale')) || 1;
  const scale = scales[(scales.indexOf(current) + 1) % scales.length];
  document.documentElement.style.setProperty('--reading-scale', String(scale));
  if (block && previousTop !== undefined) scrollBy(0, block.getBoundingClientRect().top - previousTop);
  try { localStorage.setItem('reading-font-scale', String(scale)); } catch { /* The current session remains usable. */ }
  describeFont();
  scheduleChapter();
});
describeFont();

const imageDialog = document.querySelector<HTMLDialogElement>('.image-dialog');
const largeImage = new Image();
let imageTrigger: HTMLButtonElement | undefined;
body?.querySelectorAll<HTMLImageElement>('img').forEach(image => {
  if (image.closest('a, button') || !image.alt) return;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'image-open';
  button.setAttribute('aria-label', `${isChinese ? '放大图片：' : 'Enlarge image: '}${image.alt}`);
  image.replaceWith(button);
  button.append(image);
  button.addEventListener('click', () => {
    if (!imageDialog) return;
    imageTrigger = button;
    largeImage.src = image.currentSrc || image.src;
    largeImage.alt = image.alt;
    imageDialog.querySelector('.image-dialog-scroll')!.replaceChildren(largeImage);
    imageDialog.querySelector<HTMLElement>('[data-image-caption]')!.textContent = image.alt;
    imageDialog.showModal();
  });
});
document.querySelector('[data-image-close]')?.addEventListener('click', () => imageDialog?.close());
imageDialog?.addEventListener('close', () => imageTrigger?.focus({ preventScroll:true }));
