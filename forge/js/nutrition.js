// FORGE — nutrition : journal, cibles, recherche Open Food Facts, scanner code-barres, recettes Cookidoo, calculateur.
import { S, esc, $, $$, toast, sheet, confirmBox, today, num, targets, bmr, ACTIVITY, fmtDate, dayKey } from './ui.js';
import { food, recipes, kv, uid } from './db.js';
import { BASE_FOODS, MEALS } from './data.js';
import { allSessions } from './train.js';

let day = today(), ntab = 'journal';
const sum = (list) => list.reduce((a, e) => ({ kcal: a.kcal + (+e.kcal || 0), p: a.p + (+e.p || 0), c: a.c + (+e.c || 0), f: a.f + (+e.f || 0) }), { kcal: 0, p: 0, c: 0, f: 0 });
const shift = (d, n) => { const x = new Date(d + 'T12:00:00'); x.setDate(x.getDate() + n); return x.toISOString().slice(0, 10); };

export async function renderNutrition(view) {
  view.innerHTML = `<div class="seg">${[['journal', 'Journal'], ['recettes', 'Recettes'], ['calc', 'Calculateur']].map(([k, l]) => `<button class="${ntab === k ? 'on' : ''}" data-act="ntab" data-t="${k}">${l}</button>`).join('')}</div><div id="ntab"></div>`;
  const el = $('#ntab', view);
  if (ntab === 'journal') await journal(el);
  if (ntab === 'recettes') await recipeList(el);
  if (ntab === 'calc') calc(el);
}

async function journal(el) {
  const t = targets(S.profile);
  const entries = (await food.all()).filter(e => e.date === day);
  const tot = sum(entries);
  const burned = (await allSessions()).filter(s => dayKey(s.date) === day).reduce((a, s) => a + (s.kcal || 0), 0);
  const water = S.water[day] || 0;
  const pct = Math.min(1, tot.kcal / t.kcal);
  const R = 52, C = 2 * Math.PI * R;
  const bar = (label, v, goal, cls) => `<div class="macro ${cls}"><div class="row between"><span>${label}</span><small>${Math.round(v)} / ${goal} g</small></div><div class="pbar"><i style="width:${Math.min(100, v / goal * 100)}%"></i></div></div>`;
  el.innerHTML = `
  <div class="daynav"><button class="icon-btn" data-act="dprev" aria-label="Jour précédent">‹</button><b>${day === today() ? 'Aujourd’hui' : fmtDate(day, { weekday: 'long', day: 'numeric', month: 'long' })}</b><button class="icon-btn" data-act="dnext" aria-label="Jour suivant" ${day >= today() ? 'disabled' : ''}>›</button></div>
  <section class="card kcal-card">
    <svg viewBox="0 0 120 120" class="ring" role="img" aria-label="${Math.round(tot.kcal)} kcal sur ${t.kcal}"><circle cx="60" cy="60" r="${R}" class="ring-bg"/><circle cx="60" cy="60" r="${R}" class="ring-fg ${tot.kcal > t.kcal * 1.05 ? 'over' : ''}" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - pct)}" transform="rotate(-90 60 60)"/>
      <text x="60" y="56" text-anchor="middle" class="ring-n">${Math.round(Math.max(0, t.kcal - tot.kcal))}</text><text x="60" y="74" text-anchor="middle" class="ring-l">kcal restantes</text></svg>
    <div class="grow">
      <div class="kline"><span>Mangé</span><b>${Math.round(tot.kcal)}</b></div>
      <div class="kline"><span>Objectif</span><b>${t.kcal}</b></div>
      <div class="kline"><span>Brûlé au sport</span><b>${burned ? '~' + burned : '0'}</b></div>
      ${bar('Protéines', tot.p, t.p, 'p')}${bar('Glucides', tot.c, t.c, 'c')}${bar('Lipides', tot.f, t.f, 'f')}
    </div>
  </section>
  <section class="card water"><div class="row between"><b>💧 Eau</b><span>${(water * 0.25).toLocaleString('fr-FR')} L / ${Math.max(2, Math.round((+S.profile?.weight || 70) * 0.035 * 4) / 4).toLocaleString('fr-FR')} L</span></div>
    <div class="row gap"><button class="btn ghost sm" data-act="water" data-d="-1">−</button><div class="glasses">${Array.from({ length: Math.max(8, water) }, (_, i) => `<i class="${i < water ? 'on' : ''}"></i>`).join('')}</div><button class="btn sm" data-act="water" data-d="1">+ 25 cl</button></div></section>
  ${MEALS.map(([k, l]) => { const es = entries.filter(e => e.meal === k), s = sum(es); return `
    <section class="card meal"><div class="row between"><h3>${l}</h3><span class="muted">${Math.round(s.kcal)} kcal</span></div>
    ${es.map(e => `<button class="fitem" data-act="fedit" data-id="${e.id}"><div><b>${esc(e.name)}</b><small>${e.grams ? Math.round(e.grams) + ' g' : e.portions ? e.portions + ' portion(s)' : ''} · P ${num(e.p, 0)} · G ${num(e.c, 0)} · L ${num(e.f, 0)}</small></div><span>${Math.round(e.kcal)}</span></button>`).join('')}
    <button class="btn ghost sm block" data-act="fadd" data-meal="${k}">+ Ajouter</button></section>`; }).join('')}
  <button class="btn ghost block" data-act="copyday">⧉ Copier les repas d’hier</button>`;
}

// ————— Ajout d'aliment —————
function addSheet(meal, rerender) {
  const w = sheet(`<h3>Ajouter — ${MEALS.find(m => m[0] === meal)[1]}</h3>
    <div class="seg sm">${[['search', 'Rechercher'], ['scan', 'Scanner'], ['recipes', 'Recettes'], ['manual', 'Manuel']].map(([k, l], i) => `<button class="${i ? '' : 'on'}" data-t="${k}">${l}</button>`).join('')}</div>
    <div id="addbody"></div>`, { onClose: () => { stopScan(); rerender(); } });
  const body = $('#addbody', w);
  const tabs = {
    search: () => {
      body.innerHTML = `<input class="search" id="fq" placeholder="ex : skyr, poulet, Nutella…" autocomplete="off"><div id="fres" class="pick-list"></div>`;
      const show = async (q) => {
        const qq = q.toLowerCase();
        const recent = await recents();
        const local = [...recent, ...BASE_FOODS].filter(f => f.name.toLowerCase().includes(qq)).slice(0, 12);
        $('#fres', w).innerHTML = (q ? '' : '<div class="eyebrow">Récents & basiques</div>') + local.map((f, i) => foodRow(f, 'l' + i)).join('') + (q.length >= 3 ? '<div class="muted small" id="offst">Recherche en ligne (Open Food Facts)…</div>' : '');
        bindPick(local, 'l');
        if (q.length < 3) return;
        try {
          const res = await searchOFF(q);
          if ($('#fq', w)?.value !== q) return;
          $('#offst', w).outerHTML = `<div class="eyebrow">Open Food Facts</div>` + (res.map((f, i) => foodRow(f, 'o' + i)).join('') || '<p class="muted">Aucun produit trouvé.</p>');
          bindPick(res, 'o');
        } catch (e) { const s = $('#offst', w); if (s) s.textContent = 'Recherche en ligne indisponible (hors connexion ?)'; }
      };
      let to; $('#fq', w).oninput = (e) => { clearTimeout(to); to = setTimeout(() => show(e.target.value.trim()), 350); };
      show('');
      setTimeout(() => $('#fq', w)?.focus(), 50);
    },
    scan: () => {
      body.innerHTML = `<div class="scan"><video id="vid" playsinline muted></video><div class="scanline"></div></div><p class="muted small center" id="scanst">Vise le code-barres du produit…</p>
        <div class="row gap"><input class="search grow" id="bc" inputmode="numeric" placeholder="ou tape le code-barres"><button class="btn" id="bcgo">OK</button></div>`;
      const lookup = async (code) => {
        $('#scanst', w).textContent = 'Recherche du produit ' + code + '…';
        try { const f = await productOFF(code); stopScan(); quantity(f, meal, w); }
        catch (e) { $('#scanst', w).textContent = e.message; }
      };
      $('#bcgo', w).onclick = () => { const c = $('#bc', w).value.trim(); if (c) lookup(c); };
      startScan($('#vid', w), lookup).catch(e => { $('#scanst', w).textContent = 'Caméra indisponible : ' + e.message + '. Tape le code à la main.'; });
    },
    recipes: async () => {
      const rr = (await recipes.all()).sort((a, b) => a.name.localeCompare(b.name));
      body.innerHTML = rr.length ? `<div class="pick-list">${rr.map((r, i) => `<button class="pick" data-r="${i}"><b>${esc(r.name)}</b><small>${r.kcal} kcal · P ${r.protein} g / portion${r.source === 'cookidoo' ? ' · Cookidoo' : ''}</small></button>`).join('')}</div>` : '<p class="muted">Aucune recette. Ajoute tes recettes Cookidoo dans Nutrition → Recettes.</p>';
      body.onclick = (e) => { const b = e.target.closest('[data-r]'); if (!b) return; const r = rr[+b.dataset.r]; quantity({ name: r.name, recipe: true, kcal: r.kcal, p: r.protein, c: r.carbs, f: r.fat, src: 'recette' }, meal, w); };
    },
    manual: () => {
      body.innerHTML = `<label class="field">Nom<input id="mn" placeholder="ex : Sandwich maison"></label>
        <div class="grid4"><label class="mini">Kcal<input type="number" inputmode="decimal" id="mk"></label><label class="mini">Prot. g<input type="number" inputmode="decimal" id="mp"></label><label class="mini">Gluc. g<input type="number" inputmode="decimal" id="mc"></label><label class="mini">Lip. g<input type="number" inputmode="decimal" id="mf"></label></div>
        <p class="muted small">Astuce : si tu ne connais que les macros, laisse kcal vide → calcul auto (4/4/9).</p>
        <button class="btn block" id="madd">Ajouter</button>`;
      $('#madd', w).onclick = async () => {
        const p = +$('#mp', w).value || 0, c = +$('#mc', w).value || 0, f = +$('#mf', w).value || 0;
        const kcal = +$('#mk', w).value || Math.round(p * 4 + c * 4 + f * 9);
        await food.put({ id: uid('f'), date: day, meal, name: $('#mn', w).value || 'Aliment', kcal, p, c, f, src: 'manuel' });
        toast('Ajouté'); w.close();
      };
    },
  };
  const bindPick = (list, pre) => $$(`[data-pick^="${pre}"]`, w).forEach(b => { b.onclick = () => quantity(list[+b.dataset.pick.slice(1)], meal, w); });
  $('.seg', w).onclick = (e) => { const b = e.target.closest('[data-t]'); if (!b) return; stopScan(); $$('.seg button', w).forEach(x => x.classList.toggle('on', x === b)); tabs[b.dataset.t](); };
  tabs.search();
}

const foodRow = (f, k) => `<button class="pick" data-pick="${k}"><b>${esc(f.name)}${f.brand ? ` <small>${esc(f.brand)}</small>` : ''}</b><small>${Math.round(f.kcal)} kcal · P ${num(f.p)} · G ${num(f.c)} · L ${num(f.f)} ${f.recipe ? '/ portion' : '/ 100 g'}</small></button>`;

async function recents() {
  const all = (await food.all()).filter(e => e.per100).sort((a, b) => b.id.localeCompare(a.id));
  const seen = new Set(), out = [];
  for (const e of all) { if (seen.has(e.name)) continue; seen.add(e.name); out.push({ ...e.per100, name: e.name, lastGrams: e.grams }); if (out.length >= 15) break; }
  return out;
}

function quantity(f, meal, parent) {
  const isRecipe = !!f.recipe;
  const def = isRecipe ? 1 : (f.lastGrams || f.serving || 100);
  const w = sheet(`<h3>${esc(f.name)}</h3>${f.brand ? `<p class="muted">${esc(f.brand)}</p>` : ''}
    <label class="field">${isRecipe ? 'Portions' : 'Quantité (g)'}<input type="number" inputmode="decimal" id="qty" value="${def}" step="${isRecipe ? 0.5 : 5}"></label>
    ${!isRecipe ? `<div class="chips">${[30, 50, 100, 150, 200, 250].map(g => `<button class="chip" data-g="${g}">${g} g</button>`).join('')}${f.serving ? `<button class="chip" data-g="${f.serving}">1 portion (${f.serving} g)</button>` : ''}</div>` : ''}
    <div class="stats4" id="qprev"></div>
    <label class="field">Repas<select id="qmeal">${MEALS.map(([k, l]) => `<option value="${k}" ${k === meal ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <button class="btn block" id="qadd">Ajouter au journal</button>`);
  const k = () => (+$('#qty', w).value || 0) / (isRecipe ? 1 : 100);
  const prev = () => { const m = k(); $('#qprev', w).innerHTML = `<div class="stat"><b>${Math.round(f.kcal * m)}</b><small>kcal</small></div><div class="stat"><b>${num(f.p * m)}</b><small>prot.</small></div><div class="stat"><b>${num(f.c * m)}</b><small>gluc.</small></div><div class="stat"><b>${num(f.f * m)}</b><small>lip.</small></div>`; };
  $('#qty', w).oninput = prev; prev();
  w.addEventListener('click', (e) => { const g = e.target.closest('[data-g]'); if (g) { $('#qty', w).value = g.dataset.g; prev(); } });
  $('#qadd', w).onclick = async () => {
    const m = k(), q = +$('#qty', w).value;
    await food.put({ id: uid('f'), date: day, meal: $('#qmeal', w).value, name: f.name, grams: isRecipe ? null : q, portions: isRecipe ? q : null,
      kcal: Math.round(f.kcal * m), p: +(f.p * m).toFixed(1), c: +(f.c * m).toFixed(1), f: +(f.f * m).toFixed(1), src: f.src, per100: isRecipe ? null : { kcal: f.kcal, p: f.p, c: f.c, f: f.f, brand: f.brand || '', src: f.src } });
    toast(`${f.name} ajouté`); w.close(); parent?.close();
  };
}

// ————— Open Food Facts —————
const offMap = (p) => {
  const n = p.nutriments || {};
  const kcal = n['energy-kcal_100g'] ?? (n['energy_100g'] ? n['energy_100g'] / 4.184 : null);
  if (kcal == null) return null;
  return { name: p.product_name_fr || p.product_name || 'Produit', brand: (Array.isArray(p.brands) ? p.brands.join(', ') : (p.brands || '')).replace(/\b[a-z]{2}:/g, ''), kcal: +kcal, p: +(n.proteins_100g || 0), c: +(n.carbohydrates_100g || 0), f: +(n.fat_100g || 0), serving: parseFloat(p.serving_quantity) || null, code: p.code, src: 'off' };
};
async function searchOFF(q) {
  const fields = 'code,product_name,product_name_fr,brands,nutriments,serving_quantity';
  try {
    const r = await fetch(`https://search.openfoodfacts.org/search?q=${encodeURIComponent(q)}&page_size=60&langs=fr&fields=${fields}`);
    if (!r.ok) throw new Error();
    const j = await r.json();
    const out = (j.hits || []).map(offMap).filter(f => f && f.name).slice(0, 25);
    if (!out.length) throw new Error();
    return out;
  } catch (e) {
    const r = await fetch(`https://world.openfoodfacts.org/cgi/search.pl?search_terms=${encodeURIComponent(q)}&search_simple=1&action=process&json=1&page_size=20&fields=${fields}`);
    const j = await r.json();
    return (j.products || []).map(offMap).filter(Boolean);
  }
}
async function productOFF(code) {
  const r = await fetch(`https://world.openfoodfacts.org/api/v2/product/${encodeURIComponent(code)}.json?fields=code,product_name,product_name_fr,brands,nutriments,serving_quantity`);
  const j = await r.json();
  if (j.status !== 1 || !j.product) throw new Error('Produit inconnu d’Open Food Facts. Utilise l’onglet Manuel.');
  const f = offMap({ ...j.product, code });
  if (!f) throw new Error('Ce produit n’a pas de valeurs nutritionnelles. Utilise l’onglet Manuel.');
  return f;
}

// ————— Scanner code-barres —————
let scanStream = null, scanLoop = null, zxReader = null;
async function startScan(video, onCode) {
  scanStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
  video.srcObject = scanStream; await video.play();
  let done = false;
  const hit = (c) => { if (done) return; done = true; if (navigator.vibrate) navigator.vibrate(80); onCode(c); };
  if ('BarcodeDetector' in window) {
    const det = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
    const loop = async () => { if (!scanStream || done) return; try { const r = await det.detect(video); if (r[0]) return hit(r[0].rawValue); } catch (e) { } scanLoop = requestAnimationFrame(loop); };
    loop();
  } else {
    // iPhone / Safari : décodeur ZXing chargé à la demande
    if (!window.ZXing) await new Promise((res, rej) => { const s = document.createElement('script'); s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.21.3/umd/index.min.js'; s.onload = res; s.onerror = () => rej(new Error('décodeur non chargé')); document.head.appendChild(s); });
    const hints = new Map(); hints.set(window.ZXing.DecodeHintType.POSSIBLE_FORMATS, [window.ZXing.BarcodeFormat.EAN_13, window.ZXing.BarcodeFormat.EAN_8, window.ZXing.BarcodeFormat.UPC_A, window.ZXing.BarcodeFormat.UPC_E]);
    zxReader = new window.ZXing.BrowserMultiFormatReader(hints);
    zxReader.decodeFromStream(scanStream, video, (res) => { if (res) hit(res.getText()); });
  }
}
function stopScan() {
  cancelAnimationFrame(scanLoop);
  try { zxReader?.reset(); } catch (e) { } zxReader = null;
  scanStream?.getTracks().forEach(t => t.stop()); scanStream = null;
}

// ————— Recettes (Cookidoo & perso) —————
async function recipeList(el) {
  const rr = (await recipes.all()).sort((a, b) => (b.created || '').localeCompare(a.created || ''));
  el.innerHTML = `
  <section class="card cookidoo">
    <h3>🍲 Cookidoo / Thermomix</h3>
    <p class="small">Cookidoo n’ouvre pas son catalogue aux autres applis : il n’existe pas d’API officielle. FORGE fonctionne donc ainsi :</p>
    <ol class="small"><li><b>Enregistre tes recettes Cookidoo</b> avec les valeurs nutritionnelles affichées sur la fiche (par portion) et le lien.</li>
    <li><b>Demande à Claude</b> un menu de la semaine Thermomix calé sur tes macros (onglet Coach) : il s’ajoute ici automatiquement.</li>
    <li>Ajoute une portion au journal en un geste.</li></ol>
    <div class="row gap wrap"><button class="btn grow" data-act="radd">+ Nouvelle recette</button><a class="btn ghost grow" href="https://cookidoo.fr" target="_blank" rel="noopener">Ouvrir Cookidoo ↗</a></div>
  </section>
  ${rr.map(r => `<button class="card recipe" data-act="ropen" data-id="${r.id}"><div><b>${esc(r.name)}</b><small>${r.kcal} kcal · P ${r.protein} g · G ${r.carbs} g · L ${r.fat} g / portion · ${r.portions} portions</small></div><span class="tag">${r.source === 'cookidoo' ? 'Cookidoo' : r.source === 'claude' ? 'Claude' : 'Perso'}</span></button>`).join('') || '<p class="muted center">Aucune recette pour l’instant.</p>'}`;
}

export function recipeForm(r, rerender) {
  const e = r || { id: uid('r'), name: '', portions: 4, kcal: '', protein: '', carbs: '', fat: '', link: '', ingredients: [], steps: [], source: 'cookidoo', created: new Date().toISOString() };
  const w = sheet(`<h3>${r ? 'Recette' : 'Nouvelle recette'}</h3>
    <label class="field">Nom<input name="name" value="${esc(e.name)}"></label>
    <div class="grid3"><label class="mini">Portions<input type="number" name="portions" value="${e.portions}"></label>
    <label class="mini">Source<select name="source">${[['cookidoo', 'Cookidoo'], ['claude', 'Claude'], ['perso', 'Perso']].map(([k, l]) => `<option value="${k}" ${k === e.source ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <label class="mini">Kcal / portion<input type="number" inputmode="decimal" name="kcal" value="${e.kcal}"></label>
    <label class="mini">Prot. g<input type="number" inputmode="decimal" name="protein" value="${e.protein}"></label>
    <label class="mini">Gluc. g<input type="number" inputmode="decimal" name="carbs" value="${e.carbs}"></label>
    <label class="mini">Lip. g<input type="number" inputmode="decimal" name="fat" value="${e.fat}"></label></div>
    <label class="field">Lien Cookidoo<input name="link" type="url" placeholder="https://cookidoo.fr/recipes/recipe/fr-FR/r…" value="${esc(e.link || '')}"></label>
    <label class="field">Ingrédients (un par ligne)<textarea name="ingredients" rows="4">${esc((e.ingredients || []).join('\n'))}</textarea></label>
    <label class="field">Étapes (une par ligne)<textarea name="steps" rows="4">${esc((e.steps || []).join('\n'))}</textarea></label>
    ${e.link ? `<a class="btn ghost block" href="${esc(e.link)}" target="_blank" rel="noopener">Ouvrir dans Cookidoo ↗</a>` : ''}
    <div class="row gap">${r ? '<button class="btn ghost danger grow" id="rdel">Supprimer</button>' : ''}<button class="btn grow" id="rsave">Enregistrer</button></div>
    ${r ? '<button class="btn ghost block" id="rlog">+ Ajouter une portion au journal du jour</button>' : ''}`, { onClose: rerender });
  const read = () => { const o = { ...e }; $$('[name]', w).forEach(i => { const v = i.value; o[i.name] = ['ingredients', 'steps'].includes(i.name) ? v.split('\n').map(s => s.trim()).filter(Boolean) : i.type === 'number' ? +v : v; }); return o; };
  $('#rsave', w).onclick = async () => { const o = read(); if (!o.name) return toast('Donne un nom à la recette'); if (o.link && !/^https:\/\//.test(o.link)) o.link = ''; await recipes.put(o); toast('Recette enregistrée'); w.close(); };
  if (r) {
    $('#rdel', w).onclick = async () => { if (await confirmBox('Supprimer cette recette ?', 'Supprimer')) { await recipes.del(e.id); w.close(); } };
    $('#rlog', w).onclick = () => { const o = read(); quantity({ name: o.name, recipe: true, kcal: o.kcal, p: o.protein, c: o.carbs, f: o.fat, src: 'recette' }, guessMeal(), w); };
  }
}
const guessMeal = () => { const h = new Date().getHours(); return h < 11 ? 'matin' : h < 15 ? 'midi' : h < 18 ? 'collation' : 'soir'; };

// ————— Calculateur —————
function calc(el) {
  const p = S.profile || {};
  el.innerHTML = `
  <section class="card"><h3>Dépense & besoins</h3>
    <div class="grid3">
      <label class="mini">Sexe<select id="cs"><option value="h" ${p.sex !== 'f' ? 'selected' : ''}>Homme</option><option value="f" ${p.sex === 'f' ? 'selected' : ''}>Femme</option></select></label>
      <label class="mini">Âge<input type="number" id="ca" value="${p.age || 30}"></label>
      <label class="mini">Taille cm<input type="number" id="ch" value="${p.height || 175}"></label>
      <label class="mini">Poids kg<input type="number" id="cw" step="0.1" value="${p.weight || 75}"></label>
      <label class="mini">% MG (opt.)<input type="number" id="cb" step="0.1" value="${p.bodyfat || ''}"></label>
      <label class="mini">Objectif<select id="cg">${[['seche', 'Sèche'], ['recompo', 'Recomposition'], ['maintien', 'Maintien'], ['prise', 'Prise de muscle']].map(([k, l]) => `<option value="${k}" ${k === (p.goal || 'recompo') ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    </div>
    <label class="field">Activité<select id="cact">${Object.entries(ACTIVITY).map(([k, l]) => `<option value="${k}" ${+k === +(p.activity || 1.45) ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <div id="cres"></div>
  </section>
  <section class="card"><h3>Calories d’une portion</h3>
    <p class="muted small">Valeurs pour 100 g (étiquette) → ta portion.</p>
    <div class="grid4"><label class="mini">Kcal/100 g<input type="number" id="pk" value="250"></label><label class="mini">Prot./100 g<input type="number" id="pp" value="10"></label><label class="mini">Gluc./100 g<input type="number" id="pc" value="30"></label><label class="mini">Lip./100 g<input type="number" id="pf" value="10"></label></div>
    <label class="field">Portion (g)<input type="number" id="pg" value="150"></label>
    <div class="stats4" id="pres"></div>
  </section>`;
  const run = () => {
    const pr = { sex: $('#cs').value, age: +$('#ca').value, height: +$('#ch').value, weight: +$('#cw').value, bodyfat: +$('#cb').value || null, goal: $('#cg').value, activity: +$('#cact').value };
    const t = targets(pr);
    $('#cres').innerHTML = `<div class="stats4"><div class="stat"><b>${Math.round(bmr(pr))}</b><small>métabolisme de base</small></div><div class="stat"><b>${t.tdee}</b><small>dépense / jour</small></div><div class="stat hl"><b>${t.kcal}</b><small>cible kcal</small></div><div class="stat"><b>${t.p} g</b><small>protéines</small></div></div>
      <p class="small muted">${pr.bodyfat ? 'Formule Katch-McArdle (masse maigre).' : 'Formule Mifflin-St Jeor.'} Glucides ${t.c} g · lipides ${t.f} g. Ajuste de ±100 kcal si ton poids ne bouge pas comme prévu après 2 semaines.</p>`;
    const g = (+$('#pg').value || 0) / 100;
    $('#pres').innerHTML = `<div class="stat hl"><b>${Math.round(+$('#pk').value * g)}</b><small>kcal</small></div><div class="stat"><b>${num(+$('#pp').value * g)}</b><small>prot.</small></div><div class="stat"><b>${num(+$('#pc').value * g)}</b><small>gluc.</small></div><div class="stat"><b>${num(+$('#pf').value * g)}</b><small>lip.</small></div>`;
  };
  el.addEventListener('input', run); el.addEventListener('change', run); run();
}

// ————— Actions —————
export async function onNutritionAction(act, el, rerender) {
  if (act === 'ntab') { ntab = el.dataset.t; return rerender(); }
  if (act === 'dprev') { day = shift(day, -1); return rerender(); }
  if (act === 'dnext') { day = shift(day, 1); return rerender(); }
  if (act === 'fadd') return addSheet(el.dataset.meal, rerender);
  if (act === 'water') { S.water[day] = Math.max(0, (S.water[day] || 0) + +el.dataset.d); await kv.set('water', S.water); return rerender(); }
  if (act === 'radd') return recipeForm(null, rerender);
  if (act === 'ropen') return recipeForm(await recipes.get(el.dataset.id), rerender);
  if (act === 'copyday') {
    const y = shift(day, -1);
    const prev = (await food.all()).filter(e => e.date === y);
    if (!prev.length) return toast('Rien à copier pour la veille');
    for (const e of prev) await food.put({ ...e, id: uid('f'), date: day });
    toast(`${prev.length} aliment(s) copiés`); return rerender();
  }
  if (act === 'fedit') {
    const e = await food.get(el.dataset.id);
    const w = sheet(`<h3>${esc(e.name)}</h3><p class="muted">${Math.round(e.kcal)} kcal · P ${num(e.p)} · G ${num(e.c)} · L ${num(e.f)}</p>
      ${e.per100 ? `<label class="field">Quantité (g)<input type="number" id="eg" value="${e.grams}"></label>` : ''}
      <div class="row gap"><button class="btn ghost danger grow" id="edel">Supprimer</button>${e.per100 ? '<button class="btn grow" id="esave">Enregistrer</button>' : ''}</div>`, { onClose: rerender });
    $('#edel', w).onclick = async () => { await food.del(e.id); w.close(); };
    if (e.per100) $('#esave', w).onclick = async () => { const g = +$('#eg', w).value || 0, m = g / 100, b = e.per100; Object.assign(e, { grams: g, kcal: Math.round(b.kcal * m), p: +(b.p * m).toFixed(1), c: +(b.c * m).toFixed(1), f: +(b.f * m).toFixed(1) }); await food.put(e); w.close(); };
  }
}

// Utilisé par le coach (photo de repas → journal)
export async function addFoodItems(items, meal = guessMeal(), date = today()) {
  for (const it of items) await food.put({ id: uid('f'), date, meal, name: it.name, grams: it.grams || null, kcal: Math.round(it.kcal), p: +it.protein || 0, c: +it.carbs || 0, f: +it.fat || 0, src: 'claude' });
}
export { guessMeal };
