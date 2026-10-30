const root = document.documentElement;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

document.querySelector('#replay-intro')?.addEventListener('click', () => {
  document.body.classList.remove('intro-playing');
  void document.body.offsetWidth;
  document.body.classList.add('intro-playing');
});

const meteorLayer = document.querySelector<HTMLElement>('#meteor-layer')!;
let meteorTimer: number | undefined;
const meteorBatchTimers = new Set<number>();

function spawnMeteor(fromLeft: boolean) {
  if (document.hidden || reducedMotion.matches) return;
  const meteor = document.createElement('i');
  meteor.className = 'meteor';
  const width = innerWidth, height = innerHeight;
  // Covers the trail, head and glow at both offscreen endpoints.
  const margin = 80;
  const x = fromLeft ? -margin : width + margin;
  const targetX = fromLeft ? width + margin : -margin;
  const y = height * (.08 + Math.random() * .16);
  const dx = targetX - x;
  const dy = height * (.18 + Math.random() * .16);
  const duration = width <= 600 ? 1500 + Math.random() * 500 : 2500 + Math.random() * 1000;
  meteor.style.cssText = `left:${x}px;top:${y}px;--dx:${dx}px;--dy:${dy}px;--angle:${Math.atan2(dy, dx)}rad;--duration:${duration}ms`;
  meteorLayer.append(meteor);
  meteor.addEventListener('animationend', () => meteor.remove());
}

function scheduleMeteor(delay = 8000 + Math.random() * 4000) {
  clearTimeout(meteorTimer);
  if (document.hidden || reducedMotion.matches) return;
  meteorTimer = window.setTimeout(() => {
    const fromLeft = Math.random() < .5;
    let offset = 0;
    for (let index = 0; index < 2; index++) {
      if (index > 0) offset += 550 + Math.random() * 300;
      const timer = window.setTimeout(() => {
        meteorBatchTimers.delete(timer);
        spawnMeteor(fromLeft);
      }, offset);
      meteorBatchTimers.add(timer);
    }
    scheduleMeteor();
  }, delay);
}

const cursor = document.querySelector<HTMLElement>('#star-cursor')!;
const tail = document.querySelector<HTMLElement>('#cursor-tail')!;
let previousPointer: { x: number; y: number } | undefined;
let tailTimer: number | undefined;

function positionStar(x: number, y: number) {
  cursor.style.display = 'block'; cursor.style.left = `${x}px`; cursor.style.top = `${y}px`;
  if (previousPointer) {
    const dx = x - previousPointer.x, dy = y - previousPointer.y;
    tail.style.display = 'block'; tail.style.left = `${x}px`; tail.style.top = `${y}px`;
    tail.style.width = `${Math.min(27, Math.hypot(dx, dy) * 2 + 8)}px`;
    tail.style.transform = `translate(-100%,-50%) rotate(${Math.atan2(dy, dx)}rad)`;
    tail.style.opacity = '.3';
    clearTimeout(tailTimer);
    tailTimer = window.setTimeout(() => { tail.style.opacity = '0'; }, 100);
  }
  previousPointer = { x, y };
}

function hideStar() {
  cursor.style.display = 'none'; tail.style.display = 'none'; previousPointer = undefined;
  document.body.classList.remove('has-stellar-cursor');
}

addEventListener('pointermove', event => {
  if (event.pointerType !== 'mouse' || reducedMotion.matches || document.hidden) return;
  document.body.classList.add('has-stellar-cursor');
  positionStar(event.clientX, event.clientY);
});
document.addEventListener('pointerleave', hideStar);

function stopMotion() {
  clearTimeout(meteorTimer); clearTimeout(tailTimer);
  meteorBatchTimers.forEach(timer => clearTimeout(timer)); meteorBatchTimers.clear();
  meteorLayer.replaceChildren();
  hideStar();
}

document.addEventListener('visibilitychange', () => {
  root.dataset.pageHidden = String(document.hidden);
  if (document.hidden) stopMotion();
  else scheduleMeteor();
});
reducedMotion.addEventListener('change', () => {
  stopMotion();
  if (!reducedMotion.matches) scheduleMeteor();
});
root.dataset.pageHidden = String(document.hidden);
scheduleMeteor(1500);
