const root = document.documentElement;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

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
const tail = document.querySelector<HTMLCanvasElement>('#cursor-tail')!;
const tailContext = tail.getContext('2d')!;
const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
const trailLifetime = 260;
let trail: { x: number; y: number; time: number }[] = [];
let tailFrame: number | undefined;

function resizeTail() {
  const scale = devicePixelRatio || 1;
  tail.width = Math.round(innerWidth * scale);
  tail.height = Math.round(innerHeight * scale);
  tailContext.setTransform(scale, 0, 0, scale, 0, 0);
  trail = [];
}

function drawTail(time: number) {
  trail = trail.filter(point => time - point.time < trailLifetime);
  tailContext.clearRect(0, 0, innerWidth, innerHeight);
  tailContext.lineCap = 'round';
  tailContext.lineWidth = 1.5;
  tailContext.shadowColor = '#b4d9ff';
  tailContext.shadowBlur = 6;
  for (let index = 1; index < trail.length; index++) {
    const previous = trail[index - 1], point = trail[index];
    const opacity = (1 - (time - previous.time) / trailLifetime) * .85;
    tailContext.strokeStyle = `rgba(207,232,255,${opacity})`;
    tailContext.beginPath();
    tailContext.moveTo(previous.x, previous.y);
    tailContext.lineTo(point.x, point.y);
    tailContext.stroke();
  }
  tailFrame = trail.length ? requestAnimationFrame(drawTail) : undefined;
}

function positionStar(x: number, y: number) {
  cursor.style.display = 'block'; cursor.style.left = `${x}px`; cursor.style.top = `${y}px`;
  tail.style.display = 'block';
  trail.push({ x, y, time: performance.now() });
  // Keep the light close to the star even during a fast sweep.
  let length = 0;
  for (let index = trail.length - 1; index > 0; index--) {
    length += Math.hypot(trail[index].x - trail[index - 1].x, trail[index].y - trail[index - 1].y);
    if (length > 180) { trail = trail.slice(index); break; }
  }
  if (tailFrame === undefined) tailFrame = requestAnimationFrame(drawTail);
}

function hideStar() {
  if (tailFrame !== undefined) cancelAnimationFrame(tailFrame);
  tailFrame = undefined; trail = [];
  tailContext.clearRect(0, 0, innerWidth, innerHeight);
  cursor.style.display = 'none'; tail.style.display = 'none';
  document.body.classList.remove('has-stellar-cursor');
}

addEventListener('pointermove', event => {
  if (event.pointerType !== 'mouse' || !finePointer.matches || reducedMotion.matches || document.hidden) return;
  document.body.classList.add('has-stellar-cursor');
  positionStar(event.clientX, event.clientY);
});
document.addEventListener('pointerleave', hideStar);
addEventListener('blur', hideStar);
addEventListener('resize', resizeTail);
finePointer.addEventListener('change', hideStar);
resizeTail();

function stopMotion() {
  clearTimeout(meteorTimer);
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
