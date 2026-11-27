// FORGE — outils d'interface partagés + état global.
import { kv, sessions, body, food, recipes } from './db.js';
import { exById as exByIdBase } from './data.js';

export const S = { profile: null, program: null, programs: [], custom: [], settings: {}, active: null, water: {}, health: {}, plan: {}, comp: {}, queue: [], usage: {} };

export async function loadState() {
  S.programs = (await kv.get('programs')) || [];
  S.health = (await kv.get('health')) || {};
  S.plan = (await kv.get('plan')) || {};
  S.comp = (await kv.get('comp')) || {};
  S.queue = (await kv.get('queue')) || [];
  S.usage = (await kv.get('usage')) || {};
  S.profile = await kv.get('profile');
  await repairWeights();
  S.program = await kv.get('program');
  S.custom = (await kv.get('customExercises')) || [];
  S.settings = (await kv.get('settings')) || {};
  S.active = await kv.get('active');
  S.water = (await kv.get('water')) || {};
}
// Réparation : poids importés en grammes (ex. 95000 → 95 kg)
async function repairWeights() {
  const fix = (w) => (w > 400 ? Math.round(w / 100) / 10 : w);
  let n = 0;
  for (const e of await body.all()) {
    if (+e.weight > 400) { e.weight = fix(+e.weight); if (e.bf) e.lean = Math.round(e.weight * (1 - e.bf / 100) * 10) / 10; await body.put(e); n++; }
  }
  if (S.profile && +S.profile.weight > 400) { S.profile.weight = fix(+S.profile.weight); await kv.set('profile', S.profile); n++; }
  return n;
}

export const saveProgram = () => kv.set('program', S.program);
export const saveActive = () => kv.set('active', S.active);
export const exById = (id) => exByIdBase(id, S.custom) || { id, name: id, muscle: '—', unit: 'kg', kind: 'hyper', inc: 2.5, met: 5 };

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
export const today = () => { const d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };
export const dayKey = (iso) => { const d = new Date(iso); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };
// Heure de prise des repas
export const nowTime = () => { const d = new Date(); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
export const MEAL_TIME = { matin: '08:00', midi: '12:30', collation: '16:30', soir: '20:00' };
export const mealFromTime = (t) => { const h = +String(t || '').split(':')[0]; return isNaN(h) ? null : h < 11 ? 'matin' : h < 15 ? 'midi' : h < 18 ? 'collation' : 'soir'; };
export const defTime = (date, meal) => (date === today() && (!meal || mealFromTime(nowTime()) === meal)) ? nowTime() : (MEAL_TIME[meal] || nowTime());
// Champs « Repas » + « Heure » liés : changer l'heure choisit le repas
export function mealTimeFields(meal, time, ids = ['qmeal', 'qtime']) {
  return `<div class="grid2"><label class="mini">Repas<select id="${ids[0]}">${[['matin', 'Petit-déjeuner'], ['midi', 'Déjeuner'], ['collation', 'Collation'], ['soir', 'Dîner']].map(([k, l]) => `<option value="${k}" ${k === meal ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <label class="mini">Heure<input type="time" id="${ids[1]}" value="${time}"></label></div>`;
}
export function bindMealTime(w, ids = ['qmeal', 'qtime']) {
  const t = w.querySelector('#' + ids[1]), m = w.querySelector('#' + ids[0]);
  t.addEventListener('change', () => { const k = mealFromTime(t.value); if (k) m.value = k; });
  m.addEventListener('change', () => { if (!t.dataset.touched) t.value = MEAL_TIME[m.value]; });
  t.addEventListener('input', () => { t.dataset.touched = '1'; });
}
export const fmtTime = (s) => { s = Math.max(0, Math.round(s)); const m = Math.floor(s / 60), r = s % 60; return `${m}:${String(r).padStart(2, '0')}`; };
export const fmtDur = (min) => min >= 60 ? `${Math.floor(min / 60)} h ${String(Math.round(min % 60)).padStart(2, '0')}` : `${Math.round(min)} min`;
export const fmtDate = (iso, opts = { weekday: 'short', day: 'numeric', month: 'short' }) => new Date(iso).toLocaleDateString('fr-FR', opts);
export const num = (v, d = 1) => (v == null || isNaN(v)) ? '—' : (+(+v).toFixed(d)).toLocaleString('fr-FR');
export const round = (v, step = 0.5) => Math.round(v / step) * step;

// e1RM (Epley)
export const e1rm = (w, r) => (!w || !r) ? 0 : r === 1 ? w : w * (1 + r / 30);

export function toast(msg, ms = 2600) {
  const t = document.createElement('div');
  t.className = 'toast'; t.textContent = msg;
  document.body.appendChild(t);
  requestAnimationFrame(() => t.classList.add('show'));
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, ms);
}

// Feuille modale. Retourne l'élément ; close() pour fermer.
export function sheet(html, { onClose } = {}) {
  const wrap = document.createElement('div');
  wrap.className = 'sheet-wrap';
  wrap.innerHTML = `<div class="sheet" role="dialog" aria-modal="true"><button class="sheet-x" data-close aria-label="Fermer">×</button>${html}</div>`;
  document.body.appendChild(wrap);
  requestAnimationFrame(() => wrap.classList.add('open'));
  const close = () => { wrap.classList.remove('open'); setTimeout(() => wrap.remove(), 250); onClose && onClose(); };
  wrap.addEventListener('click', (e) => { if (e.target === wrap || e.target.closest('[data-close]')) close(); });
  wrap.close = close;
  return wrap;
}

export function confirmBox(msg, okLabel = 'Confirmer') {
  return new Promise(res => {
    const w = sheet(`<h3>${esc(msg)}</h3><div class="row gap"><button class="btn ghost grow" data-no>Annuler</button><button class="btn danger grow" data-yes>${esc(okLabel)}</button></div>`, { onClose: () => res(false) });
    w.querySelector('[data-yes]').onclick = () => { res(true); w.close(); };
    w.querySelector('[data-no]').onclick = () => { res(false); w.close(); };
  });
}

// Bip + vibration (fin de repos)
let actx;
export function beep(times = 3, vib = true) {
  if (S.settings.restSound !== false) try {
    actx = actx || new (window.AudioContext || window.webkitAudioContext)();
    for (let i = 0; i < times; i++) {
      const o = actx.createOscillator(), g = actx.createGain();
      o.frequency.value = i === times - 1 ? 1320 : 880; o.type = 'sine';
      g.gain.setValueAtTime(0.0001, actx.currentTime + i * 0.25);
      g.gain.exponentialRampToValueAtTime(0.4, actx.currentTime + i * 0.25 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, actx.currentTime + i * 0.25 + 0.18);
      o.connect(g).connect(actx.destination); o.start(actx.currentTime + i * 0.25); o.stop(actx.currentTime + i * 0.25 + 0.2);
    }
  } catch (e) { /* audio indisponible */ }
  if (vib && S.settings.restVibe !== false && navigator.vibrate) navigator.vibrate([200, 100, 200, 100, 300]);
}
export function unlockAudio() { try { actx = actx || new (window.AudioContext || window.webkitAudioContext)(); actx.resume(); } catch (e) { } }

// — Calculs physiologiques —
export function bmr(p) {
  if (!p) return 0;
  const w = +p.weight, h = +p.height, a = +p.age;
  if (p.bodyfat) return 370 + 21.6 * (w * (1 - p.bodyfat / 100)); // Katch-McArdle si % MG connu
  return 10 * w + 6.25 * h - 5 * a + (p.sex === 'f' ? -161 : 5);
}
export const ACTIVITY = { 1.3: 'Sédentaire (bureau) + sport', 1.45: 'Peu actif + sport', 1.6: 'Actif (debout, marche) + sport', 1.75: 'Très actif (métier physique) + sport' };

// Objectifs : ajustement calorique, protéines et lipides (g/kg), rythme visé (% du poids par semaine), cyclage des glucides.
export const GOALS = {
  perte: { label: 'Perte de poids', short: 'Perte', adj: -0.20, prot: 2.0, fat: 0.8, rate: -0.7, cycle: true, desc: 'Déficit de 20 % : environ −0,5 à −0,8 % du poids par semaine. Protéines hautes pour limiter la perte de muscle.' },
  seche: { label: 'Sèche (garder le muscle)', short: 'Sèche', adj: -0.15, prot: 2.4, fat: 0.8, rate: -0.5, cycle: true, desc: 'Déficit modéré, protéines très hautes, glucides concentrés les jours d’entraînement pour garder la force.' },
  recompo: { label: 'Recomposition : muscle + perte de gras', short: 'Recompo', adj: -0.08, prot: 2.2, fat: 0.9, rate: -0.2, cycle: true, desc: 'Léger déficit : le poids bouge peu mais la taille baisse et la force monte.' },
  maintien: { label: 'Tonifier / maintenir', short: 'Maintien', adj: 0, prot: 1.8, fat: 1.0, rate: 0, cycle: false, desc: 'Calories de maintien : on garde le poids, on améliore la forme et le tonus.' },
  prise: { label: 'Prise de muscle', short: 'Prise', adj: 0.10, prot: 1.8, fat: 1.0, rate: 0.25, cycle: false, desc: 'Surplus de 10 % : environ +0,25 % du poids par semaine pour limiter la prise de gras.' },
};
export const goalOf = (p) => GOALS[p?.goal] || GOALS.recompo;
export const WEEKDAYS = ['Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa', 'Di'];
export const defaultTrainingDays = (n) => ({ 2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 2, 4, 5], 6: [0, 1, 2, 3, 4, 5] }[n] || [0, 2, 4]);
export const weekdayIdx = (date) => (new Date(date + 'T12:00:00').getDay() + 6) % 7;
export function isTrainingDay(p, date) {
  const days = p?.trainingDays?.length ? p.trainingDays : defaultTrainingDays(+p?.days || 4);
  return days.includes(weekdayIdx(date));
}

// Cibles du jour. date optionnelle → cyclage glucides (jour d'entraînement / repos) et dépense réelle de l'Apple Watch.
export function targets(p, date) {
  if (!p) return { kcal: 2000, p: 140, c: 200, f: 65, tdee: 2000, base: 2000 };
  const g = goalOf(p);
  let tdee = bmr(p) * (+p.activity || 1.45);
  const h = date && S.health?.[date];
  let watch = false;
  if (date && p.useWatch && h?.active) { tdee = bmr(p) * 1.1 + +h.active; watch = true; } // basal + activité mesurée + digestion
  const base = Math.round((tdee * (1 + g.adj) + (+p.kcalAdjust || 0)) / 10) * 10;
  let kcal = base, dayType = null;
  if (date && g.cycle && p.carbCycle !== false && !watch) {
    const n = (p.trainingDays?.length || defaultTrainingDays(+p.days || 4).length);
    const train = isTrainingDay(p, date);
    dayType = train ? 'entrainement' : 'repos';
    const bump = 150;
    kcal = Math.round((train ? base + bump : base - bump * n / Math.max(1, 7 - n)) / 10) * 10;
  }
  const comp = date ? (+S.comp?.[date] || 0) : 0; // rattrapage d'un écart
  kcal -= comp;
  const w = +p.weight;
  const prot = Math.round(w * g.prot);
  const fat = Math.round(w * g.fat);
  const carbs = Math.max(50, Math.round((kcal - prot * 4 - fat * 9) / 4));
  return { kcal, p: prot, c: carbs, f: fat, tdee: Math.round(tdee), base, dayType, watch, comp };
}

// Ajustement automatique : compare la tendance réelle du poids au rythme visé.
export function adaptiveAdvice(p, entries) {
  if (!p) return null;
  const g = goalOf(p);
  const now = Date.now();
  const pts = entries.filter(e => e.weight && now - new Date(e.date) < 28 * 86400000).map(e => ({ t: new Date(e.date).getTime() / 86400000 / 7, w: +e.weight }));
  if (pts.length < 3 || (pts[pts.length - 1].t - pts[0].t) < 10 / 7) return { ready: false, n: pts.length };
  const mt = pts.reduce((a, x) => a + x.t, 0) / pts.length, mw = pts.reduce((a, x) => a + x.w, 0) / pts.length;
  const slope = pts.reduce((a, x) => a + (x.t - mt) * (x.w - mw), 0) / pts.reduce((a, x) => a + (x.t - mt) ** 2, 0); // kg / semaine
  const expected = g.rate / 100 * mw;
  const diff = slope - expected;
  let adjust = 0;
  if (Math.abs(diff) > 0.15) adjust = Math.max(-300, Math.min(300, -Math.round(diff * 1100 / 50) * 50));
  return { ready: true, slope, expected, adjust };
}

export async function archiveProgram(prog = S.program) {
  if (!prog) return;
  S.programs = (S.programs || []).filter(x => x.id !== prog.id);
  S.programs.unshift({ ...prog, archived: new Date().toISOString() });
  await kv.set('programs', S.programs);
}
// Estimation % masse grasse (méthode US Navy)
export function navyBF(sex, height, neck, waist, hip) {
  if (!height || !neck || !waist) return null;
  if (sex === 'f') { if (!hip) return null; return 163.205 * Math.log10(+waist + +hip - +neck) - 97.684 * Math.log10(+height) - 78.387; }
  return 86.01 * Math.log10(+waist - +neck) - 70.041 * Math.log10(+height) + 36.76;
}
// Dépense d'une séance (MET)
export function sessionKcal(sess, weightKg) {
  const w = weightKg || 75;
  if (sess.kcal) return sess.kcal;
  let k = 0;
  for (const ex of sess.exercises || []) {
    const e = exById(ex.exId);
    if (ex.cardio) { k += (e.met || 7) * w * ((ex.cardio.minutes || 0) / 60); continue; }
    if (ex.hiit) { k += (e.met || 10) * w * (((ex.hiit.done || 0) * (ex.hiit.work + ex.hiit.restWork * 0.3)) / 3600); continue; }
    const done = (ex.sets || []).filter(s => s.done).length;
    k += (e.met || 5) * w * (done * 1.6 / 60); // ~1 min 40 par série, repos inclus partiellement
  }
  return Math.round(k);
}

// Toutes les données récentes en texte, pour Claude.
export async function contextText({ days = 21 } = {}) {
  const p = S.profile || {};
  const t = targets(p);
  const since = Date.now() - days * 86400000;
  const ss = (await sessions.all()).filter(s => new Date(s.date).getTime() >= since).sort((a, b) => a.date.localeCompare(b.date));
  const bb = (await body.all()).sort((a, b) => a.date.localeCompare(b.date)).slice(-8);
  const ff = (await food.all()).filter(f => new Date(f.date).getTime() >= since);
  const byDay = {};
  for (const f of ff) { const d = byDay[f.date] ||= { kcal: 0, p: 0 }; d.kcal += f.kcal; d.p += f.p; }
  const lines = [];
  const hd = Object.entries(S.health || {}).sort().slice(-7);
  if (hd.length) lines.push('APPLE SANTÉ (7 derniers jours) : ' + hd.map(([d, h]) => `${d} ${h.steps ?? '?'} pas, ${h.active ?? '?'} kcal actives${h.rhr ? ', FC repos ' + h.rhr : ''}${h.sleep ? ', sommeil ' + h.sleep + ' h' : ''}`).join(' | '));
  lines.push(`PROFIL : ${p.name || 'Utilisateur'}, ${p.sex === 'f' ? 'femme' : 'homme'}, ${p.age} ans, ${p.height} cm, ${p.weight} kg${p.bodyfat ? `, ${p.bodyfat} % MG` : ''}. Niveau : ${p.level}. Objectif : ${goalOf(p).label}. ${p.days} séances/semaine, matériel : ${p.equipment}. ${p.notes ? 'Notes : ' + p.notes : ''}`);
  lines.push(`CIBLES NUTRITION : ${t.kcal} kcal/j (dépense estimée ${t.tdee}), protéines ${t.p} g, glucides ${t.c} g, lipides ${t.f} g.`);
  if (S.program) {
    lines.push(`PROGRAMME ACTUEL « ${S.program.name} » (début ${S.program.startDate}) :`);
    for (const d of S.program.days) lines.push(`- ${d.name} : ` + d.items.map(it => {
      const e = exById(it.exId);
      if (it.role === 'cardio') return `${e.name} ${it.minutes} min`;
      if (it.role === 'hiit') return `${e.name} ${it.rounds}×${it.work}s/${it.restWork}s`;
      return `${e.name} ${it.sets}×${it.secs ? it.secs + 's' : it.repMin + '-' + it.repMax} (repos ${it.rest}s)`;
    }).join(' ; '));
  }
  lines.push(`SÉANCES DES ${days} DERNIERS JOURS (${ss.length}) :`);
  for (const s of ss) {
    const ex = (s.exercises || []).map(x => {
      const e = exById(x.exId);
      if (x.cardio) return `${e.name} ${x.cardio.minutes || 0} min${x.cardio.km ? ' ' + x.cardio.km + ' km' : ''}`;
      if (x.hiit) return `${e.name} ${x.hiit.done || 0} rounds`;
      const sets = (x.sets || []).filter(z => z.done).map(z => z.secs ? z.secs + 's' : `${z.w || 0}×${z.r || 0}`).join(', ');
      return sets ? `${e.name} [${sets}]` : '';
    }).filter(Boolean).join(' ; ');
    lines.push(`- ${s.date.slice(0, 10)} ${s.name} (${s.minutes || '?'} min${s.rpe ? ', ressenti ' + s.rpe + '/10' : ''}) : ${ex}${s.note ? ' — note : ' + s.note : ''}`);
  }
  if (bb.length) lines.push('CORPS : ' + bb.map(b => `${b.date} ${b.weight ?? '?'} kg${b.waist ? ' taille ' + b.waist + ' cm' : ''}${b.bf ? ' ' + num(b.bf) + ' % MG' : ''}`).join(' | '));
  const dd = Object.entries(byDay).sort().slice(-10);
  if (dd.length) lines.push('NUTRITION (kcal / protéines) : ' + dd.map(([d, v]) => `${d} ${Math.round(v.kcal)} kcal ${Math.round(v.p)} g P`).join(' | '));
  const rr = await recipes.all();
  if (rr.length) lines.push('RECETTES ENREGISTRÉES (Cookidoo / perso) : ' + rr.slice(0, 30).map(r => `${r.name} (${r.kcal} kcal/portion)`).join(', '));
  return lines.join('\n');
}
