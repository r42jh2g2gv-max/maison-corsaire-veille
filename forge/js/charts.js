// FORGE — petits graphiques SVG (hors-ligne), une série par graphique, info-bulle au toucher.
const W = 340, H = 170, PL = 38, PR = 10, PT = 12, PB = 24;

function niceTicks(min, max, n = 4) {
  if (min === max) { min -= 1; max += 1; }
  const span = max - min, step0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= step0) || step0;
  const lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step;
  const t = []; for (let v = lo; v <= hi + step / 2; v += step) t.push(+v.toFixed(6));
  return t;
}
const fmtD = (d) => new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
const fmtN = (v) => (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString('fr-FR') : (+v.toFixed(1)).toLocaleString('fr-FR'));

// points: [{x: Date|string, y: number, label?: string}]
export function lineChart(points, { unit = '', id = 'c' + Math.random().toString(36).slice(2, 7), area = true } = {}) {
  if (!points.length) return `<div class="empty-chart">Pas encore de données</div>`;
  const pts = points.map(p => ({ ...p, t: new Date(p.x).getTime() })).sort((a, b) => a.t - b.t);
  const ys = pts.map(p => p.y);
  const ticks = niceTicks(Math.min(...ys), Math.max(...ys));
  const y0 = ticks[0], y1 = ticks[ticks.length - 1];
  const t0 = pts[0].t, t1 = pts[pts.length - 1].t || t0 + 1;
  const sx = (t) => PL + (pts.length === 1 ? (W - PL - PR) / 2 : ((t - t0) / (t1 - t0 || 1)) * (W - PL - PR));
  const sy = (v) => PT + (1 - (v - y0) / (y1 - y0 || 1)) * (H - PT - PB);
  const path = pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p.t).toFixed(1)},${sy(p.y).toFixed(1)}`).join('');
  const areaPath = `${path}L${sx(pts[pts.length - 1].t).toFixed(1)},${H - PB}L${sx(pts[0].t).toFixed(1)},${H - PB}Z`;
  const grid = ticks.map(v => `<line x1="${PL}" x2="${W - PR}" y1="${sy(v)}" y2="${sy(v)}" class="cg"/><text x="${PL - 6}" y="${sy(v) + 3.5}" class="ct" text-anchor="end">${fmtN(v)}</text>`).join('');
  const xl = pts.length > 1 ? `<text x="${PL}" y="${H - 6}" class="ct">${fmtD(pts[0].t)}</text><text x="${W - PR}" y="${H - 6}" class="ct" text-anchor="end">${fmtD(pts[pts.length - 1].t)}</text>` : `<text x="${sx(t0)}" y="${H - 6}" class="ct" text-anchor="middle">${fmtD(t0)}</text>`;
  const marks = pts.length <= 40 ? pts.map(p => `<circle cx="${sx(p.t)}" cy="${sy(p.y)}" r="4" class="cm"/>`).join('') : '';
  const last = pts[pts.length - 1];
  const data = JSON.stringify(pts.map(p => [sx(p.t), sy(p.y), fmtD(p.t), fmtN(p.y), p.label || ''])).replace(/"/g, '&quot;');
  return `<div class="chart" data-chart="${data}" data-unit="${unit}">
  <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Graphique : dernière valeur ${fmtN(last.y)} ${unit}">
    ${grid}${xl}
    ${area ? `<path d="${areaPath}" class="ca"/>` : ''}
    <path d="${path}" class="cl"/>${marks}
    <line class="cx" x1="0" x2="0" y1="${PT}" y2="${H - PB}" style="display:none"/>
    <circle class="ch" r="5" style="display:none"/>
    <rect x="${PL}" y="0" width="${W - PL - PR}" height="${H}" fill="transparent" class="chit"/>
  </svg><div class="ctip" style="display:none"></div></div>`;
}

// bars: [{label, y}]
export function barChart(bars, { unit = '' } = {}) {
  if (!bars.length || bars.every(b => !b.y)) return `<div class="empty-chart">Pas encore de données</div>`;
  const ticks = niceTicks(0, Math.max(...bars.map(b => b.y)));
  const y1 = ticks[ticks.length - 1];
  const bw = (W - PL - PR) / bars.length;
  const sy = (v) => PT + (1 - v / (y1 || 1)) * (H - PT - PB);
  const grid = ticks.map(v => `<line x1="${PL}" x2="${W - PR}" y1="${sy(v)}" y2="${sy(v)}" class="cg"/><text x="${PL - 6}" y="${sy(v) + 3.5}" class="ct" text-anchor="end">${fmtN(v)}</text>`).join('');
  const rects = bars.map((b, i) => {
    const x = PL + i * bw + 2, w = Math.max(2, bw - 4), y = sy(b.y), h = H - PB - y;
    const r = Math.min(4, w / 2, h);
    const d = h <= 0 ? '' : `M${x},${H - PB}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${H - PB}Z`;
    const lbl = (bars.length <= 8 || i % Math.ceil(bars.length / 6) === 0) ? `<text x="${x + w / 2}" y="${H - 6}" class="ct" text-anchor="middle">${b.label}</text>` : '';
    return `<g class="bar"><title>${b.label} : ${fmtN(b.y)} ${unit}</title><path d="${d}" class="cb"/><rect x="${x - 2}" y="${PT}" width="${bw}" height="${H - PT - PB}" fill="transparent" data-tip="${b.label} · ${fmtN(b.y)} ${unit}"/>${lbl}</g>`;
  }).join('');
  return `<div class="chart bars"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Histogramme">${grid}${rects}</svg><div class="ctip" style="display:none"></div></div>`;
}

// Info-bulles (délégation globale).
export function bindCharts(root = document) {
  root.querySelectorAll('.chart[data-chart]').forEach(el => {
    if (el._bound) return; el._bound = true;
    const pts = JSON.parse(el.dataset.chart), unit = el.dataset.unit;
    const svg = el.querySelector('svg'), tip = el.querySelector('.ctip'), cx = el.querySelector('.cx'), ch = el.querySelector('.ch');
    const move = (ev) => {
      const r = svg.getBoundingClientRect();
      const e = ev.touches ? ev.touches[0] : ev;
      const x = (e.clientX - r.left) * (W / r.width);
      let best = pts[0]; for (const p of pts) if (Math.abs(p[0] - x) < Math.abs(best[0] - x)) best = p;
      cx.setAttribute('x1', best[0]); cx.setAttribute('x2', best[0]); cx.style.display = '';
      ch.setAttribute('cx', best[0]); ch.setAttribute('cy', best[1]); ch.style.display = '';
      tip.innerHTML = `<b>${best[3]} ${unit}</b><span>${best[2]}${best[4] ? ' · ' + best[4] : ''}</span>`;
      tip.style.display = '';
      const px = best[0] / W * r.width, tw = tip.offsetWidth;
      tip.style.left = Math.min(Math.max(0, px - tw / 2), r.width - tw) + 'px';
      tip.style.top = Math.max(0, best[1] / H * r.height - 52) + 'px';
    };
    const hide = () => { tip.style.display = 'none'; cx.style.display = 'none'; ch.style.display = 'none'; };
    svg.addEventListener('pointermove', move); svg.addEventListener('pointerdown', move);
    svg.addEventListener('pointerleave', hide);
  });
  root.querySelectorAll('.chart.bars').forEach(el => {
    if (el._bound) return; el._bound = true;
    const tip = el.querySelector('.ctip');
    el.addEventListener('pointerover', (e) => {
      const t = e.target.closest('[data-tip]'); if (!t) { tip.style.display = 'none'; return; }
      const r = el.getBoundingClientRect(), b = t.getBoundingClientRect();
      tip.innerHTML = `<b>${t.dataset.tip}</b>`; tip.style.display = '';
      tip.style.left = Math.min(Math.max(0, b.left - r.left + b.width / 2 - tip.offsetWidth / 2), r.width - tip.offsetWidth) + 'px';
      tip.style.top = '0px';
    });
    el.addEventListener('pointerleave', () => { tip.style.display = 'none'; });
  });
}
