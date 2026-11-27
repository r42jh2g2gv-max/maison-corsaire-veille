// FORGE — nutrition : journal, objectifs (perte / sèche / prise), photo de repas, Open Food Facts, scanner,
// menu de la semaine, recettes Cookidoo / Thermomix, calculateur.
import { S, esc, $, $$, toast, sheet, confirmBox, today, num, targets, bmr, ACTIVITY, fmtDate, dayKey, GOALS, goalOf, adaptiveAdvice, contextText } from './ui.js';
import { food, recipes, body, kv, uid } from './db.js';
import { BASE_FOODS, MEALS } from './data.js';
import { allSessions } from './train.js';
import { structured, FOOD_SCHEMA, RECIPES_SCHEMA, FORMAT_HINT, extractJSON, fileToBase64 } from './claude.js';
import { renderPlan, onPlanAction, plannedFor, plannedLabel, toggleEaten } from './plan.js';
import { healthCard } from './health.js';
import { ecartSheet, compensation } from './ecart.js';
import { fetchT, isNetErr, pendingFood, registerHandler } from './offline.js';

let day = today(), ntab = 'journal';
const sum = (list) => list.reduce((a, e) => ({ kcal: a.kcal + (+e.kcal || 0), p: a.p + (+e.p || 0), c: a.c + (+e.c || 0), f: a.f + (+e.f || 0) }), { kcal: 0, p: 0, c: 0, f: 0 });
const shift = (d, n) => { const x = new Date(d + 'T12:00:00'); x.setDate(x.getDate() + n); return x.toISOString().slice(0, 10); };
export const guessMeal = () => { const h = new Date().getHours(); return h < 11 ? 'matin' : h < 15 ? 'midi' : h < 18 ? 'collation' : 'soir'; };

export async function renderNutrition(view) {
  view.innerHTML = `<div class="seg">${[['journal', 'Journal'], ['semaine', 'Menu semaine'], ['recettes', 'Recettes'], ['calc', 'Calculs']].map(([k, l]) => `<button class="${ntab === k ? 'on' : ''}" data-act="ntab" data-t="${k}">${l}</button>`).join('')}</div><div id="ntab"></div>`;
  const el = $('#ntab', view);
  if (ntab === 'journal') await journal(el);
  if (ntab === 'semaine') await renderPlan(el);
  if (ntab === 'recettes') await recipeList(el);
  if (ntab === 'calc') calc(el);
}

// ————— Journal —————
async function journal(el) {
  const p = S.profile;
  const t = targets(p, day);
  const g = goalOf(p);
  const entries = (await food.all()).filter(e => e.date === day);
  const tot = sum(entries);
  const burned = (await allSessions()).filter(s => dayKey(s.date) === day).reduce((a, s) => a + (s.kcal || 0), 0);
  const water = S.water[day] || 0;
  const pct = Math.min(1, tot.kcal / t.kcal);
  const R = 52, C = 2 * Math.PI * R;
  const bar = (label, v, goal, cls) => `<div class="macro ${cls}"><div class="row between"><span>${label}</span><small>${Math.round(v)} / ${goal} g</small></div><div class="pbar"><i style="width:${Math.min(100, v / goal * 100)}%"></i></div></div>`;
  const adv = p ? adaptiveAdvice(p, (await body.all()).sort((a, b) => a.date.localeCompare(b.date))) : null;
  el.innerHTML = `
  <div class="daynav"><button class="icon-btn" data-act="dprev" aria-label="Jour précédent">‹</button><b>${day === today() ? 'Aujourd’hui' : fmtDate(day, { weekday: 'long', day: 'numeric', month: 'long' })}</b><button class="icon-btn" data-act="dnext" aria-label="Jour suivant">›</button></div>
  <section class="card goalcard">
    <div class="chips">${Object.entries(GOALS).map(([k, v]) => `<button class="chip ${k === (p?.goal || 'recompo') ? 'on' : ''}" data-act="goal" data-g="${k}">${v.short}</button>`).join('')}</div>
    <p class="small muted">${g.desc}</p>
    ${t.dayType ? `<p class="small"><b>${t.dayType === 'entrainement' ? '🏋️ Jour d’entraînement' : '🛋 Jour de repos'}</b> : ${t.dayType === 'entrainement' ? 'plus de glucides pour la performance' : 'un peu moins de glucides'} (moyenne semaine : ${t.base} kcal).</p>` : ''}
    ${t.watch ? '<p class="small"><b>⌚ Calé sur ta dépense réelle</b> mesurée par l’Apple Watch.</p>' : ''}
  </section>
  <section class="card kcal-card">
    <svg viewBox="0 0 120 120" class="ring" role="img" aria-label="${Math.round(tot.kcal)} kcal sur ${t.kcal}"><circle cx="60" cy="60" r="${R}" class="ring-bg"/><circle cx="60" cy="60" r="${R}" class="ring-fg ${tot.kcal > t.kcal * 1.05 ? 'over' : ''}" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - pct)}" transform="rotate(-90 60 60)"/>
      <text x="60" y="56" text-anchor="middle" class="ring-n">${Math.round(Math.max(0, t.kcal - tot.kcal))}</text><text x="60" y="74" text-anchor="middle" class="ring-l">kcal restantes</text></svg>
    <div class="grow">
      <div class="kline"><span>Mangé</span><b>${Math.round(tot.kcal)}</b></div>
      <div class="kline"><span>Objectif</span><b>${t.kcal}</b></div>
      <div class="kline"><span>Sport${S.health[day]?.active ? ' · montre' : ''}</span><b>${S.health[day]?.active ? S.health[day].active : burned ? '~' + burned : '0'}</b></div>
      ${bar('Protéines', tot.p, t.p, 'p')}${bar('Glucides', tot.c, t.c, 'c')}${bar('Lipides', tot.f, t.f, 'f')}
    </div>
  </section>
  ${adv?.ready && adv.adjust ? `<section class="card adapt"><b>📉 Ajustement conseillé : ${adv.adjust > 0 ? '+' : ''}${adv.adjust} kcal/jour</b>
    <p class="small">Ton poids évolue de <b>${adv.slope > 0 ? '+' : ''}${num(adv.slope, 2)} kg/sem</b> ; pour ton objectif « ${g.short} », on vise <b>${adv.expected > 0 ? '+' : ''}${num(adv.expected, 2)} kg/sem</b>.</p>
    <button class="btn sm" data-act="adapt" data-v="${adv.adjust}">Appliquer</button></section>` : ''}
  ${adv && !adv.ready ? `<p class="muted small">Pèse-toi 2 à 3 fois par semaine : après 10 jours, FORGE ajuste tes calories selon l’évolution réelle de ton poids.</p>` : ''}
  ${p?.kcalAdjust ? `<p class="muted small">Ajustement actif : ${p.kcalAdjust > 0 ? '+' : ''}${p.kcalAdjust} kcal/jour · <a href="#" data-act="adapt-reset">remettre à zéro</a></p>` : ''}
  ${t.comp ? `<p class="small">↘︎ Rattrapage d’un écart : <b>−${t.comp} kcal</b> aujourd’hui · <a href="#" data-act="comp-cancel">annuler</a></p>` : ''}
  <div class="row gap"><button class="btn grow photo-cta" data-act="fphoto">📷 Photo → calories</button><button class="btn ghost grow" data-act="ecart">🍻 Écart / soirée</button></div>
  ${tot.kcal > t.kcal + 150 ? `<button class="btn ghost sm block" data-act="comp-check">Tu dépasses de ${Math.round(tot.kcal - t.kcal)} kcal : comment rattraper ?</button>` : ''}
  <section class="card water"><div class="row between"><b>💧 Eau</b><span>${(water * 0.25).toLocaleString('fr-FR')} L / ${Math.max(2, Math.round((+p?.weight || 70) * 0.035 * 4) / 4).toLocaleString('fr-FR')} L</span></div>
    <div class="row gap"><button class="btn ghost sm" data-act="water" data-d="-1">−</button><div class="glasses">${Array.from({ length: Math.max(8, water) }, (_, i) => `<i class="${i < water ? 'on' : ''}"></i>`).join('')}</div><button class="btn sm" data-act="water" data-d="1">+ 25 cl</button></div></section>
  ${MEALS.map(([k, l]) => { const es = entries.filter(e => e.meal === k), s = sum(es); const pl = plannedFor(day, k); return `
    <section class="card meal"><div class="row between"><h3>${l}</h3><span class="muted">${Math.round(s.kcal)} kcal</span></div>
    ${pl && !pl.done ? `<div class="planned"><div><small>Prévu au menu</small><b>${esc(pl.name)}</b><small>${plannedLabel(pl, day, k)}</small></div><button class="btn sm" data-act="eat" data-meal="${k}">✓ Mangé</button></div>` : ''}
    ${es.map(e => `<button class="fitem" data-act="fedit" data-id="${e.id}"><div><b>${esc(e.name)}</b><small>${e.grams ? Math.round(e.grams) + ' g' : e.portions ? num(e.portions, 2) + ' portion(s)' : ''} · P ${num(e.p, 0)} · G ${num(e.c, 0)} · L ${num(e.f, 0)}</small></div><span>${e.pending ? '⏳' : Math.round(e.kcal)}</span></button>`).join('')}
    <button class="btn ghost sm block" data-act="fadd" data-meal="${k}">+ Ajouter</button></section>`; }).join('')}
  ${healthCard(day)}
  <button class="btn ghost block" data-act="copyday">⧉ Copier les repas de la veille</button>`;
}

// ————— Sélecteur d'aliment générique —————
// onPick(f) : f = aliment pour 100 g, ou { recipe: true, ... } (valeurs par portion)
export function foodPicker({ title, onPick, onClose, offlineMeal = null, tabs: only = ['search', 'scan', 'recipes', 'manual'] }) {
  const LBL = { search: 'Rechercher', scan: 'Scanner', recipes: 'Recettes', manual: 'Manuel' };
  const w = sheet(`<h3>${esc(title)}</h3>
    <div class="seg sm">${only.map((k, i) => `<button class="${i ? '' : 'on'}" data-t="${k}">${LBL[k]}</button>`).join('')}</div>
    <div id="addbody"></div>`, { onClose: () => { stopScan(); onClose && onClose(); } });
  const bodyEl = $('#addbody', w);
  const pick = (f) => onPick(f, w);
  const tabs = {
    search: () => {
      bodyEl.innerHTML = `<input class="search" id="fq" placeholder="ex : skyr, poulet, lasagnes Picard…" autocomplete="off"><div id="fres" class="pick-list"></div>`;
      const show = async (q) => {
        const qq = q.toLowerCase();
        const local = [...await recents(), ...BASE_FOODS].filter(f => f.name.toLowerCase().includes(qq)).slice(0, 12);
        $('#fres', w).innerHTML = (q ? '' : '<div class="eyebrow">Récents & basiques</div>') + local.map((f, i) => foodRow(f, 'l' + i)).join('') + (q.length >= 3 ? '<div class="muted small" id="offst">Recherche en ligne (Open Food Facts)…</div>' : '');
        bindPick(local, 'l');
        if (q.length < 3) return;
        try {
          const res = await searchOFF(q);
          if ($('#fq', w)?.value.trim() !== q) return;
          $('#offst', w).outerHTML = `<div class="eyebrow">Open Food Facts</div>` + (res.map((f, i) => foodRow(f, 'o' + i)).join('') || '<p class="muted">Aucun produit trouvé.</p>');
          bindPick(res, 'o');
        } catch (e) { const s = $('#offst', w); if (s) s.textContent = 'Recherche en ligne indisponible (hors connexion ?)'; }
      };
      let to; $('#fq', w).oninput = (e) => { clearTimeout(to); to = setTimeout(() => show(e.target.value.trim()), 350); };
      show('');
    },
    scan: () => {
      bodyEl.innerHTML = `<div class="scan"><video id="vid" playsinline muted></video><div class="scanline"></div></div><p class="muted small center" id="scanst">Vise le code-barres du produit…</p>
        <div class="row gap"><input class="search grow" id="bc" inputmode="numeric" placeholder="ou tape le code-barres"><button class="btn" id="bcgo">OK</button></div>`;
      const lookup = async (code) => {
        $('#scanst', w).textContent = 'Recherche du produit ' + code + '…';
        try { const f = await productOFF(code); stopScan(); pick(f); }
        catch (e) {
          if (isNetErr(e) && offlineMeal) {
            stopScan();
            $('#scanst', w).innerHTML = `Pas de réseau. Quantité mangée (g) ? <input id="offg" type="number" inputmode="decimal" value="100" class="search"><button class="btn block" id="offok">Mettre en attente</button>`;
            $('#offok', w).onclick = async () => { await pendingFood({ date: day, meal: offlineMeal, name: `Produit ${code} (en attente)`, grams: +$('#offg', w).value || 100, task: { type: 'barcode', code } }); w.close(); };
          } else $('#scanst', w).textContent = isNetErr(e) ? 'Pas de réseau pour chercher ce produit.' : e.message;
        }
      };
      $('#bcgo', w).onclick = () => { const c = $('#bc', w).value.trim(); if (c) lookup(c); };
      startScan($('#vid', w), lookup).catch(e => { $('#scanst', w).textContent = 'Caméra indisponible : ' + e.message + '. Tape le code à la main.'; });
    },
    recipes: async () => {
      const rr = (await recipes.all()).sort((a, b) => a.name.localeCompare(b.name));
      bodyEl.innerHTML = rr.length ? `<div class="pick-list">${rr.map((r, i) => `<button class="pick" data-r="${i}"><b>${esc(r.name)}</b><small>${r.kcal} kcal · P ${r.protein} g / portion${r.source === 'cookidoo' ? ' · Cookidoo' : ''}</small></button>`).join('')}</div>` : '<p class="muted">Aucune recette. Ajoute-les dans Nutrition → Recettes.</p>';
      bodyEl.onclick = (e) => { const b = e.target.closest('[data-r]'); if (!b) return; pick(recipeFood(rr[+b.dataset.r])); };
    },
    manual: () => {
      bodyEl.innerHTML = `<label class="field">Nom<input id="mn" placeholder="ex : Restaurant, sandwich maison…"></label>
        <div class="grid4"><label class="mini">Kcal<input type="number" inputmode="decimal" id="mk"></label><label class="mini">Prot. g<input type="number" inputmode="decimal" id="mp"></label><label class="mini">Gluc. g<input type="number" inputmode="decimal" id="mc"></label><label class="mini">Lip. g<input type="number" inputmode="decimal" id="mf"></label></div>
        <p class="muted small">Valeurs pour 1 portion. Kcal vide → calcul auto depuis les macros (4/4/9).</p>
        <button class="btn block" id="madd">Valider</button>`;
      $('#madd', w).onclick = () => {
        const p = +$('#mp', w).value || 0, c = +$('#mc', w).value || 0, f = +$('#mf', w).value || 0;
        const kcal = +$('#mk', w).value || Math.round(p * 4 + c * 4 + f * 9);
        pick({ name: $('#mn', w).value || 'Repas', recipe: true, free: true, kcal, p, c, f, src: 'manuel' });
      };
    },
  };
  const bindPick = (list, pre) => $$(`[data-pick^="${pre}"]`, w).forEach(b => { b.onclick = () => pick(list[+b.dataset.pick.slice(1)]); });
  $('.seg', w).onclick = (e) => { const b = e.target.closest('[data-t]'); if (!b) return; stopScan(); $$('.seg button', w).forEach(x => x.classList.toggle('on', x === b)); tabs[b.dataset.t](); };
  tabs[only[0]]();
  return w;
}
export const recipeFood = (r) => ({ name: r.name, recipe: true, recipeId: r.id, kcal: +r.kcal || 0, p: +r.protein || 0, c: +r.carbs || 0, f: +r.fat || 0, gpp: r.totalWeight && r.portions ? r.totalWeight / r.portions : null, src: 'recette' });

const foodRow = (f, k) => `<button class="pick" data-pick="${k}"><b>${esc(f.name)}${f.brand ? ` <small>${esc(f.brand)}</small>` : ''}</b><small>${Math.round(f.kcal)} kcal · P ${num(f.p)} · G ${num(f.c)} · L ${num(f.f)} ${f.recipe ? '/ portion' : '/ 100 g'}</small></button>`;

async function recents() {
  const all = (await food.all()).filter(e => e.per100).sort((a, b) => b.id.localeCompare(a.id));
  const seen = new Set(), out = [];
  for (const e of all) { if (seen.has(e.name)) continue; seen.add(e.name); out.push({ ...e.per100, name: e.name, lastGrams: e.grams }); if (out.length >= 15) break; }
  return out;
}

function addSheet(meal, rerender) {
  foodPicker({ title: 'Ajouter — ' + MEALS.find(m => m[0] === meal)[1], onPick: (f, w) => quantity(f, meal, w), onClose: rerender, offlineMeal: meal });
}

function quantity(f, meal, parent, date = day) {
  const isRecipe = !!f.recipe;
  const def = isRecipe ? 1 : (f.lastGrams || f.serving || 100);
  const w = sheet(`<h3>${esc(f.name)}</h3>${f.brand ? `<p class="muted">${esc(f.brand)}</p>` : ''}
    <label class="field">${isRecipe ? 'Portions' : 'Quantité (g)'}<input type="number" inputmode="decimal" id="qty" value="${def}" step="${isRecipe ? 0.25 : 5}"></label>
    ${!isRecipe ? `<div class="chips">${[30, 50, 100, 150, 200, 250].map(g => `<button class="chip" data-g="${g}">${g} g</button>`).join('')}${f.serving ? `<button class="chip" data-g="${f.serving}">1 portion (${f.serving} g)</button>` : ''}</div>` : `<div class="chips">${[0.5, 0.75, 1, 1.25, 1.5, 2].map(g => `<button class="chip" data-g="${g}">${String(g).replace('.', ',')}</button>`).join('')}</div>`}
    <div class="stats4" id="qprev"></div>
    <label class="field">Repas<select id="qmeal">${MEALS.map(([k, l]) => `<option value="${k}" ${k === meal ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <button class="btn block" id="qadd">Ajouter au journal</button>`);
  const k = () => (+$('#qty', w).value || 0) / (isRecipe ? 1 : 100);
  const prev = () => { const m = k(); $('#qprev', w).innerHTML = `<div class="stat"><b>${Math.round(f.kcal * m)}</b><small>kcal${isRecipe && f.gpp ? ' · ' + Math.round(f.gpp * (+$('#qty', w).value || 0)) + ' g' : ''}</small></div><div class="stat"><b>${num(f.p * m)}</b><small>prot.</small></div><div class="stat"><b>${num(f.c * m)}</b><small>gluc.</small></div><div class="stat"><b>${num(f.f * m)}</b><small>lip.</small></div>`; };
  $('#qty', w).oninput = prev; prev();
  w.addEventListener('click', (e) => { const g = e.target.closest('[data-g]'); if (g) { $('#qty', w).value = g.dataset.g; prev(); } });
  $('#qadd', w).onclick = async () => {
    const m = k(), q = +$('#qty', w).value;
    await food.put({ id: uid('f'), date, meal: $('#qmeal', w).value, name: f.name, grams: isRecipe ? (f.gpp ? Math.round(f.gpp * q) : null) : q, portions: isRecipe ? q : null,
      kcal: Math.round(f.kcal * m), p: +(f.p * m).toFixed(1), c: +(f.c * m).toFixed(1), f: +(f.f * m).toFixed(1), src: f.src, per100: isRecipe ? null : { kcal: f.kcal, p: f.p, c: f.c, f: f.f, brand: f.brand || '', src: f.src } });
    toast(`${f.name} ajouté`); w.close(); parent?.close();
  };
}

// ————— Photo de repas → calories —————
const PHOTO_PROMPT = 'Estime les calories et macros du repas sur la photo jointe : identifie chaque aliment, estime le poids de chaque portion visible (taille de l’assiette, couverts et contenants comme repères), en restant réaliste.';

function photoSheet(meal, rerender) {
  const hasKey = !!S.settings.apiKey;
  let img = null, file = null;
  const w = sheet(`<h3>📷 Calories par photo</h3>
    <label class="btn block">Prendre la photo<input type="file" accept="image/*" capture="environment" id="pf" hidden></label>
    <label class="btn ghost block">Choisir dans la galerie<input type="file" accept="image/*" id="pg" hidden></label>
    <img id="pprev" class="full" hidden alt="Photo du repas">
    <label class="field">Précisions (optionnel)<input id="pdesc" placeholder="ex : assiette de 26 cm, fait maison, sauce à part…"></label>
    ${hasKey ? `<button class="btn block" id="pgo" disabled>Analyser avec Claude</button>` : `
      <p class="small muted">Sans clé API, la photo part dans ton app Claude (abonnement) avec la consigne ; recolle ensuite sa réponse ici.</p>
      <button class="btn block" id="pshare" disabled>Envoyer à Claude</button>
      <textarea id="ppaste" rows="3" placeholder="Colle ici la réponse de Claude…"></textarea>
      <button class="btn ghost block" id="pimp">Importer la réponse</button>`}`, { onClose: rerender });
  const onFile = async (e) => {
    file = e.target.files[0]; if (!file) return;
    img = await fileToBase64(file);
    const pv = $('#pprev', w); pv.src = 'data:' + img.type + ';base64,' + img.data; pv.hidden = false;
    const b = $('#pgo', w) || $('#pshare', w); b.disabled = false;
  };
  $('#pf', w).onchange = onFile; $('#pg', w).onchange = onFile;
  const prompt = () => PHOTO_PROMPT + ($('#pdesc', w).value ? ' Précisions : ' + $('#pdesc', w).value : '');
  if (hasKey) $('#pgo', w).onclick = async () => {
    const b = $('#pgo', w); b.disabled = true; b.textContent = 'Claude analyse ton assiette…';
    try {
      const data = await structured(prompt(), FOOD_SCHEMA, await contextText({ days: 3 }), { images: [img], effort: 'medium' });
      w.close(); foodReview(data.items, data.comment, meal, rerender);
    } catch (e) {
      if (isNetErr(e)) { await pendingFood({ date: day, meal, name: 'Repas en photo (en attente)', task: { type: 'photo', img, desc: $('#pdesc', w).value } }); w.close(); return; }
      toast('⚠️ ' + (e.status === 401 ? 'Clé API invalide' : e.message), 5000); b.disabled = false; b.textContent = 'Analyser avec Claude';
    }
  };
  else {
    $('#pshare', w).onclick = async () => {
      const text = prompt() + '\n\n' + FORMAT_HINT.food;
      const jpg = new File([Uint8Array.from(atob(img.data), c => c.charCodeAt(0))], 'repas.jpg', { type: 'image/jpeg' });
      try {
        if (navigator.canShare?.({ files: [jpg] })) { await navigator.clipboard.writeText(text).catch(() => { }); await navigator.share({ files: [jpg], text }); return; }
      } catch (e) { if (e.name === 'AbortError') return; }
      await navigator.clipboard.writeText(text).catch(() => { });
      toast('Consigne copiée : dans Claude, joins la photo et colle le texte', 5000);
      setTimeout(() => window.open('https://claude.ai/new', '_blank', 'noopener'), 600);
    };
    $('#pimp', w).onclick = () => {
      try { const d = extractJSON($('#ppaste', w).value); w.close(); foodReview(d.items, d.comment, meal, rerender); }
      catch (e) { toast('Réponse illisible : vérifie qu’elle contient le bloc JSON'); }
    };
  }
}

// Revue modifiable d'une estimation (photo, Claude) avant ajout au journal
export function foodReview(items, comment, meal = guessMeal(), rerender, date = day) {
  const base = items.map(i => ({ ...i, g0: +i.grams || 0 }));
  const w = sheet(`<h3>Repas estimé</h3>
    <div id="rv"></div>
    ${comment ? `<p class="small muted">${esc(comment)}</p>` : ''}
    <p class="small muted">Corrige les grammes si besoin : les calories suivent.</p>
    <label class="field">Repas<select id="fm">${MEALS.map(([k, l]) => `<option value="${k}" ${k === meal ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <button class="btn block" id="fadd">Ajouter au journal</button>`, { onClose: rerender });
  const scaled = (i) => { const k = i.g0 ? (+i.grams || 0) / i.g0 : 1; return { kcal: i.kcal * k, protein: i.protein * k, carbs: i.carbs * k, fat: i.fat * k }; };
  const draw = () => {
    const tot = base.reduce((a, i) => a + scaled(i).kcal, 0);
    $('#rv', w).innerHTML = `<div class="stat hl"><b>${Math.round(tot)} kcal</b><small>total</small></div>` + base.map((i, n) => { const s = scaled(i); return `<div class="rv-item"><div class="grow"><b>${esc(i.name)}</b><small>${Math.round(s.kcal)} kcal · P ${Math.round(s.protein)} · G ${Math.round(s.carbs)} · L ${Math.round(s.fat)}</small></div>
      ${i.g0 ? `<label class="mini rvg">g<input type="number" inputmode="decimal" data-n="${n}" value="${Math.round(i.grams)}"></label>` : ''}<button class="icon-btn sm danger" data-rm="${n}" aria-label="Retirer">✕</button></div>`; }).join('');
  };
  draw();
  $('#rv', w).addEventListener('change', (e) => { const n = e.target.dataset.n; if (n != null) { base[+n].grams = +e.target.value; draw(); } });
  $('#rv', w).addEventListener('click', (e) => { const b = e.target.closest('[data-rm]'); if (b) { base.splice(+b.dataset.rm, 1); draw(); } });
  $('#fadd', w).onclick = async () => {
    for (const i of base) { const s = scaled(i); await food.put({ id: uid('f'), date, meal: $('#fm', w).value, name: i.name, grams: i.grams || null, kcal: Math.round(s.kcal), p: +s.protein.toFixed(1), c: +s.carbs.toFixed(1), f: +s.fat.toFixed(1), src: 'photo' }); }
    w.close(); toast('Ajouté au journal ✓');
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
    const r = await fetchT(`https://search.openfoodfacts.org/search?q=${encodeURIComponent(q)}&page_size=60&langs=fr&fields=${fields}`);
    if (!r.ok) throw new Error();
    const j = await r.json();
    const out = (j.hits || []).map(offMap).filter(f => f && f.name).slice(0, 25);
    if (!out.length) throw new Error();
    return out;
  } catch (e) {
    const r = await fetchT(`https://world.openfoodfacts.org/cgi/search.pl?search_terms=${encodeURIComponent(q)}&search_simple=1&action=process&json=1&page_size=20&fields=${fields}`);
    const j = await r.json();
    return (j.products || []).map(offMap).filter(Boolean);
  }
}
export async function productOFF(code) {
  if (!navigator.onLine) throw new TypeError('offline');
  const r = await fetchT(`https://world.openfoodfacts.org/api/v2/product/${encodeURIComponent(code)}.json?fields=code,product_name,product_name_fr,brands,nutriments,serving_quantity`);
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

// ————— Recettes (Cookidoo, Thermomix, maison) —————
async function recipeList(el) {
  const rr = (await recipes.all()).sort((a, b) => (b.created || '').localeCompare(a.created || ''));
  el.innerHTML = `
  <section class="card cookidoo">
    <h3>🍲 Cookidoo & Thermomix</h3>
    <p class="small">Vorwerk n’autorise aucune app tierce à se connecter au Thermomix ou à Cookidoo (pas d’API). Le pont passe par Cookidoo :</p>
    <ol class="small">
      <li><b>Cookidoo → FORGE</b> : ouvre une recette sur cookidoo.fr, sélectionne tout le texte de la page, copie, puis « Importer depuis Cookidoo » : FORGE lit les portions, les valeurs nutritionnelles, les ingrédients et les étapes.</li>
      <li><b>FORGE → Thermomix</b> : sur une recette FORGE ou Claude, « Envoyer vers mon Thermomix » copie la recette au format Cookidoo. Colle-la dans Cookidoo → <i>Mes créations</i> → <i>Créer une recette</i>, ajoute-la à <i>Ma semaine</i> : elle s’affiche sur ton TM6 / TM7.</li>
      <li><b>Menu semaine</b> : planifie tes recettes, FORGE calcule tes portions.</li>
    </ol>
    <div class="row gap wrap"><button class="btn grow" data-act="rimport">⇩ Importer depuis Cookidoo</button><button class="btn ghost grow" data-act="radd">+ Recette maison</button></div>
    <a class="btn ghost block" href="https://cookidoo.fr" target="_blank" rel="noopener">Ouvrir Cookidoo ↗</a>
  </section>
  ${rr.map(r => `<button class="card recipe" data-act="ropen" data-id="${r.id}"><div><b>${esc(r.name)}</b><small>${r.kcal} kcal · P ${r.protein} g · G ${r.carbs} g · L ${r.fat} g / portion · ${r.portions} portions${r.totalWeight ? ' · ' + Math.round(r.totalWeight / r.portions) + ' g/portion' : ''}</small></div><span class="tag">${r.source === 'cookidoo' ? 'Cookidoo' : r.source === 'claude' ? 'Claude' : 'Maison'}</span></button>`).join('') || '<p class="muted center">Aucune recette pour l’instant.</p>'}`;
}

// Lit le texte copié depuis une page de recette Cookidoo.
export function parseCookidoo(txt) {
  const lines = txt.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  const n = (re) => { const m = txt.match(re); return m ? +m[1].replace(',', '.') : null; };
  const skip = /^(cookidoo|accueil|rechercher|recettes?|se connecter|menu|mes recettes|ma semaine|imprimer|partager|ajouter|\d+ ?min|facile|moyen|difficile|temps|préparation \d)/i;
  const name = lines.find(l => l.length > 3 && l.length < 90 && !skip.test(l) && !/kcal|portion|ingrédient/i.test(l)) || 'Recette Cookidoo';
  const section = (start, ends) => {
    const i = lines.findIndex(l => start.test(l)); if (i < 0) return [];
    const out = [];
    for (const l of lines.slice(i + 1)) { if (ends.test(l)) break; out.push(l); }
    return out.filter(l => l.length > 1 && l.length < 400);
  };
  const ingredients = section(/^ingr[ée]dients?$/i, /^(pr[ée]paration|ustensiles?|valeurs nutritionnelles|astuces?|conseils?)/i);
  const steps = section(/^pr[ée]paration$/i, /^(valeurs nutritionnelles|astuces?|conseils?|variantes?|ustensiles?|tags?|ces recettes)/i);
  return {
    name,
    portions: n(/(\d+)\s*(?:portions?|personnes?|parts?|pers\.)/i) || n(/portions?\s*:?\s*(\d+)/i) || 4,
    kcal: n(/(\d+(?:[.,]\d+)?)\s*kcal/i),
    protein: n(/prot[ée]ines?\s*:?\s*(\d+(?:[.,]\d+)?)\s*g/i),
    carbs: n(/glucides\s*:?\s*(\d+(?:[.,]\d+)?)\s*g/i),
    fat: n(/lipides\s*:?\s*(\d+(?:[.,]\d+)?)\s*g/i),
    ingredients, steps,
    link: (txt.match(/https:\/\/cookidoo\.[a-z.]+\/recipes\/recipe\/[^\s)"]+/) || [''])[0],
  };
}

function importCookidooSheet(rerender) {
  const w = sheet(`<h3>Importer depuis Cookidoo</h3>
    <ol class="small"><li>Ouvre la recette sur <b>cookidoo.fr</b> (ou l’app Cookidoo → Partager → Copier le lien, puis ouvre-la dans Safari).</li><li>Appuie longuement sur le texte → <b>Tout sélectionner</b> → <b>Copier</b>.</li><li>Colle ci-dessous.</li></ol>
    <textarea id="ctxt" rows="7" placeholder="Colle ici le texte de la recette…"></textarea>
    <button class="btn block" id="cgo">Lire la recette</button>`);
  $('#cgo', w).onclick = async () => {
    const txt = $('#ctxt', w).value; if (txt.trim().length < 30) return toast('Colle le texte complet de la recette');
    let r = parseCookidoo(txt);
    if ((!r.kcal || !r.ingredients.length) && S.settings.apiKey) {
      const b = $('#cgo', w); b.disabled = true; b.textContent = 'Claude lit la recette…';
      try {
        const d = await structured('Extrais cette recette Cookidoo / Thermomix (nom, portions, valeurs nutritionnelles PAR PORTION — estime-les si absentes —, ingrédients, étapes avec réglages Thermomix) :\n\n' + txt.slice(0, 20000), RECIPES_SCHEMA, '', { effort: 'low' });
        const x = d.recipes[0]; if (x) r = { ...r, ...x, link: r.link };
      } catch (e) { toast('Analyse Claude impossible : ' + e.message); }
    }
    w.close();
    recipeForm({ id: uid('r'), source: 'cookidoo', created: new Date().toISOString(), ...r, kcal: r.kcal ?? '', protein: r.protein ?? '', carbs: r.carbs ?? '', fat: r.fat ?? '' }, rerender, true);
    if (!r.kcal) toast('Valeurs nutritionnelles non trouvées : complète-les depuis la fiche Cookidoo', 5000);
  };
}

function thermomixText(o) {
  return `${o.name}\nPortions : ${o.portions}\n\nINGRÉDIENTS\n${(o.ingredients || []).map(i => '- ' + i).join('\n')}\n\nPRÉPARATION\n${(o.steps || []).map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\nValeurs par portion : ${o.kcal} kcal · protéines ${o.protein} g · glucides ${o.carbs} g · lipides ${o.fat} g`;
}

export function recipeForm(r, rerender, isNew = false) {
  const e = r || { id: uid('r'), name: '', portions: 4, kcal: '', protein: '', carbs: '', fat: '', totalWeight: '', link: '', ingredients: [], steps: [], source: 'perso', created: new Date().toISOString() };
  const existing = r && !isNew;
  const w = sheet(`<h3>${existing ? 'Recette' : 'Nouvelle recette'}</h3>
    <label class="field">Nom<input name="name" value="${esc(e.name)}"></label>
    <div class="grid3"><label class="mini">Portions<input type="number" name="portions" value="${e.portions}"></label>
    <label class="mini">Source<select name="source">${[['cookidoo', 'Cookidoo'], ['claude', 'Claude'], ['perso', 'Maison']].map(([k, l]) => `<option value="${k}" ${k === e.source ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <label class="mini">Repas<select name="meal"><option value="">Tous</option>${MEALS.map(([k, l]) => `<option value="${k}" ${k === e.meal ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <label class="mini">Kcal / portion<input type="number" inputmode="decimal" name="kcal" value="${e.kcal}"></label>
    <label class="mini">Prot. g<input type="number" inputmode="decimal" name="protein" value="${e.protein}"></label>
    <label class="mini">Gluc. g<input type="number" inputmode="decimal" name="carbs" value="${e.carbs}"></label>
    <label class="mini">Lip. g<input type="number" inputmode="decimal" name="fat" value="${e.fat}"></label>
    <label class="mini">Poids total g<input type="number" inputmode="decimal" name="totalWeight" value="${e.totalWeight || ''}" placeholder="opt."></label></div>
    <p class="muted small">Poids total de la préparation (pèse le bol du Thermomix, sans le bol) : FORGE te dira combien de grammes mettre dans ton assiette.</p>
    <label class="field">Lien Cookidoo<input name="link" type="url" placeholder="https://cookidoo.fr/recipes/recipe/fr-FR/r…" value="${esc(e.link || '')}"></label>
    <label class="field">Ingrédients (un par ligne)<textarea name="ingredients" rows="4">${esc((e.ingredients || []).join('\n'))}</textarea></label>
    <label class="field">Étapes (une par ligne, ex : 10 min / 100°C / vitesse 1)<textarea name="steps" rows="4">${esc((e.steps || []).join('\n'))}</textarea></label>
    <div class="row gap">${existing ? '<button class="btn ghost danger grow" id="rdel">Supprimer</button>' : ''}<button class="btn grow" id="rsave">Enregistrer</button></div>
    ${existing ? `<button class="btn ghost block" id="rlog">+ Ajouter au journal du jour</button>
    <button class="btn ghost block" id="rtm">📤 Envoyer vers mon Thermomix</button>
    ${e.link ? `<a class="btn ghost block" href="${esc(e.link)}" target="_blank" rel="noopener">Ouvrir dans Cookidoo ↗</a>` : ''}` : ''}`, { onClose: rerender });
  const read = () => { const o = { ...e }; $$('[name]', w).forEach(i => { const v = i.value; o[i.name] = ['ingredients', 'steps'].includes(i.name) ? v.split('\n').map(s => s.trim()).filter(Boolean) : i.type === 'number' ? (v === '' ? null : +v) : v; }); return o; };
  $('#rsave', w).onclick = async () => { const o = read(); if (!o.name) return toast('Donne un nom à la recette'); if (o.link && !/^https:\/\//.test(o.link)) o.link = ''; await recipes.put(o); toast('Recette enregistrée'); w.close(); };
  if (existing) {
    $('#rdel', w).onclick = async () => { if (await confirmBox('Supprimer cette recette ?', 'Supprimer')) { await recipes.del(e.id); w.close(); } };
    $('#rlog', w).onclick = () => quantity(recipeFood(read()), guessMeal(), w, today());
    $('#rtm', w).onclick = async () => {
      const txt = thermomixText(read());
      try { await navigator.clipboard.writeText(txt); } catch (err) { }
      const s = sheet(`<h3>📤 Vers ton Thermomix</h3><p class="small">Recette copiée. Dans Cookidoo : <b>Mes recettes → Mes créations → Créer une recette</b>, colle les ingrédients et les étapes, enregistre, puis ajoute-la à <b>Ma semaine</b>. Elle apparaît sur ton Thermomix connecté.</p>
        <textarea rows="8" readonly>${esc(txt)}</textarea><a class="btn block" href="https://cookidoo.fr" target="_blank" rel="noopener">Ouvrir Cookidoo ↗</a>`);
      $('textarea', s).onclick = (ev) => ev.target.select();
    };
  }
}

// ————— Calculateur —————
function calc(el) {
  const p = S.profile || {};
  el.innerHTML = `
  <section class="card"><h3>Dépense & besoins selon l’objectif</h3>
    <div class="grid3">
      <label class="mini">Sexe<select id="cs"><option value="h" ${p.sex !== 'f' ? 'selected' : ''}>Homme</option><option value="f" ${p.sex === 'f' ? 'selected' : ''}>Femme</option></select></label>
      <label class="mini">Âge<input type="number" id="ca" value="${p.age || 30}"></label>
      <label class="mini">Taille cm<input type="number" id="ch" value="${p.height || 175}"></label>
      <label class="mini">Poids kg<input type="number" id="cw" step="0.1" value="${p.weight || 75}"></label>
      <label class="mini">% MG (opt.)<input type="number" id="cb" step="0.1" value="${p.bodyfat || ''}"></label>
      <label class="mini">Activité<select id="cact">${Object.entries(ACTIVITY).map(([k, l]) => `<option value="${k}" ${+k === +(p.activity || 1.45) ? 'selected' : ''}>${l.replace(' + sport', '')}</option>`).join('')}</select></label>
    </div>
    <div id="cres"></div>
  </section>
  <section class="card"><h3>Calories d’une portion</h3>
    <p class="muted small">Valeurs pour 100 g (étiquette) → ta portion.</p>
    <div class="grid4"><label class="mini">Kcal/100 g<input type="number" id="pk" value="250"></label><label class="mini">Prot./100 g<input type="number" id="pp" value="10"></label><label class="mini">Gluc./100 g<input type="number" id="pc" value="30"></label><label class="mini">Lip./100 g<input type="number" id="pf" value="10"></label></div>
    <label class="field">Portion (g)<input type="number" id="pg" value="150"></label>
    <div class="stats4" id="pres"></div>
  </section>`;
  const run = () => {
    const pr = { sex: $('#cs').value, age: +$('#ca').value, height: +$('#ch').value, weight: +$('#cw').value, bodyfat: +$('#cb').value || null, activity: +$('#cact').value };
    $('#cres').innerHTML = `<p class="small muted">Métabolisme de base : <b>${Math.round(bmr(pr))} kcal</b> (${pr.bodyfat ? 'Katch-McArdle' : 'Mifflin-St Jeor'}) · dépense totale : <b>${targets({ ...pr, goal: 'maintien' }).tdee} kcal</b></p>
      <div class="table goals">${Object.entries(GOALS).map(([k, g]) => { const t = targets({ ...pr, goal: k }); return `<div class="tr ${k === p.goal ? 'cur' : ''}"><span><b>${g.short}</b><small>${g.adj > 0 ? '+' : ''}${Math.round(g.adj * 100)} %</small></span><b>${t.kcal} kcal</b><small>P ${t.p} · G ${t.c} · L ${t.f}</small></div>`; }).join('')}</div>`;
    const gg = (+$('#pg').value || 0) / 100;
    $('#pres').innerHTML = `<div class="stat hl"><b>${Math.round(+$('#pk').value * gg)}</b><small>kcal</small></div><div class="stat"><b>${num(+$('#pp').value * gg)}</b><small>prot.</small></div><div class="stat"><b>${num(+$('#pc').value * gg)}</b><small>gluc.</small></div><div class="stat"><b>${num(+$('#pf').value * gg)}</b><small>lip.</small></div>`;
  };
  el.addEventListener('input', run); el.addEventListener('change', run); run();
}

// ————— Actions —————
export async function onNutritionAction(act, el, rerender) {
  if (act === 'ntab') { ntab = el.dataset.t; return rerender(); }
  if (act.startsWith('plan-')) return onPlanAction(act, el, rerender);
  if (act === 'dprev') { day = shift(day, -1); return rerender(); }
  if (act === 'dnext') { day = shift(day, 1); return rerender(); }
  if (act === 'fadd') return addSheet(el.dataset.meal, rerender);
  if (act === 'fphoto') return photoSheet(guessMeal(), rerender);
  if (act === 'ecart') return ecartSheet(day, rerender);
  if (act === 'comp-check') return compensation(day, 0, rerender);
  if (act === 'comp-cancel') { delete S.comp[day]; await kv.set('comp', S.comp); return rerender(); }
  if (act === 'eat') { await toggleEaten(day, el.dataset.meal); toast('Ajouté au journal ✓'); return rerender(); }
  if (act === 'goal') {
    if (!S.profile) return toast('Crée d’abord ton profil');
    S.profile.goal = el.dataset.g; await kv.set('profile', S.profile);
    toast('Objectif : ' + GOALS[el.dataset.g].label); return rerender();
  }
  if (act === 'adapt') { S.profile.kcalAdjust = (+S.profile.kcalAdjust || 0) + +el.dataset.v; S.profile.adjustedAt = today(); await kv.set('profile', S.profile); toast('Calories ajustées'); return rerender(); }
  if (act === 'adapt-reset') { S.profile.kcalAdjust = 0; await kv.set('profile', S.profile); return rerender(); }
  if (act === 'water') { S.water[day] = Math.max(0, (S.water[day] || 0) + +el.dataset.d); await kv.set('water', S.water); return rerender(); }
  if (act === 'radd') return recipeForm(null, rerender);
  if (act === 'rimport') return importCookidooSheet(rerender);
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
    $('#edel', w).onclick = async () => { await food.del(e.id); for (const pl of Object.values(S.plan)) if (pl.done === e.id) pl.done = null; await kv.set('plan', S.plan); w.close(); };
    if (e.per100) $('#esave', w).onclick = async () => { const g = +$('#eg', w).value || 0, m = g / 100, b = e.per100; Object.assign(e, { grams: g, kcal: Math.round(b.kcal * m), p: +(b.p * m).toFixed(1), c: +(b.c * m).toFixed(1), f: +(b.f * m).toFixed(1) }); await food.put(e); w.close(); };
  }
}

// Utilisé par le coach
export async function addFoodItems(items, meal = guessMeal(), date = today()) {
  for (const it of items) await food.put({ id: uid('f'), date, meal, name: it.name, grams: it.grams || null, kcal: Math.round(it.kcal), p: +it.protein || 0, c: +it.carbs || 0, f: +it.fat || 0, src: 'claude' });
}

// ————— Tâches en attente (salle sans réseau) —————
registerHandler('barcode', async (t) => {
  const f = await productOFF(t.code);
  const e = await food.get(t.foodId); if (!e) return;
  const g = e.grams || f.serving || 100, m = g / 100;
  Object.assign(e, { name: f.name, grams: g, kcal: Math.round(f.kcal * m), p: +(f.p * m).toFixed(1), c: +(f.c * m).toFixed(1), f: +(f.f * m).toFixed(1), pending: false, src: 'off',
    per100: { kcal: f.kcal, p: f.p, c: f.c, f: f.f, brand: f.brand || '', src: 'off' } });
  await food.put(e);
});
registerHandler('photo', async (t) => {
  if (!S.settings.apiKey) throw new Error('clé API absente');
  const data = await structured(PHOTO_PROMPT + (t.desc ? ' Précisions : ' + t.desc : ''), FOOD_SCHEMA, await contextText({ days: 3 }), { images: [t.img], effort: 'medium' });
  await food.del(t.foodId);
  for (const i of data.items) await food.put({ id: uid('f'), date: t.date, meal: t.meal, name: i.name, grams: i.grams || null, kcal: Math.round(i.kcal), p: +(+i.protein).toFixed(1), c: +(+i.carbs).toFixed(1), f: +(+i.fat).toFixed(1), src: 'photo' });
});
