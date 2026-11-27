// FORGE — menu de la semaine : recettes maison / Thermomix ou produits tout prêts,
// portions calculées pour coller aux calories du jour, « mangé » → journal, courses.
import { S, esc, $, $$, toast, sheet, confirmBox, today, num, targets, fmtDate, defTime } from './ui.js';
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
  await food.put({ id, date, meal, time: defTime(date, meal), name: e.name, grams: pr.grams || null, portions: pr.unit === 'portion' ? pr.qty : null, kcal: Math.round(pr.kcal), p: +pr.p.toFixed(1), c: +pr.c.toFixed(1), f: +pr.f.toFixed(1), src: 'menu',
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

// ————— Liste de courses par rayon —————
const AISLES = [
  ['🥦 Fruits & légumes', /oignon|ail\b|échalote|carotte|tomate|courgette|poivron|brocoli|épinard|salade|champignon|pomme de terre|patate|citron|banane|pomme|fruits? rouges?|framboise|myrtille|fraise|avocat|concombre|haricots? verts?|poireau|chou|persil|coriandre|basilic|ciboulette|menthe|gingembre|aubergine|potiron|butternut|courge|céleri|kiwi|orange|mangue|ananas|poire|raisin|légume|fruit/i],
  ['🥩 Viandes & poissons', /poulet|dinde|bœuf|boeuf|steak|haché|porc|jambon|lardon|saumon|thon|cabillaud|colin|crevette|poisson|viande|merguez|saucisse|veau|agneau|chorizo|filet/i],
  ['🧀 Crèmerie & œufs', /lait(?! de coco)|crème|beurre|fromage|parmesan|emmental|gruyère|mozzarella|feta|chèvre|ricotta|yaourt|skyr|œuf|oeuf/i],
  ['🍝 Féculents & céréales', /riz|pâtes|spaghetti|penne|quinoa|semoule|farine|flocons|avoine|lentille|pois chiche|haricots? (rouges?|blancs?)|pain|tortilla|wrap|boulgour|nouilles|polenta|patate douce/i],
  ['🥫 Épicerie & condiments', /huile|vinaigre|sauce|moutarde|concentré|coulis|bouillon|cube|épice|sel\b|poivre|curry|paprika|cumin|curcuma|lait de coco|coco|miel|sucre|levure|chocolat|cacao|beurre de cacahuète|amande|noix|noisette|graine|whey|protéine|ketchup|soja|olive|câpre|conserve|boîte/i],
  ['🧊 Surgelés', /surgel/i],
  ['🥤 Boissons', /\beau\b|jus|café|thé|boisson|soda|vin|bière/i],
];
const aisleOf = (txt) => (AISLES.find(([, re]) => re.test(txt)) || ['🛒 Autres'])[0];

// « 600 g de poulet » → { q: 600, u: 'g', n: 'poulet' }
const UNIT = /^(\d+(?:[.,]\d+)?|\d+\/\d+)\s*(kg|g|mg|ml|cl|dl|l|c\.? ?à ?s\.?|c\.? ?à ?c\.?|cs|cc|càs|càc|cuillères? à (?:soupe|café)|pincées?|tranches?|boîtes?|sachets?|gousses?|pièces?|bottes?|brins?|pots?|briques?|verres?)?\.?\s+(?:de |d’|d')?(.+)$/i;
function parseIng(line) {
  const m = line.trim().replace(/^[-•]\s*/, '').match(UNIT);
  if (!m) return { n: line.trim().replace(/^[-•]\s*/, ''), q: null, u: '' };
  const q = m[1].includes('/') ? (+m[1].split('/')[0] / +m[1].split('/')[1]) : +m[1].replace(',', '.');
  return { q, u: (m[2] || '').toLowerCase(), n: m[3].trim() };
}
const fmtQ = (q, u) => { if (q == null) return ''; let v = q, uu = u; if (['g', 'ml', 'mg'].includes(u)) v = Math.ceil(v / 10) * 10; else if (['kg', 'l', 'cl', 'dl'].includes(u)) v = Math.ceil(v * 10) / 10; else v = Math.ceil(v * 2) / 2 >= 1 && !/c\.|cs|cc|càs|càc|cuill/.test(u) ? Math.ceil(v) : Math.ceil(v * 2) / 2; if (u === 'g' && v >= 1000) { v /= 1000; uu = 'kg'; } if (u === 'ml' && v >= 1000) { v /= 1000; uu = 'l'; } return `${(Math.round(v * 10) / 10).toLocaleString('fr-FR')}${uu ? ' ' + uu : ''}`; };

async function buildShopping() {
  const days = weekDays(weekOffset);
  const rr = Object.fromEntries((await recipes.all()).map(r => [r.id, r]));
  const rec = {}, items = {}, batch = [];
  for (const d of days) for (const [m] of MEALS) {
    const e = plannedFor(d, m); if (!e) continue;
    const pr = portionFor(e, d, m);
    if (e.type === 'recipe') (rec[e.recipeId || e.name] ||= { e, q: 0 }).q += pr.qty;
    if (e.type === 'product') { const k = 'p|' + e.name.toLowerCase(); (items[k] ||= { label: e.name + (e.brand ? ` (${e.brand})` : ''), q: 0, u: 'g', aisle: aisleOf(e.name) }).q += pr.grams; }
  }
  for (const { e, q } of Object.values(rec)) {
    const r = rr[e.recipeId];
    const factor = r?.portions ? q / r.portions : 1;
    batch.push({ name: e.name, q, factor, portions: r?.portions });
    for (const line of r?.ingredients || []) {
      const p = parseIng(line);
      const k = p.n.toLowerCase() + '|' + p.u;
      if (p.q == null) { items[k] ||= { label: p.n, q: null, u: '', aisle: aisleOf(p.n) }; continue; }
      (items[k] ||= { label: p.n, q: 0, u: p.u, aisle: aisleOf(p.n) }).q += p.q * factor;
    }
  }
  return { batch, items };
}

async function shopping() {
  const wk = weekDays(weekOffset)[0];
  const store = (await kv.get('shop')) || {};
  const st = store[wk] ||= { checked: [], extra: [] };
  const { batch, items } = await buildShopping();
  for (const x of st.extra) items['x|' + x] = { label: x, q: null, u: '', aisle: aisleOf(x), extra: true };
  const groups = {};
  for (const [k, it] of Object.entries(items)) (groups[it.aisle] ||= []).push([k, it]);
  const order = [...AISLES.map(a => a[0]), '🛒 Autres'].filter(a => groups[a]);
  const save = async () => { store[wk] = st; await kv.set('shop', store); };
  const w = sheet(`<h3>🧾 Courses de la semaine</h3>
    ${batch.length ? `<details class="batch"><summary>🍲 Batch cooking : ${batch.length} recette${batch.length > 1 ? 's' : ''} à préparer</summary>${batch.map(b => `<div class="hist-ex"><b>${esc(b.name)}</b><span>${num(b.q, 2)} portions → ${b.portions ? `cuisiner <b>${num(b.factor, 2)} ×</b> la recette (${b.portions} portions)` : 'à préparer'}</span></div>`).join('')}</details>` : ''}
    <div id="shopl">${order.length ? order.map(a => `<div class="aisle"><div class="eyebrow">${a}</div>${groups[a].map(([k, it]) => `<label class="shopi ${st.checked.includes(k) ? 'done' : ''}"><input type="checkbox" data-k="${esc(k)}" ${st.checked.includes(k) ? 'checked' : ''}><span>${it.q != null ? `<b>${fmtQ(it.q, it.u)}</b> ` : ''}${esc(it.label)}</span></label>`).join('')}</div>`).join('') : '<p class="muted">Planifie des repas dans le menu de la semaine pour générer ta liste.</p>'}</div>
    <div class="row gap"><input class="grow" id="shopadd" placeholder="Ajouter un article (ex : éponges)"><button class="btn" id="shopaddb">+</button></div>
    <div class="row gap"><button class="btn grow" id="shopshare">📤 Partager / Drive</button><button class="btn ghost grow" id="shopclear">Décocher tout</button></div>
    <p class="muted small">« Partager » envoie la liste triée par rayon vers Notes, Rappels, WhatsApp, Google Drive… ou le copie pour ta commande drive.</p>`);
  $('#shopl', w).addEventListener('change', async (e) => {
    const k = e.target.dataset.k; if (!k) return;
    st.checked = e.target.checked ? [...new Set([...st.checked, k])] : st.checked.filter(x => x !== k);
    e.target.closest('.shopi').classList.toggle('done', e.target.checked); await save();
  });
  const add = async () => { const v = $('#shopadd', w).value.trim(); if (!v) return; st.extra.push(v); await save(); w.close(); setTimeout(shopping, 260); };
  $('#shopaddb', w).onclick = add; $('#shopadd', w).onkeydown = (e) => { if (e.key === 'Enter') add(); };
  $('#shopclear', w).onclick = async () => { st.checked = []; await save(); w.close(); setTimeout(shopping, 260); };
  $('#shopshare', w).onclick = async () => {
    const txt = 'Courses FORGE — semaine du ' + fmtDate(wk, { day: 'numeric', month: 'long' }) + '\n' + order.map(a => '\n' + a.replace(/^\S+\s/, '').toUpperCase() + '\n' + groups[a].filter(([k]) => !st.checked.includes(k)).map(([, it]) => `☐ ${it.q != null ? fmtQ(it.q, it.u) + ' ' : ''}${it.label}`).join('\n')).join('\n');
    try { if (navigator.share) { await navigator.share({ title: 'Liste de courses', text: txt }); return; } } catch (e) { if (e.name === 'AbortError') return; }
    try { await navigator.clipboard.writeText(txt); toast('Liste copiée : colle-la où tu veux'); } catch (e) { toast('Copie impossible'); }
  };
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
