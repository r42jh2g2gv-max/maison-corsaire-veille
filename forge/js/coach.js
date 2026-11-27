// FORGE — Coach Claude : abonnement (copier/coller) ou clé API (intégré).
import { S, esc, $, $$, toast, sheet, confirmBox, contextText, targets, saveProgram, exById } from './ui.js';
import { kv, recipes, uid } from './db.js';
import { EXERCISES, makeItem } from './data.js';
import { chat, structured, extractJSON, FORMAT_HINT, PROGRAM_SCHEMA, RECIPES_SCHEMA, FOOD_SCHEMA, fileToBase64 } from './claude.js';
import { addFoodItems, guessMeal } from './nutrition.js';
import { defaultRole } from './train.js';

let history = null, busy = false;

const TASKS = {
  bilan: { label: '📊 Bilan de ma semaine', prompt: 'Fais le bilan de mes 7 derniers jours (entraînement, récupération, nutrition, évolution du corps). Dis-moi ce qui va bien, les 3 points à corriger en priorité et ce que je dois faire la semaine prochaine.' },
  programme: { label: '🏋️ Adapter mon programme', json: 'program', prompt: 'Analyse mes séances récentes (charges, reps, ressenti, notes) et adapte mon programme hybride pour continuer à gagner du muscle, perdre du gras, me tonifier et améliorer endurance, force et cardio. Garde la même structure de jours sauf si une meilleure répartition est justifiée. Garde les noms d’exercices français classiques.' },
  menu: { label: '🍲 Menu Thermomix de la semaine', json: 'recipes', prompt: 'Propose-moi 7 recettes réalisables au Thermomix (style Cookidoo), simples, adaptées à mes cibles caloriques et à ma forte consommation de protéines : 2 petits-déjeuners, 3 plats pour le midi/soir, 2 collations. Donne les macros PAR PORTION et les étapes avec réglages Thermomix (temps / température / vitesse).' },
  repas: { label: '🍽 Estimer un repas', json: 'food', ask: 'Décris ton repas (aliments, quantités approximatives)…', prompt: 'Estime les calories et macros de ce repas, aliment par aliment, avec des quantités réalistes :' },
  libre: { label: '💬 Question libre', ask: 'Ta question pour ton coach…', prompt: '' },
};

export async function renderCoach(view) {
  if (!history) history = (await kv.get('chat')) || [];
  const hasKey = !!S.settings.apiKey;
  view.innerHTML = `
  <section class="card">
    <h2>Coach Claude</h2>
    <p class="small">Claude connaît ton profil, ton programme, tes séances, tes mesures et ton journal alimentaire. Il peut <b>adapter ton programme</b>, faire ton <b>bilan</b>, créer un <b>menu Thermomix</b> ou <b>estimer un repas</b>.</p>
    <div class="seg sm"><button class="${!hasKey || S.coachMode === 'abo' ? 'on' : ''}" data-act="cmode" data-m="abo">Mon abonnement Claude</button><button class="${hasKey && S.coachMode !== 'abo' ? 'on' : ''}" data-act="cmode" data-m="api">Coach intégré (API)</button></div>
  </section>
  <div id="cbody"></div>`;
  if (!hasKey || S.coachMode === 'abo') aboMode($('#cbody', view)); else apiMode($('#cbody', view));
}

// ————— Voie 1 : abonnement claude.ai —————
function aboMode(el) {
  el.innerHTML = `
  <section class="card">
    <h3>1 · Choisis une demande</h3>
    <p class="muted small">FORGE prépare un message complet (toutes tes données) et le copie. Tu le colles dans l’app Claude : c’est inclus dans ton abonnement.</p>
    <div class="tasks">${Object.entries(TASKS).map(([k, t]) => `<button class="btn ghost block" data-act="abo-task" data-k="${k}">${t.label}</button>`).join('')}</div>
  </section>
  <section class="card">
    <h3>2 · Recolle la réponse de Claude</h3>
    <p class="muted small">Pour un programme, un menu ou un repas, Claude répond avec un bloc JSON : colle toute sa réponse ici, FORGE l’importe.</p>
    <textarea id="paste" rows="5" placeholder="Colle ici la réponse complète de Claude…"></textarea>
    <button class="btn block" data-act="abo-import">Importer dans FORGE</button>
  </section>
  ${!S.settings.apiKey ? `<section class="card muted small"><b>Envie que le coach réponde directement dans l’app ?</b> Il faut une clé API Anthropic (console.anthropic.com), facturée à l’usage, en plus de l’abonnement. À renseigner dans Profil → Claude.</section>` : ''}`;
}

async function buildPrompt(k, extra = '') {
  const t = TASKS[k];
  const ctx = await contextText();
  return `Tu es mon coach sportif (entraînement hybride force/hypertrophie/endurance/cardio) et mon diététicien. Voici mes données exportées depuis mon app FORGE :\n\n${ctx}\n\nDEMANDE : ${t.prompt}${extra ? '\n' + extra : ''}${t.json ? '\n\n' + FORMAT_HINT[t.json] : ''}`;
}

async function copyAndOpen(text) {
  try { await navigator.clipboard.writeText(text); toast('Message copié ✓ Colle-le dans Claude'); }
  catch (e) {
    const w = sheet(`<h3>Copie ce message</h3><textarea rows="10" readonly>${esc(text)}</textarea>`);
    const ta = $('textarea', w); ta.focus(); ta.select();
    return;
  }
  setTimeout(() => window.open('https://claude.ai/new', '_blank', 'noopener'), 400);
}

// ————— Voie 2 : API —————
function apiMode(el) {
  el.innerHTML = `
  <div class="tasks row gap wrap">${Object.entries(TASKS).filter(([k]) => k !== 'libre').map(([k, t]) => `<button class="chip" data-act="api-task" data-k="${k}">${t.label}</button>`).join('')}
    <label class="chip">📷 Photo de repas<input type="file" accept="image/*" capture="environment" data-act="meal-photo" hidden></label></div>
  <section class="chat" id="chat">${history.length ? history.map(m => bubble(m.role, m.content)).join('') : `<div class="bubble assistant">Salut ! Je suis ton coach. Pose-moi une question sur ton entraînement, ta nutrition ou ta récupération 💪</div>`}</section>
  <form class="chat-in" data-act="chat-send"><textarea id="msg" rows="1" placeholder="Écris à ton coach…"></textarea><button class="btn" ${busy ? 'disabled' : ''}>Envoyer</button></form>
  ${history.length ? '<button class="btn ghost sm" data-act="chat-clear">Effacer la conversation</button>' : ''}`;
  const c = $('#chat'); c.scrollTop = c.scrollHeight;
}

function md(t) {
  // mini-markdown : gras, listes, titres, sauts de ligne
  return esc(t).replace(/^### (.*)$/gm, '<b>$1</b>').replace(/^## (.*)$/gm, '<b>$1</b>').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/^[-•] (.*)$/gm, '• $1').replace(/\n/g, '<br>');
}
const bubble = (role, text) => `<div class="bubble ${role}">${role === 'assistant' ? md(text) : esc(text)}</div>`;

async function send(text) {
  if (busy || !text.trim()) return;
  busy = true;
  history.push({ role: 'user', content: text });
  const chatEl = $('#chat');
  chatEl.insertAdjacentHTML('beforeend', bubble('user', text) + `<div class="bubble assistant typing" id="live">…</div>`);
  chatEl.scrollTop = chatEl.scrollHeight;
  let acc = '';
  try {
    const ctx = await contextText();
    const reply = await chat(history.slice(-20), ctx, (d) => { acc += d; const l = $('#live'); if (l) { l.innerHTML = md(acc); l.classList.remove('typing'); chatEl.scrollTop = chatEl.scrollHeight; } });
    history.push({ role: 'assistant', content: reply });
    await kv.set('chat', history.slice(-40));
  } catch (e) {
    history.pop();
    const l = $('#live'); if (l) { l.textContent = '⚠️ ' + errText(e); l.classList.add('err'); }
  } finally {
    const l = $('#live'); if (l) l.removeAttribute('id');
    busy = false;
  }
}

function errText(e) {
  const s = e?.status;
  if (s === 401) return 'Clé API invalide. Vérifie-la dans Profil → Claude.';
  if (s === 429) return 'Trop de requêtes, réessaie dans une minute.';
  if (s === 529 || s >= 500) return 'Claude est surchargé, réessaie dans un instant.';
  if (e?.name === 'TypeError' || /fetch|network/i.test(e?.message)) return 'Pas de connexion internet.';
  return e?.message || 'Erreur inconnue';
}

// ————— Imports (communs aux deux voies) —————
const norm = (s) => s.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
async function findOrCreateEx(name, role) {
  const all = [...EXERCISES, ...S.custom];
  const n = norm(name);
  let ex = all.find(e => norm(e.name) === n) || all.find(e => norm(e.name).includes(n) || n.includes(norm(e.name)));
  if (ex) return ex;
  ex = { id: uid('x'), name, muscle: role === 'cardio' ? 'Cardio' : role === 'hiit' ? 'HIIT' : role === 'core' ? 'Abdos' : 'Corps entier', eq: 'smp', unit: role === 'cardio' ? 'cardio' : role === 'core' ? 'pdc' : 'kg', kind: role === 'iso' ? 'iso' : role, inc: 2.5, met: role === 'cardio' ? 7 : 5, custom: true };
  S.custom.push(ex); await kv.set('customExercises', S.custom);
  return ex;
}

async function importProgram(data) {
  if (!data?.days?.length) throw new Error('Aucun jour dans le programme');
  const w = sheet(`<h3>${esc(data.name || 'Programme proposé')}</h3>${data.explanation ? `<p class="small">${esc(data.explanation)}</p>` : ''}
    ${data.days.map(d => `<div class="hist-ex"><b>${esc(d.name)}</b><span>${d.items.map(i => esc(i.exercise)).join(' · ')}</span></div>`).join('')}
    <div class="row gap"><button class="btn ghost grow" data-close>Annuler</button><button class="btn grow" id="apply">Appliquer ce programme</button></div>`);
  $('#apply', w).onclick = async () => {
    const days = [];
    for (const [i, d] of data.days.entries()) {
      const items = [];
      for (const it of d.items || []) {
        const role = it.role || 'hyper';
        const ex = await findOrCreateEx(it.exercise, role);
        const base = makeItem(ex, role);
        const keys = role === 'cardio' ? ['minutes'] : role === 'hiit' ? ['rounds', 'work', 'restWork'] : it.secs && role === 'core' ? ['sets', 'secs', 'rest'] : ['sets', 'repMin', 'repMax', 'rest'];
        if (role === 'core' && it.secs) { delete base.repMin; delete base.repMax; }
        for (const k of keys) if (it[k] != null && it[k] !== 0) base[k] = it[k];
        items.push(base);
      }
      days.push({ id: uid('d' + i), name: d.name, focus: d.focus || '', items });
    }
    const keepStart = S.program?.startDate;
    S.program = { id: uid('p'), name: data.name || 'Programme Claude', created: new Date().toISOString(), startDate: keepStart || new Date().toISOString().slice(0, 10), weeks: 12, days, source: 'claude' };
    await saveProgram(); w.close(); toast('Programme mis à jour ✓'); location.hash = '#/entrainement';
  };
}

async function importRecipes(data) {
  const list = data?.recipes || [];
  if (!list.length) throw new Error('Aucune recette trouvée');
  for (const r of list) await recipes.put({ id: uid('r'), name: r.name, portions: r.portions || 1, kcal: Math.round(r.kcal), protein: Math.round(r.protein), carbs: Math.round(r.carbs), fat: Math.round(r.fat), ingredients: r.ingredients || [], steps: r.steps || [], meal: r.meal, source: 'claude', created: new Date().toISOString() });
  toast(`${list.length} recette(s) ajoutée(s) dans Nutrition → Recettes`);
}

async function importFood(data) {
  const items = data?.items || [];
  if (!items.length) throw new Error('Aucun aliment trouvé');
  const tot = items.reduce((a, i) => a + (+i.kcal || 0), 0);
  const w = sheet(`<h3>Repas estimé : ${Math.round(tot)} kcal</h3>
    ${items.map(i => `<div class="hist-ex"><b>${esc(i.name)}${i.grams ? ` <small>${Math.round(i.grams)} g</small>` : ''}</b><span>${Math.round(i.kcal)} kcal · P ${Math.round(i.protein)} · G ${Math.round(i.carbs)} · L ${Math.round(i.fat)}</span></div>`).join('')}
    ${data.comment ? `<p class="small">${esc(data.comment)}</p>` : ''}
    <label class="field">Repas<select id="fm">${[['matin', 'Petit-déjeuner'], ['midi', 'Déjeuner'], ['collation', 'Collation'], ['soir', 'Dîner']].map(([k, l]) => `<option value="${k}" ${k === guessMeal() ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <button class="btn block" id="fadd">Ajouter au journal d’aujourd’hui</button>`);
  $('#fadd', w).onclick = async () => { await addFoodItems(items, $('#fm', w).value); w.close(); toast('Ajouté au journal ✓'); };
}

function importAny(data) {
  if (data.days) return importProgram(data);
  if (data.recipes) return importRecipes(data);
  if (data.items) return importFood(data);
  throw new Error('Format non reconnu');
}

async function runApiTask(k, extra = '', images = []) {
  const t = TASKS[k];
  const schema = { program: PROGRAM_SCHEMA, recipes: RECIPES_SCHEMA, food: FOOD_SCHEMA }[t.json];
  const w = sheet(`<h3>${t.label}</h3><div class="loader"></div><p class="muted center">Claude réfléchit… (jusqu’à une minute)</p>`);
  try {
    const ctx = await contextText();
    if (!schema) {
      w.close();
      $('#msg').value = t.prompt + (extra ? '\n' + extra : '');
      return send($('#msg').value).then(() => { $('#msg').value = ''; });
    }
    const data = await structured(t.prompt + (extra ? '\n' + extra : ''), schema, ctx, { images, effort: k === 'programme' ? 'high' : 'medium' });
    w.close();
    await importAny(data);
  } catch (e) { w.close(); toast('⚠️ ' + errText(e), 5000); }
}

function ask(k, then) {
  const t = TASKS[k];
  if (!t.ask) return then('');
  const w = sheet(`<h3>${t.label}</h3><textarea id="askv" rows="4" placeholder="${esc(t.ask)}"></textarea><button class="btn block" id="askgo">Continuer</button>`);
  $('#askgo', w).onclick = () => { const v = $('#askv', w).value.trim(); if (!v) return; w.close(); then(v); };
  setTimeout(() => $('#askv', w)?.focus(), 50);
}

export async function onCoachAction(act, el, rerender) {
  if (act === 'cmode') {
    if (el.dataset.m === 'api' && !S.settings.apiKey) { toast('Ajoute d’abord ta clé API dans Profil → Claude'); location.hash = '#/profil'; return; }
    S.coachMode = el.dataset.m; return rerender();
  }
  if (act === 'abo-task') { const k = el.dataset.k; return ask(k, async (v) => copyAndOpen(await buildPrompt(k, v))); }
  if (act === 'abo-import') {
    const txt = $('#paste').value; if (!txt.trim()) return toast('Colle d’abord la réponse de Claude');
    try { await importAny(extractJSON(txt)); $('#paste').value = ''; } catch (e) { toast('Import impossible : ' + e.message + '. Vérifie que la réponse contient le bloc JSON.', 5000); }
  }
  if (act === 'api-task') { const k = el.dataset.k; return ask(k, (v) => runApiTask(k, v)); }
  if (act === 'chat-clear') { if (await confirmBox('Effacer la conversation ?', 'Effacer')) { history = []; await kv.set('chat', []); rerender(); } }
}

export async function onCoachChange(act, el) {
  if (act === 'meal-photo' && el.files[0]) {
    const img = await fileToBase64(el.files[0]);
    runApiTask('repas', 'Le repas est sur la photo jointe. Identifie chaque aliment et estime les portions visibles.', [img]);
  }
}

export async function onCoachSubmit(form) {
  const t = $('#msg'); const v = t.value; t.value = '';
  await send(v);
}
