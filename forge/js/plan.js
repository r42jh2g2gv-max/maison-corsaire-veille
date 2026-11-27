// FORGE — menu de la semaine : recettes maison / Thermomix ou produits tout prêts,
// portions calculées pour coller aux calories du jour, « mangé » → journal, courses.
import { S, esc, $, $$, toast, sheet, confirmBox, today, num, targets, fmtDate } from './ui.js';
import { kv, food, recipes, uid } from './db.js';
import { MEALS } from './data.js';
import { foodPicker, recipeFood } from './nutrition.js';

export const SPLIT = { matin: 0.25, midi: 0.35, collation: 0.10, soir: 0.30 };
let weekOffset = 0;

const iso = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
function weekDays(offset = 0) {
  const d = new Date(); d.setHours(12, 0, 0, 0);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7) + offset * 7);
  return Array.from({ length: 7 }, (_, i) => { const x = new Date(d); x.setDate(d.getDate() + i); return iso(x); });
}
const key = (date, meal) => `${date}|${meal}`;
const save = () => kv.set('plan', S.plan);
export const plannedFor = (date, meal) => S.plan[key(date, meal)] || null;

// Portion conseillée pour atteindre la part de calories du repas.
export function portionFor(e, date, meal) {
  const share = (S.profile?.mealSplit?.[meal] ?? SPLIT[meal]);
  const dayKcal = targets(S.profile, date).kcal;
  let T = dayKcal * share;
  if (meal === 'soir') {
    // le dîner complète la journée : on retire ce qui est déjà prévu aux autres repas
    const others = ['matin', 'midi', 'collation'].map(m => plannedFor(date, m) ? portionFor(plannedFor(date, m), date, m).kcal : dayKcal * SPLIT[m]).reduce((a, b) => a + b, 0);
    T = Math.max(dayKcal * 0.15, dayKcal - others);
  }
  if (e.type === 'free') return { qty: 1, unit: 'portion', kcal: e.kcal, p: e.p, c: e.c, f: e.f };
  if (e.type === 'recipe') {
    const q = e.qty ?? Math.min(4, Math.max(0.25, Math.round((T / (e.kcal || T)) * 4) / 4));
    return { qty: q, unit: 'portion', grams: e.gpp ? Math.round(e.gpp * q) : null, kcal: e.kcal * q, p: e.p * q, c: e.c * q, f: e.f * q };
  }
  const g = e.qty ?? Math.min(1000, Math.max(20, Math.round((T / (e.kcal || 100)) * 100 / 5) * 5));
  const m = g / 100;
  return { qty: g, unit: 'g', grams: g, kcal: e.kcal * m, p: e.p * m, c: e.c * m, f: e.f * m };
}
export function plannedLabel(e, date, meal) {
  const pr = portionFor(e, date, meal);
  if (e.type === 'recipe') return `${num(pr.qty, 2)} portion${pr.qty > 1 ? 's' : ''}${pr.grams ? ' ≈ ' + pr.grams + ' g' : ''} · ${Math.round(pr.kcal)} kcal`;
  if (e.type === 'product') return `${pr.grams} g${e.serving ? ` (≈ ${num(pr.grams / e.serving, 1)} portion)` : ''} · ${Math.round(pr.kcal)} kcal`;
  return `${Math.round(pr.kcal)} kcal`;
}

export async function toggleEaten(date, meal) {
  const e = plannedFor(date, meal); if (!e) return;
  if (e.done) { await food.del(e.done); e.done = null; await save(); return; }
  const pr = portionFor(e, date, meal);
  const id = uid('f');
  await food.put({ id, date, meal, name: e.name, grams: pr.grams || null, portions: pr.unit === 'portion' ? pr.qty : null, kcal: Math.round(pr.kcal), p: +pr.p.toFixed(1), c: +pr.c.toFixed(1), f: +pr.f.toFixed(1), src: 'menu',
    per100: e.type === 'product' ? { kcal: e.kcal, p: e.p, c: e.c, f: e.f, brand: e.brand || '', src: 'off' } : null });
  e.done = id; await save();
}

function entryFrom(f) {
  if (f.free) return { type: 'free', name: f.name, kcal: f.kcal, p: f.p, c: f.c, f: f.f };
  if (f.recipe) return { type: 'recipe', recipeId: f.recipeId, name: f.name, kcal: f.kcal, p: f.p, c: f.c, f: f.f, gpp: f.gpp };
  return { type: 'product', name: f.name, brand: f.brand, kcal: f.kcal, p: f.p, c: f.c, f: f.f, serving: f.serving };
}

export async function renderPlan(el) {
  const days = weekDays(weekOffset);
  let weekKcal = 0, weekTarget = 0;
  const html = days.map(d => {
    const t = targets(S.profile, d);
    let planned = 0;
    const rows = MEALS.map(([m, l]) => {
      const e = plannedFor(d, m);
      if (e) planned += portionFor(e, d, m).kcal;
      return `<div class="pslot ${e?.done ? 'done' : ''}">
        <button class="pmain" data-act="plan-slot" data-d="${d}" data-m="${m}"><small>${l} · ~${Math.round(t.kcal * (SPLIT[m]))} kcal</small>
          ${e ? `<b>${e.type === 'product' ? '🛒 ' : e.type === 'recipe' ? '🍲 ' : ''}${esc(e.name)}</b><small>${plannedLabel(e, d, m)}</small>` : '<span class="muted">+ Planifier</span>'}</button>
        ${e ? `<button class="check ${e.done ? 'on' : ''}" data-act="plan-eat" data-d="${d}" data-m="${m}" aria-label="Mangé">✓</button>` : ''}</div>`;
    }).join('');
    weekKcal += planned; weekTarget += t.kcal;
    return `<section class="card pday ${d === today() ? 'today' : ''}"><div class="row between"><h3>${fmtDate(d, { weekday: 'long', day: 'numeric', month: 'short' })}</h3><span class="muted small">${Math.round(planned)} / ${t.kcal} kcal${t.dayType ? (t.dayType === 'entrainement' ? ' · 🏋️' : ' · 🛋') : ''}</span></div>${rows}</section>`;
  }).join('');
  el.innerHTML = `
  <div class="daynav"><button class="icon-btn" data-act="plan-week" data-d="-1" aria-label="Semaine précédente">‹</button><b>Semaine du ${fmtDate(days[0], { day: 'numeric', month: 'long' })}</b><button class="icon-btn" data-act="plan-week" data-d="1" aria-label="Semaine suivante">›</button></div>
  <section class="card"><p class="small">Planifie tes repas <b>faits maison</b> (recettes, Thermomix) ou <b>tout prêts</b> (produits du commerce) : FORGE calcule la portion à mettre dans ton assiette pour coller à tes calories du jour. Touche ✓ quand c’est mangé : ça part dans ton journal.</p>
    <div class="row gap wrap"><button class="btn sm grow" data-act="plan-fill">✨ Remplir avec mes recettes</button><button class="btn sm ghost grow" data-act="plan-shop">🧾 Courses & batch cooking</button></div>
    <div class="row gap wrap"><a class="btn sm ghost grow" href="#/coach">🤖 Menu Thermomix par Claude</a><button class="btn sm ghost danger grow" data-act="plan-clear">Vider la semaine</button></div>
    <p class="muted small">Prévu cette semaine : ${Math.round(weekKcal)} / ${weekTarget} kcal</p></section>
  ${html}`;
}

function slotSheet(d, m, rerender) {
  const e = plannedFor(d, m);
  const choose = () => foodPicker({
    title: `${MEALS.find(x => x[0] === m)[1]} — ${fmtDate(d)}`,
    onPick: async (f, w) => { const prevDone = e?.done; S.plan[key(d, m)] = entryFrom(f); if (prevDone) await food.del(prevDone); await save(); w.close(); toast('Ajouté au menu'); },
    onClose: rerender,
  });
  if (!e) return choose();
  const pr = portionFor(e, d, m);
  const w = sheet(`<h3>${esc(e.name)}</h3><p class="muted">${e.type === 'recipe' ? 'Fait maison' : e.type === 'product' ? 'Tout prêt' : 'Repas libre'} · ${plannedLabel(e, d, m)}</p>
    ${e.type !== 'free' ? `<label class="field">${e.type === 'recipe' ? 'Portions' : 'Grammes'} (auto : ${e.type === 'recipe' ? num(portionFor({ ...e, qty: undefined }, d, m).qty, 2) : portionFor({ ...e, qty: undefined }, d, m).qty})<input type="number" inputmode="decimal" id="pq" step="${e.type === 'recipe' ? 0.25 : 5}" value="${pr.qty}"></label>` : ''}
    <div class="row gap"><button class="btn ghost grow" id="pauto">Portion auto</button><button class="btn grow" id="psave">Enregistrer</button></div>
    <button class="btn ghost block" id="pchg">Changer de plat</button>
    <button class="btn ghost block" id="pcopy">Répéter sur les autres jours</button>
    <button class="btn ghost danger block" id="prm">Retirer du menu</button>`, { onClose: rerender });
  $('#psave', w).onclick = async () => { const v = $('#pq', w)?.value; if (v) e.qty = +v; await save(); w.close(); };
  $('#pauto', w).onclick = async () => { delete e.qty; await save(); w.close(); };
  $('#pchg', w).onclick = () => { w.close(); setTimeout(choose, 260); };
  $('#prm', w).onclick = async () => { if (e.done) await food.del(e.done); delete S.plan[key(d, m)]; await save(); w.close(); };
  $('#pcopy', w).onclick = async () => {
    const days = weekDays(weekOffset);
    for (const x of days) if (x !== d && !plannedFor(x, m)) S.plan[key(x, m)] = { ...e, done: null };
    await save(); toast('Répété sur les créneaux libres de la semaine'); w.close();
  };
}

async function autofill() {
  const rr = await recipes.all();
  if (!rr.length) return toast('Ajoute d’abord des recettes (Cookidoo, Claude ou maison)');
  const pools = {
    matin: rr.filter(r => r.meal === 'matin'),
    collation: rr.filter(r => r.meal === 'collation'),
    plat: rr.filter(r => !r.meal || r.meal === 'midi' || r.meal === 'soir'),
  };
  const idx = { matin: 0, collation: 0, plat: 0 };
  let n = 0;
  for (const d of weekDays(weekOffset)) for (const [m] of MEALS) {
    if (plannedFor(d, m)) continue;
    const pool = m === 'matin' ? pools.matin : m === 'collation' ? pools.collation : pools.plat;
    if (!pool.length) continue;
    const g = m === 'matin' ? 'matin' : m === 'collation' ? 'collation' : 'plat';
    // batch cooking : un même plat 2 jours de suite (midi puis soir du lendemain)
    const r = pool[Math.floor(idx[g]++ / (g === 'plat' ? 2 : 1)) % pool.length];
    S.plan[key(d, m)] = entryFrom(recipeFood(r)); n++;
  }
  await save();
  toast(n ? `${n} repas planifiés` : 'Aucun créneau libre ou recette adaptée (indique le repas sur tes recettes)');
}

async function shopping() {
  const days = weekDays(weekOffset);
  const rr = Object.fromEntries((await recipes.all()).map(r => [r.id, r]));
  const rec = {}, prod = {};
  for (const d of days) for (const [m] of MEALS) {
    const e = plannedFor(d, m); if (!e) continue;
    const pr = portionFor(e, d, m);
    if (e.type === 'recipe') { (rec[e.recipeId || e.name] ||= { e, q: 0 }).q += pr.qty; }
    if (e.type === 'product') { (prod[e.name] ||= { e, g: 0 }).g += pr.grams; }
  }
  const lines = [];
  let html = '';
  for (const { e, q } of Object.values(rec)) {
    const r = rr[e.recipeId];
    const factor = r?.portions ? q / r.portions : null;
    html += `<div class="hist-ex"><b>🍲 ${esc(e.name)}</b><span>${num(q, 2)} portions cette semaine${factor ? ` → cuisiner <b>${num(factor, 2)} ×</b> la recette (${r.portions} portions)` : ''}</span>
      ${r?.ingredients?.length ? `<ul class="small">${r.ingredients.map(i => `<li>${esc(i)}${factor && Math.abs(factor - 1) > 0.05 ? ` <i>× ${num(factor, 2)}</i>` : ''}</li>`).join('')}</ul>` : ''}</div>`;
    lines.push(`${e.name} — ${factor ? 'recette × ' + num(factor, 2) : num(q, 2) + ' portions'}`, ...(r?.ingredients || []).map(i => `  - ${i}${factor && Math.abs(factor - 1) > 0.05 ? ' (× ' + num(factor, 2) + ')' : ''}`));
  }
  for (const { e, g } of Object.values(prod)) {
    html += `<div class="hist-ex"><b>🛒 ${esc(e.name)}${e.brand ? ` <small>${esc(e.brand)}</small>` : ''}</b><span>${Math.round(g)} g au total${e.serving ? ` (≈ ${Math.ceil(g / e.serving)} portions)` : ''}</span></div>`;
    lines.push(`${e.name}${e.brand ? ' (' + e.brand + ')' : ''} — ${Math.round(g)} g`);
  }
  const w = sheet(`<h3>Courses & batch cooking</h3>${html || '<p class="muted">Rien de planifié cette semaine.</p>'}${lines.length ? '<button class="btn block" id="scopy">Copier la liste</button>' : ''}`);
  if (lines.length) $('#scopy', w).onclick = async () => { const t = 'Courses FORGE\n' + lines.join('\n'); try { if (navigator.share) await navigator.share({ text: t }); else { await navigator.clipboard.writeText(t); toast('Liste copiée'); } } catch (e) { await navigator.clipboard.writeText(t).catch(() => { }); } };
}

export async function onPlanAction(act, el, rerender) {
  if (act === 'plan-week') { weekOffset += +el.dataset.d; return rerender(); }
  if (act === 'plan-slot') return slotSheet(el.dataset.d, el.dataset.m, rerender);
  if (act === 'plan-eat') { await toggleEaten(el.dataset.d, el.dataset.m); return rerender(); }
  if (act === 'plan-fill') { await autofill(); return rerender(); }
  if (act === 'plan-shop') return shopping();
  if (act === 'plan-clear') {
    if (!(await confirmBox('Vider le menu de cette semaine ? (le journal n’est pas touché)', 'Vider'))) return;
    for (const d of weekDays(weekOffset)) for (const [m] of MEALS) delete S.plan[key(d, m)];
    await save(); rerender();
  }
}
