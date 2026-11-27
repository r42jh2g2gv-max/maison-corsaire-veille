// FORGE — programme, séance en direct, minuteurs de repos et d'intervalles, historique.
import { S, esc, $, $$, exById, saveProgram, archiveProgram, WEEKDAYS, saveActive, toast, sheet, confirmBox, beep, unlockAudio, fmtTime, fmtDur, fmtDate, num, round, e1rm, sessionKcal } from './ui.js';
import { sessions, kv, uid } from './db.js';
import { EXERCISES, MUSCLES, makeItem, weekInfo, applyBlock, generateProgram, PRESETS, dayMinutes, WEEKDAY_LONG, fitProgramToTime, fitDayToTime } from './data.js';
import { hr, parseActivity } from './devices.js';
import { exInfoSheet } from './exinfo.js';

const ROLE_LABEL = { force: 'Force', hyper: 'Hypertrophie', iso: 'Isolation', core: 'Gainage', cardio: 'Cardio', hiit: 'HIIT' };

export function prescription(it) {
  if (it.role === 'cardio') return `${it.minutes} min${it.zone ? ' · zone ' + it.zone : ''}`;
  if (it.role === 'hiit') return `${it.rounds} × ${it.work}s effort / ${it.restWork}s récup`;
  const reps = it.secs ? `${it.secs} s` : it.repMin === it.repMax ? `${it.repMin}` : `${it.repMin}–${it.repMax}`;
  return `${it.sets} × ${reps} · repos ${fmtTime(it.rest || 60)}`;
}

// ————— Historique / suggestions —————
let cacheSessions = null;
export async function allSessions(force = false) {
  if (!cacheSessions || force) cacheSessions = (await sessions.all()).sort((a, b) => b.date.localeCompare(a.date));
  return cacheSessions;
}
export const invalidateSessions = () => { cacheSessions = null; };

function lastPerf(exId, list) {
  for (const s of list) {
    const x = (s.exercises || []).find(e => e.exId === exId && ((e.sets || []).some(z => z.done) || e.cardio?.done || e.hiit?.done));
    if (x) return { date: s.date, ex: x };
  }
  return null;
}

function suggest(it, last, ex) {
  if (!last || !last.ex.sets) return null;
  const done = last.ex.sets.filter(z => z.done);
  if (!done.length) return null;
  if (it.secs) { const best = Math.max(...done.map(z => z.secs || 0)); return { secs: best >= it.secs ? best + 5 : it.secs, msg: best >= it.secs ? '+5 s' : 'Même durée' }; }
  const w = Math.max(...done.map(z => +z.w || 0));
  const allHit = done.length >= (it.sets || 1) && done.every(z => (+z.r || 0) >= it.repMax);
  const misses = done.filter(z => (+z.r || 0) < it.repMin).length;
  if (ex.unit === 'pdc' && !w) {
    const best = Math.max(...done.map(z => +z.r || 0));
    return allHit ? { w: 0, r: Math.min(best + 1, it.repMax + 3), msg: 'Objectif atteint : +1 rep ou ajoute du lest / une variante plus dure' } : { w: 0, r: best, msg: 'Vise +1 rep sur chaque série' };
  }
  if (allHit) return { w: round(w + (ex.inc || 2.5), ex.inc >= 2.5 ? 0.5 : 0.5), msg: `+${ex.inc || 2.5} kg : haut de fourchette atteint partout 💪` };
  if (misses >= 2) return { w: round(w * 0.95, 0.5), msg: 'Charge −5 % : plusieurs séries sous la fourchette' };
  return { w, msg: 'Même charge : ajoute 1 rep là où tu peux' };
}

function lastText(last) {
  if (!last) return '';
  const x = last.ex;
  if (x.cardio) return `Dernière : ${x.cardio.minutes || 0} min${x.cardio.km ? ' · ' + x.cardio.km + ' km' : ''}`;
  if (x.hiit) return `Dernière : ${x.hiit.done} rounds`;
  return 'Dernière : ' + x.sets.filter(z => z.done).map(z => z.secs ? z.secs + 's' : (+z.w ? `${num(z.w)}×${z.r}` : `${z.r} reps`)).join(' · ');
}

// ————— Écran Entraînement —————
export async function renderTrain(view) {
  if (!S.program) {
    view.innerHTML = `<section class="card hero"><h2>Pas encore de programme</h2><p>Complète ton profil pour générer ton programme hybride sur mesure.</p>${S.profile ? '<button class="btn block" data-act="catalog">📋 Choisir un programme prédéfini</button>' : '<a class="btn" href="#/profil">Créer mon profil</a>'}${S.programs?.length ? '<button class="btn ghost block" data-act="programs">📚 Mes programmes</button>' : ''}</section>`;
    return;
  }
  const info = weekInfo(S.program);
  const list = await allSessions();
  const weekStart = new Date(); weekStart.setHours(0, 0, 0, 0); weekStart.setDate(weekStart.getDate() - ((weekStart.getDay() + 6) % 7));
  const doneThisWeek = new Set(list.filter(s => new Date(s.date) >= weekStart).flatMap(s => [s.dayId, ...(s.dayIds || [])]));
  view.innerHTML = `
  ${S.active ? `<a class="card resume" href="#/seance"><b>▶ Séance en cours</b><span>${esc(S.active.name)}</span></a>` : ''}
  <section class="card">
    <div class="row between"><div><div class="eyebrow">Semaine ${info.week} / ${info.total} · Bloc ${info.block}</div><h2>${esc(S.program.name)}</h2></div>
    <button class="icon-btn" data-act="prog-menu" aria-label="Réglages du programme">⚙︎</button></div>
    <div class="phase ${info.deload ? 'deload' : ''}">${info.phase}${info.off ? ' — tes séries et reps, sans cycle automatique' : info.deload ? ' — semaine allégée pour récupérer' : info.block === 1 ? ' — on construit le volume' : info.block === 2 ? ' — charges plus lourdes, moins de reps' : ' — on exprime la force et la forme'}</div>
    <div class="row gap wrap prog-actions"><button class="btn sm grow" data-act="catalog">📋 Prédéfinis</button><button class="btn sm ghost grow" data-act="programs">📚 Mes programmes</button><button class="btn sm ghost grow" data-act="prog-menu">✎ Modifier</button><a class="btn sm ghost grow" href="#/coach">🤖 Adapter</a></div>
    <div class="weekbar">${Array.from({ length: info.total }, (_, i) => `<i class="${i + 1 < info.week ? 'past' : i + 1 === info.week ? 'now' : ''} ${(i + 1) % 4 === 0 ? 'dl' : ''}"></i>`).join('')}</div>
  </section>
  <h3 class="sec">Séances du programme</h3>
  ${S.program.days.map(d => `
    <section class="card day ${doneThisWeek.has(d.id) ? 'done' : ''}">
      <div class="row between"><div><h3>${esc(d.name)}</h3><div class="muted">${esc(d.focus || '')} · ${d.items.length} exercices · ≈ ${dayMinutes(d, S.program.periodize !== false)} min${S.program.minutes && dayMinutes(d, S.program.periodize !== false) > S.program.minutes + 2 ? ' ⚠️' : ''}${doneThisWeek.has(d.id) ? ' · ✓ fait cette semaine' : ''}</div></div>
      <button class="btn sm ghost" data-act="edit-day" data-id="${d.id}">✎ Modifier</button></div>
      <ul class="exlist">${d.items.map(it => { const e = exById(it.exId); const b = applyBlock(it, info); return `<li data-act="exinfo-prog" data-ex="${it.exId}"><span>${esc(e.name)} <i class="info">ⓘ</i></span><small>${prescription(b)}</small></li>`; }).join('')}</ul>
      <button class="btn block" data-act="start" data-id="${d.id}">Démarrer</button>
    </section>`).join('')}
  <div class="row gap wrap">
    <button class="btn ghost grow" data-act="start-free">+ Séance libre</button>
    <button class="btn ghost grow" data-act="add-day">+ Ajouter un jour</button>
    <label class="btn ghost grow">⇪ GPX / TCX<input type="file" accept=".gpx,.tcx,application/gpx+xml,application/xml,text/xml" data-act="import-activity" hidden></label>
  </div>
  <h3 class="sec">Historique</h3>
  ${list.length ? list.slice(0, 40).map(s => `<button class="card hist" data-act="hist" data-id="${s.id}"><div><b>${esc(s.name)}</b><small>${fmtDate(s.date)} · ${fmtDur(s.minutes || 0)}${s.volume ? ' · ' + num(s.volume / 1000, 1) + ' t' : ''}${s.kcal ? ' · ' + s.kcal + ' kcal' : ''}</small></div><span>›</span></button>`).join('') : '<p class="muted center">Tes séances apparaîtront ici.</p>'}
  `;
}

export async function onTrainAction(act, el, rerender) {
  if (act === 'start') return startSession(el.dataset.id);
  if (act === 'start-free') return startSession(null);
  if (act === 'edit-day') return editDay(el.dataset.id, rerender);
  if (act === 'add-day') {
    S.program.days.push({ id: uid('d'), name: `J${S.program.days.length + 1} · Nouvelle séance`, focus: 'Perso', items: [] });
    await saveProgram(); rerender(); return editDay(S.program.days[S.program.days.length - 1].id, rerender);
  }
  if (act === 'prog-menu') return programMenu(rerender);
  if (act === 'programs') return programsSheet(rerender);
  if (act === 'exinfo-prog') return exInfoSheet(el.dataset.ex);
  if (act === 'catalog') return catalogSheet(rerender);
  if (act === 'hist') return showSession(el.dataset.id, rerender);
}

export async function onTrainChange(act, el, rerender) {
  if (act === 'import-activity' && el.files[0]) {
    try {
      const a = parseActivity(await el.files[0].text(), el.files[0].name);
      const s = { id: uid('s'), date: a.start, name: a.name, dayId: null, minutes: a.minutes, kcal: a.kcal, avgHr: a.avgHr, maxHr: a.maxHr, imported: true,
        exercises: [{ exId: a.type, role: 'cardio', cardio: { minutes: a.minutes, km: a.km, hr: a.avgHr, kcal: a.kcal, done: true } }] };
      s.kcal = s.kcal || sessionKcal(s, S.profile?.weight);
      await sessions.put(s); invalidateSessions();
      toast(`Importé : ${a.km} km en ${fmtDur(a.minutes)}`); rerender();
    } catch (e) { toast('Import impossible : ' + e.message); }
  }
}

function programMenu(rerender) {
  const P = S.program;
  const w = sheet(`<h3>Modifier le programme</h3>
    <label class="field">Nom<input id="pname" value="${esc(P.name)}"></label>
    <div class="grid2"><label class="mini">Début (semaine 1)<input type="date" id="pstart" value="${P.startDate}"></label>
    <label class="mini">Temps max / séance (min)<input type="number" id="pmin" inputmode="numeric" min="20" max="180" step="5" value="${P.minutes || S.profile?.sessionMinutes || 60}"></label>
    <label class="mini">Durée<select id="pweeks">${[4, 6, 8, 10, 12, 16].map(n => `<option value="${n}" ${n === (P.weeks || 12) ? 'selected' : ''}>${n} semaines</option>`).join('')}</select></label></div>
    <label class="field">Progression par blocs<select id="pperiod"><option value="on" ${P.periodize !== false ? 'selected' : ''}>Oui : volume → force → pic, décharge toutes les 4 sem.</option><option value="off" ${P.periodize === false ? 'selected' : ''}>Non : toujours les séries/reps que je définis</option></select></label>
    <h3 class="sec">Jours (ordre avec ↑ ↓)</h3>
    <div id="pdays"></div>
    <button class="btn ghost block" id="padd">+ Ajouter un jour</button>
    <button class="btn block" id="psave">Enregistrer</button>
    <hr>
    <button class="btn ghost block" id="pdup">⧉ Dupliquer ce programme</button>
    <button class="btn ghost block" id="pregen">📋 Choisir un programme prédéfini</button>
    <button class="btn ghost block" id="pblank">＋ Programme vide (je construis tout)</button>
    <p class="muted small">L’ancien programme est rangé dans « Mes programmes » : tu peux y revenir à tout moment.</p>`, { onClose: rerender });
  const days = [...P.days];
  const draw = () => { $('#pdays', w).innerHTML = days.map((d, i) => `<div class="edit-item row between"><span class="grow"><b>${esc(d.name)}</b><br><small class="muted">${d.items.length} exercices</small></span>
    <button class="icon-btn sm" data-mv="-1" data-i="${i}" aria-label="Monter">↑</button><button class="icon-btn sm" data-mv="1" data-i="${i}" aria-label="Descendre">↓</button><button class="icon-btn sm" data-ed="${i}" aria-label="Modifier">✎</button><button class="icon-btn sm" data-cp="${i}" aria-label="Dupliquer">⧉</button><button class="icon-btn sm danger" data-rm="${i}" aria-label="Supprimer">✕</button></div>`).join(''); };
  draw();
  const commit = async () => {
    const mn = Math.min(180, Math.max(20, Math.round((+$('#pmin', w).value || 60) / 5) * 5));
    P.days = days; P.periodize = $('#pperiod', w).value === 'on';
    if (mn !== P.minutes) { fitProgramToTime(P, mn, S.profile?.goal); if (S.profile) { S.profile.sessionMinutes = mn; await kv.set('profile', S.profile); } toast(`Séances ajustées à ${mn} min max`); }
    P.name = $('#pname', w).value; P.startDate = $('#pstart', w).value; P.weeks = +$('#pweeks', w).value; P.periodize = $('#pperiod', w).value === 'on'; await saveProgram(); };
  $('#pdays', w).onclick = async (e) => {
    const b = e.target.closest('button'); if (!b) return; const i = +b.dataset.i;
    if (b.dataset.mv) { const j = i + +b.dataset.mv; if (j >= 0 && j < days.length) [days[i], days[j]] = [days[j], days[i]]; draw(); }
    if (b.dataset.cp) { const d = days[+b.dataset.cp]; days.splice(+b.dataset.cp + 1, 0, { ...JSON.parse(JSON.stringify(d)), id: uid('d'), name: d.name + ' (copie)' }); draw(); }
    if (b.dataset.rm) { if (await confirmBox('Supprimer ce jour ?', 'Supprimer')) { days.splice(+b.dataset.rm, 1); draw(); } }
    if (b.dataset.ed) { await commit(); w.close(); setTimeout(() => editDay(days[+b.dataset.ed].id, rerender), 260); }
  };
  $('#padd', w).onclick = () => { days.push({ id: uid('d'), name: `J${days.length + 1} · Nouvelle séance`, focus: 'Perso', items: [] }); draw(); };
  $('#psave', w).onclick = async () => { await commit(); toast('Programme enregistré'); w.close(); };
  $('#pdup', w).onclick = async () => { await commit(); const copy = { ...JSON.parse(JSON.stringify(P)), id: uid('p'), name: P.name + ' (copie)', archived: new Date().toISOString() }; S.programs.unshift(copy); await kv.set('programs', S.programs); toast('Copie rangée dans Mes programmes'); };
  $('#pregen', w).onclick = async () => {
    if (!S.profile) return toast('Crée d’abord ton profil');
    await commit(); w.close(); setTimeout(() => catalogSheet(rerender), 260);
  };
  $('#pblank', w).onclick = async () => {
    await commit(); await archiveProgram();
    S.program = { id: uid('p'), name: 'Mon programme', created: new Date().toISOString(), startDate: new Date().toISOString().slice(0, 10), weeks: 12, periodize: false, days: [{ id: uid('d'), name: 'J1 · Séance A', focus: 'Perso', items: [] }] };
    await saveProgram(); w.close(); toast('Programme vide créé : ajoute tes exercices');
  };
}

function programsSheet(rerender) {
  const w = sheet(`<h3>📚 Mes programmes</h3><div id="plist"></div>`, { onClose: rerender });
  const draw = () => {
    $('#plist', w).innerHTML = (S.program ? `<div class="edit-item"><div class="eyebrow">Actif</div><b>${esc(S.program.name)}</b><br><small class="muted">${S.program.days.length} jours · ${S.program.weeks || 12} semaines</small></div>` : '') +
      (S.programs.length ? S.programs.map((p, i) => `<div class="edit-item"><b>${esc(p.name)}</b><br><small class="muted">${p.days.length} jours · rangé le ${fmtDate(p.archived || p.created)}</small>
        <div class="row gap"><button class="btn sm grow" data-on="${i}">Activer</button><button class="btn sm ghost grow" data-ren="${i}">Renommer</button><button class="btn sm ghost danger" data-del="${i}">✕</button></div></div>`).join('') : '<p class="muted">Aucun autre programme enregistré. Quand tu régénères ou importes un programme de Claude, l’ancien arrive ici.</p>');
  };
  draw();
  $('#plist', w).onclick = async (e) => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.on) {
      const i = +b.dataset.on, p = S.programs[i];
      S.programs.splice(i, 1);
      if (S.program) S.programs.unshift({ ...S.program, archived: new Date().toISOString() });
      S.program = p; delete S.program.archived;
      if (await confirmBox('Repartir de la semaine 1 aujourd’hui ?', 'Oui, semaine 1')) S.program.startDate = new Date().toISOString().slice(0, 10);
      await kv.set('programs', S.programs); await saveProgram(); toast('Programme activé'); w.close();
    }
    if (b.dataset.ren) { const p = S.programs[+b.dataset.ren]; const n = prompt('Nouveau nom', p.name); if (n) { p.name = n; await kv.set('programs', S.programs); draw(); } }
    if (b.dataset.del) { if (await confirmBox('Supprimer ce programme ?', 'Supprimer')) { S.programs.splice(+b.dataset.del, 1); await kv.set('programs', S.programs); draw(); } }
  };
}

// ————— Catalogue de programmes prédéfinis (selon temps max et jours) —————
function catalogSheet(rerender) {
  if (!S.profile) { toast('Crée d’abord ton profil'); location.hash = '#/profil'; return; }
  const p = S.profile;
  let preset = p.preset || 'hybride', minutes = p.sessionMinutes || 60;
  let tdays = (p.trainingDays?.length ? p.trainingDays : [0, 2, 4]).slice();
  const w = sheet(`<h3>📋 Programmes prédéfinis</h3>
    <p class="muted small">Choisis ton temps maximum et tes jours : chaque séance est calculée pour tenir dedans (échauffement compris).</p>
    <div class="field">Temps max par séance<div class="row gap"><div class="chips grow" id="cmin">${[30, 45, 50, 60, 75, 90].map(m => `<button class="chip ${m === minutes ? 'on' : ''}" data-m="${m}">${m} min</button>`).join('')}</div><label class="mini cminl">ou<input type="number" id="cmini" inputmode="numeric" min="20" max="180" step="5" value="${minutes}"></label></div></div>
    <div class="field">Jours d’entraînement<div class="wdays" id="cdays">${WEEKDAYS.map((d, i) => `<label><input type="checkbox" value="${i}" ${tdays.includes(i) ? 'checked' : ''}><span>${d}</span></label>`).join('')}</div></div>
    <div id="cpresets" class="presets"></div>
    <div id="cprev"></div>
    <button class="btn block" id="cgo">Utiliser ce programme</button>
    <p class="muted small">Ton programme actuel est rangé dans « Mes programmes ». Tout reste modifiable ensuite.</p>`, { onClose: rerender });
  let prog;
  const draw = () => {
    $('#cpresets', w).innerHTML = Object.entries(PRESETS).map(([k, v]) => `<button class="preset ${k === preset ? 'on' : ''}" data-p="${k}"><b>${v.label}</b><small>${v.desc}</small></button>`).join('');
    if (!tdays.length) { $('#cprev', w).innerHTML = '<p class="muted">Coche au moins un jour.</p>'; return; }
    prog = generateProgram(p, { preset, minutes, trainingDays: tdays });
    $('#cprev', w).innerHTML = `<h3 class="sec">Aperçu · ${tdays.length} séance${tdays.length > 1 ? 's' : ''} / semaine</h3>` + prog.days.map(d => `<div class="edit-item"><div class="row between"><b>${esc(d.name)}</b><span class="tag">≈ ${dayMinutes(d)} min max</span></div><small class="muted">${d.items.map(it => esc(exById(it.exId).name)).join(' · ')}</small></div>`).join('');
  };
  draw();
  $('#cmin', w).onclick = (e) => { const b = e.target.closest('[data-m]'); if (!b) return; minutes = +b.dataset.m; $('#cmini', w).value = minutes; $$('#cmin .chip', w).forEach(c => c.classList.toggle('on', c === b)); draw(); };
  $('#cmini', w).onchange = (e) => { minutes = Math.min(180, Math.max(20, Math.round((+e.target.value || 60) / 5) * 5)); e.target.value = minutes; $$('#cmin .chip', w).forEach(c => c.classList.toggle('on', +c.dataset.m === minutes)); draw(); };
  $('#cdays', w).onchange = () => { tdays = $$('#cdays input:checked', w).map(x => +x.value); draw(); };
  $('#cpresets', w).onclick = (e) => { const b = e.target.closest('[data-p]'); if (!b) return; preset = b.dataset.p; draw(); };
  $('#cgo', w).onclick = async () => {
    if (!prog) return;
    await archiveProgram();
    S.program = prog; await saveProgram();
    Object.assign(S.profile, { preset, sessionMinutes: minutes, trainingDays: tdays, days: tdays.length }); await kv.set('profile', S.profile);
    toast('Programme activé 💪'); w.close();
  };
}

// ————— Sélecteur d'exercice —————
export function pickExercise(onPick) {
  const all = () => [...EXERCISES, ...S.custom];
  const w = sheet(`<h3>Choisir un exercice</h3>
    <input class="search" id="exq" placeholder="Rechercher…" autocomplete="off">
    <div class="chips" id="exm"><button class="chip on" data-m="">Tous</button>${MUSCLES.map(m => `<button class="chip" data-m="${m}">${m}</button>`).join('')}</div>
    <div id="exr" class="pick-list"></div>
    <details class="custom"><summary>+ Créer un exercice</summary>
      <label class="field">Nom<input id="cxn"></label>
      <div class="grid2"><label class="field">Muscle<select id="cxm">${MUSCLES.map(m => `<option>${m}</option>`).join('')}</select></label>
      <label class="field">Type<select id="cxu"><option value="kg">Charge (kg)</option><option value="pdc">Poids du corps</option><option value="time">Chrono (s)</option><option value="cardio">Cardio (min/km)</option></select></label></div>
      <button class="btn block" id="cxs">Créer</button></details>`);
  let m = '';
  const draw = () => {
    const q = $('#exq', w).value.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '');
    const res = all().filter(e => (!m || e.muscle === m) && e.name.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').includes(q));
    $('#exr', w).innerHTML = res.map(e => `<button class="pick" data-id="${e.id}"><b>${esc(e.name)}</b><small>${esc(e.muscle)}</small></button>`).join('') || '<p class="muted">Aucun résultat</p>';
  };
  draw();
  $('#exq', w).oninput = draw;
  $('#exm', w).onclick = (e) => { const b = e.target.closest('[data-m]'); if (!b) return; m = b.dataset.m; $$('.chip', w).forEach(c => c.classList.toggle('on', c === b)); draw(); };
  $('#exr', w).onclick = (e) => { const b = e.target.closest('[data-id]'); if (!b) return; w.close(); onPick(exById(b.dataset.id)); };
  $('#cxs', w).onclick = async () => {
    const name = $('#cxn', w).value.trim(); if (!name) return;
    const unit = $('#cxu', w).value;
    const ex = { id: uid('x'), name, muscle: $('#cxm', w).value, eq: 'smp', unit, kind: unit === 'cardio' ? 'cardio' : unit === 'time' ? 'core' : 'hyper', inc: unit === 'kg' ? 2.5 : 0, met: 5, custom: true };
    S.custom.push(ex); await kv.set('customExercises', S.custom);
    w.close(); onPick(ex);
  };
}

export function defaultRole(ex) { return ex.kind === 'cardio' ? 'cardio' : ex.kind === 'hiit' ? 'hiit' : ex.kind === 'core' ? 'core' : ex.kind === 'force' ? 'force' : ex.kind === 'iso' ? 'iso' : 'hyper'; }

// ————— Édition d'un jour —————
function editDay(id, rerender) {
  const day = S.program.days.find(d => d.id === id); if (!day) return;
  const w = sheet(`<h3>Modifier la séance</h3><div class="grid2"><label class="mini">Nom<input id="dn" value="${esc(day.name)}"></label><label class="mini">Type / objectif<input id="df" value="${esc(day.focus || '')}" placeholder="ex : Force, Cardio…"></label></div>
    <label class="field">Jour de la semaine<select id="dwd"><option value="">Libre (quand je veux)</option>${WEEKDAY_LONG.map((n, i) => `<option value="${i}" ${day.weekday === i ? 'selected' : ''}>${n}</option>`).join('')}</select></label>
    <div class="dur" id="ddur"></div><div id="items"></div>
    <button class="btn ghost block" id="addx">+ Ajouter un exercice</button>
    <div class="row gap"><button class="btn danger ghost grow" id="deld">Supprimer ce jour</button><button class="btn grow" id="saved">Enregistrer</button></div>`, { onClose: rerender });
  const num = (label, key, it, i, step = 1) => `<label class="mini">${label}<input type="number" inputmode="decimal" step="${step}" data-i="${i}" data-k="${key}" value="${it[key] ?? ''}"></label>`;
  const draw = () => {
    $('#items', w).innerHTML = day.items.map((it, i) => {
      const e = exById(it.exId);
      let f;
      if (it.role === 'cardio') f = num('Minutes', 'minutes', it, i) + num('Zone', 'zone', it, i);
      else if (it.role === 'hiit') f = num('Rounds', 'rounds', it, i) + num('Effort s', 'work', it, i) + num('Récup s', 'restWork', it, i);
      else if (it.secs) f = num('Séries', 'sets', it, i) + num('Secondes', 'secs', it, i) + num('Repos s', 'rest', it, i, 15);
      else f = num('Séries', 'sets', it, i) + num('Reps min', 'repMin', it, i) + num('Reps max', 'repMax', it, i) + num('Repos s', 'rest', it, i, 15);
      return `<div class="edit-item"><div class="row between"><b>${esc(e.name)}</b><span class="row">
        <button class="icon-btn sm" data-mv="-1" data-i="${i}" aria-label="Monter">↑</button><button class="icon-btn sm" data-mv="1" data-i="${i}" aria-label="Descendre">↓</button>
        <button class="icon-btn sm" data-sw="${i}" aria-label="Remplacer">⇄</button><button class="icon-btn sm danger" data-rm="${i}" aria-label="Retirer">✕</button></span></div>
        <div class="row gap wrap">${f}<label class="mini">Type<select data-i="${i}" data-k="role">${Object.entries(ROLE_LABEL).map(([k, v]) => `<option value="${k}" ${k === it.role ? 'selected' : ''}>${v}</option>`).join('')}</select></label></div></div>`;
    }).join('') || '<p class="muted">Aucun exercice.</p>';
  };
  const _draw = draw; const drawAll = () => { _draw(); dur(); }; const dur = () => { const per = S.program.periodize !== false; const m = dayMinutes(day, per); const lim = S.program.minutes || S.profile?.sessionMinutes; $('#ddur', w).innerHTML = `⏱ Durée estimée : <b>${m} min</b>${per ? ' (semaine la plus chargée)' : ''}${lim ? ` / ${lim} min max` : ''}${lim && m > lim + 2 ? ` · <span class="warn">trop long</span> <button class="btn sm" id="dfit">Ajuster à ${lim} min</button>` : ''}`; const f = $('#dfit', w); if (f) f.onclick = () => { fitDayToTime(day, lim, S.profile?.goal, per); drawAll(); toast(`Séance ajustée à ${lim} min max`); }; };
  drawAll();
  $('#items', w).addEventListener('change', (e) => {
    const t = e.target; if (!t.dataset.k) return;
    const it = day.items[+t.dataset.i];
    if (t.dataset.k === 'role') { const n = makeItem(exById(it.exId), t.value); day.items[+t.dataset.i] = n; drawAll(); return; }
    it[t.dataset.k] = t.value === '' ? undefined : +t.value; dur();
  });
  $('#items', w).addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    const i = +b.dataset.i;
    if (b.dataset.mv) { const j = i + +b.dataset.mv; if (j < 0 || j >= day.items.length) return; [day.items[i], day.items[j]] = [day.items[j], day.items[i]]; drawAll(); }
    if (b.dataset.rm !== undefined) { day.items.splice(+b.dataset.rm, 1); drawAll(); }
    if (b.dataset.sw !== undefined) { const k = +b.dataset.sw; const apply = (ex) => { const old = day.items[k]; const n = makeItem(ex, defaultRole(ex)); if (old.sets && n.sets) Object.assign(n, { sets: old.sets, rest: old.rest }); day.items[k] = n; drawAll(); };
      const s2 = exInfoSheet(day.items[k].exId, apply); s2.querySelector('.sheet').insertAdjacentHTML('beforeend', '<button class="btn ghost block" data-other>🔍 Autre exercice…</button>'); s2.querySelector('[data-other]').onclick = () => { s2.close(); pickExercise(apply); }; return; }
    if (false) pickExercise(ex => { const old = day.items[+b.dataset.sw]; const n = makeItem(ex, defaultRole(ex)); if (old.sets && n.sets) Object.assign(n, { sets: old.sets, rest: old.rest }); day.items[+b.dataset.sw] = n; drawAll(); });
  });
  $('#addx', w).onclick = () => pickExercise(ex => { day.items.push(makeItem(ex, defaultRole(ex))); drawAll(); });
  $('#saved', w).onclick = async () => { day.name = $('#dn', w).value; day.focus = $('#df', w).value; day.weekday = $('#dwd', w).value === '' ? null : +$('#dwd', w).value; await saveProgram(); toast('Séance enregistrée'); w.close(); };
  $('#deld', w).onclick = async () => { if (!(await confirmBox('Supprimer ce jour du programme ?', 'Supprimer'))) return; S.program.days = S.program.days.filter(d => d.id !== id); await saveProgram(); w.close(); };
}

// ————— Séance en direct —————
function buildEx(it, list) {
  const ex = exById(it.exId);
  const last = lastPerf(it.exId, list);
  const sug = suggest(it, last, ex);
  const o = { exId: it.exId, role: it.role, target: it, last: lastText(last), sug };
  if (it.role === 'cardio') o.cardio = { minutes: it.minutes || '', km: '', hr: '', kcal: '', done: false };
  else if (it.role === 'hiit') o.hiit = { rounds: it.rounds || 8, work: it.work || 30, restWork: it.restWork || 90, done: 0 };
  else o.sets = Array.from({ length: it.sets || 3 }, () => it.secs ? { secs: sug?.secs || it.secs, done: false } : { w: sug?.w ?? '', r: sug?.r ?? '', done: false });
  return o;
}

async function startSession(dayId) {
  if (S.active && !(await confirmBox('Une séance est déjà en cours. La remplacer ?', 'Remplacer'))) { location.hash = '#/seance'; return; }
  unlockAudio();
  const list = await allSessions();
  const info = weekInfo(S.program);
  const day = dayId ? S.program.days.find(d => d.id === dayId) : null;
  S.active = {
    id: uid('s'), dayId, name: day ? day.name : 'Séance libre', start: Date.now(), week: info.week, phase: info.phase,
    exercises: day ? day.items.map(it => buildEx(applyBlock(it, info), list)) : [], note: '',
  };
  await saveActive();
  location.hash = '#/seance';
}

// Séance construite à la volée (rattrapage, séance combinée)
export async function startCustom(name, items, dayIds = []) {
  if (S.active && !(await confirmBox('Une séance est déjà en cours. La remplacer ?', 'Remplacer'))) { location.hash = '#/seance'; return; }
  unlockAudio();
  const list = await allSessions();
  const info = weekInfo(S.program);
  S.active = { id: uid('s'), dayId: dayIds[0] || null, dayIds, name, start: Date.now(), week: info.week, phase: info.phase, exercises: items.map(it => buildEx(applyBlock(it, info), list)), note: '' };
  await saveActive();
  location.hash = '#/seance';
}

let tick;
export async function renderSession(view) {
  const a = S.active;
  if (!a) { view.innerHTML = `<section class="card hero"><h2>Aucune séance en cours</h2><a class="btn" href="#/entrainement">Choisir une séance</a></section>`; return; }
  requestWakeLock();
  view.innerHTML = `
  <section class="card sess-head">
    <div class="row between"><div><div class="eyebrow">Semaine ${a.week || '-'} · ${esc(a.phase || '')}</div><h2>${esc(a.name)}</h2></div>
      <div class="clock" id="elapsed">0:00</div></div>
    <div class="row gap wrap">
      <button class="chip hrchip" data-act="hr">${hr.device ? `❤ <b id="bpm">${hr.bpm ?? '…'}</b> bpm` : '❤ Connecter cardio'}</button>
      <span class="chip" id="sprog"></span>
      <button class="chip" data-act="chrono">⏱ Chrono</button>
    </div>
  </section>
  ${a.exercises.map((x, i) => exCard(x, i)).join('')}
  <button class="btn ghost block" data-act="add-ex">+ Ajouter un exercice</button>
  <label class="field">Notes de séance<textarea data-k="note" rows="2" placeholder="Sensations, douleurs, énergie…">${esc(a.note || '')}</textarea></label>
  <div class="row gap"><button class="btn ghost danger grow" data-act="cancel">Abandonner</button><button class="btn grow" data-act="finish">Terminer la séance</button></div>`;
  updateProgress();
  clearInterval(tick);
  tick = setInterval(() => { const el = $('#elapsed'); if (!el) return clearInterval(tick); el.textContent = fmtTime((Date.now() - a.start) / 1000); }, 1000);
  hr.listeners.clear();
  hr.listeners.add(b => { const el = $('#bpm'); if (el) el.textContent = b ?? '—'; });
}

function exCard(x, i) {
  const e = exById(x.exId), t = x.target;
  const head = `<div class="row between"><div><h3>${esc(e.name)}</h3><div class="muted">${esc(e.muscle)} · ${ROLE_LABEL[x.role] || ''} · ${prescription(t)}</div></div>
    <span class="row"><button class="icon-btn" data-act="exinfo" data-i="${i}" aria-label="Technique et équivalents">ⓘ</button><button class="icon-btn" data-act="ex-menu" data-i="${i}" aria-label="Options" style="margin-left:6px">⋯</button></span></div>
    ${x.last ? `<div class="last">${esc(x.last)}</div>` : ''}${x.sug?.msg ? `<div class="sug">→ ${esc(x.sug.msg)}</div>` : ''}${t.note ? `<div class="sug warn">${esc(t.note)}</div>` : ''}`;
  if (x.cardio) {
    const c = x.cardio;
    return `<section class="card ex ${c.done ? 'all-done' : ''}">${head}
      <div class="grid4"><label class="mini">Minutes<input type="number" inputmode="decimal" data-i="${i}" data-c="minutes" value="${c.minutes}"></label>
      <label class="mini">Km<input type="number" inputmode="decimal" step="0.01" data-i="${i}" data-c="km" value="${c.km}"></label>
      <label class="mini">FC moy.<input type="number" inputmode="numeric" data-i="${i}" data-c="hr" value="${c.hr}"></label>
      <label class="mini">Kcal<input type="number" inputmode="numeric" data-i="${i}" data-c="kcal" value="${c.kcal}"></label></div>
      <div class="row gap"><button class="btn ghost grow" data-act="cardio-timer" data-i="${i}">⏱ Chrono ${t.minutes || ''} min</button><button class="btn grow ${c.done ? 'ok' : ''}" data-act="cardio-done" data-i="${i}">${c.done ? '✓ Fait' : 'Valider'}</button></div></section>`;
  }
  if (x.hiit) {
    const h = x.hiit;
    return `<section class="card ex ${h.done >= h.rounds ? 'all-done' : ''}">${head}
      <div class="grid3"><label class="mini">Rounds<input type="number" data-i="${i}" data-h="rounds" value="${h.rounds}"></label>
      <label class="mini">Effort (s)<input type="number" data-i="${i}" data-h="work" value="${h.work}"></label>
      <label class="mini">Récup (s)<input type="number" data-i="${i}" data-h="restWork" value="${h.restWork}"></label></div>
      <div class="row gap"><span class="chip">${h.done} / ${h.rounds} faits</span><button class="btn grow" data-act="hiit" data-i="${i}">▶ Lancer le minuteur</button></div></section>`;
  }
  const unit = e.unit;
  const rows = x.sets.map((s, j) => s.secs !== undefined
    ? `<div class="set ${s.done ? 'done' : ''}"><span class="n">${j + 1}</span><label class="mini grow">Secondes<input type="number" inputmode="numeric" data-i="${i}" data-j="${j}" data-f="secs" value="${s.secs}"></label>
        <button class="icon-btn" data-act="hold" data-i="${i}" data-j="${j}" aria-label="Chrono">⏱</button><button class="check" data-act="set" data-i="${i}" data-j="${j}" aria-label="Valider la série">✓</button></div>`
    : `<div class="set ${s.done ? 'done' : ''}"><span class="n">${j + 1}</span>
        <label class="mini grow">${unit === 'pdc' ? 'Lest kg' : 'kg'}<input type="number" inputmode="decimal" step="0.5" data-i="${i}" data-j="${j}" data-f="w" value="${s.w}" placeholder="${unit === 'pdc' ? '0' : '—'}"></label>
        <label class="mini grow">Reps<input type="number" inputmode="numeric" data-i="${i}" data-j="${j}" data-f="r" value="${s.r}" placeholder="${t.repMin || ''}–${t.repMax || ''}"></label>${s.done && j > 0 && x.sets[j - 1].at && s.at ? `<small class="rr" title="Temps entre les 2 séries">${fmtTime((s.at - x.sets[j - 1].at) / 1000)}</small>` : ''}
        <button class="check" data-act="set" data-i="${i}" data-j="${j}" aria-label="Valider la série">✓</button></div>`).join('');
  const allDone = x.sets.length && x.sets.every(s => s.done);
  return `<section class="card ex ${allDone ? 'all-done' : ''}">${head}<div class="sets">${rows}</div>
    <div class="row gap"><button class="btn ghost sm grow" data-act="add-set" data-i="${i}">+ Série</button><button class="btn ghost sm grow" data-act="rest" data-i="${i}">⏱ Repos ${fmtTime(t.rest || 90)}</button></div></section>`;
}

function updateProgress() {
  const a = S.active; if (!a) return;
  let done = 0, total = 0;
  for (const x of a.exercises) {
    if (x.sets) { total += x.sets.length; done += x.sets.filter(s => s.done).length; }
    if (x.cardio) { total++; if (x.cardio.done) done++; }
    if (x.hiit) { total++; if (x.hiit.done >= x.hiit.rounds) done++; }
  }
  const el = $('#sprog'); if (el) el.textContent = `${done} / ${total} validés`;
}

export async function onSessionInput(el) {
  const a = S.active; if (!a) return;
  if (el.dataset.k === 'note') { a.note = el.value; return saveActive(); }
  const x = a.exercises[+el.dataset.i]; if (!x) return;
  const v = el.value === '' ? '' : +el.value;
  if (el.dataset.f) {
    const j = +el.dataset.j; x.sets[j][el.dataset.f] = v;
    // propage la charge aux séries suivantes non validées
    if (el.dataset.f === 'w') for (let k = j + 1; k < x.sets.length; k++) if (!x.sets[k].done) { x.sets[k].w = v; const inp = document.querySelector(`[data-i="${el.dataset.i}"][data-j="${k}"][data-f="w"]`); if (inp) inp.value = v; }
  }
  if (el.dataset.c) x.cardio[el.dataset.c] = v;
  if (el.dataset.h) x.hiit[el.dataset.h] = v;
  await saveActive();
}

export async function onSessionAction(act, el, rerender) {
  const a = S.active; if (!a) return;
  const i = +el.dataset.i, x = a.exercises[i];
  if (act === 'set') {
    const s = x.sets[+el.dataset.j];
    s.done = !s.done;
    if (s.done && s.secs === undefined && (s.r === '' || s.r == null)) s.r = x.target.repMax || x.target.repMin || 10;
    if (s.done) { s.at = Date.now(); if (S.settings.restAuto !== false) startRest(x.target.rest || 90, exById(x.exId).name); }
    await saveActive(); refreshCard(i); updateProgress();
  }
  if (act === 'add-set') { const l = x.sets[x.sets.length - 1] || {}; x.sets.push(l.secs !== undefined ? { secs: l.secs, done: false } : { w: l.w ?? '', r: l.r ?? '', done: false }); await saveActive(); refreshCard(i); updateProgress(); }
  if (act === 'chrono') return chronoSheet();
  if (act === 'rest') startRest(x.target.rest || 90, exById(x.exId).name);
  if (act === 'hold') { const s = x.sets[+el.dataset.j]; intervalTimer({ rounds: 1, work: +s.secs || 30, restWork: 0, title: exById(x.exId).name, onRound: async () => { s.done = true; s.at = Date.now(); await saveActive(); refreshCard(i); updateProgress(); startRest(x.target.rest || 45, exById(x.exId).name); } }); }
  if (act === 'hiit') intervalTimer({ rounds: +x.hiit.rounds, work: +x.hiit.work, restWork: +x.hiit.restWork, title: exById(x.exId).name, start: x.hiit.done, onRound: async (n) => { x.hiit.done = n; await saveActive(); refreshCard(i); updateProgress(); } });
  if (act === 'cardio-done') { x.cardio.done = !x.cardio.done; if (x.cardio.done && !x.cardio.minutes) x.cardio.minutes = x.target.minutes; await saveActive(); refreshCard(i); updateProgress(); }
  if (act === 'cardio-timer') intervalTimer({ rounds: 1, work: (x.target.minutes || 30) * 60, restWork: 0, title: exById(x.exId).name + ' — zone ' + (x.target.zone || 2), onRound: async () => { x.cardio.minutes = x.target.minutes; x.cardio.done = true; await saveActive(); refreshCard(i); updateProgress(); } });
  if (act === 'add-ex') pickExercise(async ex => { const it = makeItem(ex, defaultRole(ex)); a.exercises.push(buildEx(it, await allSessions())); await saveActive(); rerender(); });
  if (act === 'ex-menu') exMenu(i, rerender);
  if (act === 'exinfo') exInfoSheet(x.exId, (ex) => swapEx(i, ex, rerender));
  if (act === 'hr') connectHR(rerender);
  if (act === 'cancel') { if (await confirmBox('Abandonner la séance ? Rien ne sera enregistré.', 'Abandonner')) { S.active = null; await kv.del('active'); stopRest(); location.hash = '#/entrainement'; } }
  if (act === 'finish') finishSession();
}

function refreshCard(i) {
  const cards = $$('#view section.card.ex');
  const c = cards[i]; if (!c) return;
  const tmp = document.createElement('div'); tmp.innerHTML = exCard(S.active.exercises[i], i);
  c.replaceWith(tmp.firstElementChild);
}

async function swapEx(i, ex, rerender) {
  const a = S.active, x = a.exercises[i];
  const it = { ...x.target, ...makeItem(ex, defaultRole(ex)) };
  if (x.target.sets && it.sets) { it.sets = x.target.sets; it.repMin = x.target.repMin; it.repMax = x.target.repMax; it.rest = x.target.rest; }
  a.exercises[i] = buildEx(it, await allSessions()); await saveActive(); rerender();
  toast(`Remplacé par ${ex.name}`);
}

function exMenu(i, rerender) {
  const a = S.active, x = a.exercises[i];
  const w = sheet(`<h3>${esc(exById(x.exId).name)}</h3>
    <button class="btn ghost block" data-m="alts">⇄ Machine prise ? Voir les équivalents</button>
    <button class="btn ghost block" data-m="swap">🔍 Remplacer par un autre exercice</button>
    <button class="btn ghost block" data-m="up">↑ Monter</button><button class="btn ghost block" data-m="down">↓ Descendre</button>
    ${x.sets ? '<button class="btn ghost block" data-m="rmset">− Retirer la dernière série</button>' : ''}
    <button class="btn ghost danger block" data-m="rm">✕ Retirer de la séance</button>`);
  w.addEventListener('click', async (e) => {
    const m = e.target.closest('[data-m]')?.dataset.m; if (!m) return;
    w.close();
    if (m === 'swap') return pickExercise(ex => swapEx(i, ex, rerender));
    if (m === 'alts') return exInfoSheet(x.exId, (ex) => swapEx(i, ex, rerender));
    if (m === 'up' && i > 0) [a.exercises[i - 1], a.exercises[i]] = [a.exercises[i], a.exercises[i - 1]];
    if (m === 'down' && i < a.exercises.length - 1) [a.exercises[i + 1], a.exercises[i]] = [a.exercises[i], a.exercises[i + 1]];
    if (m === 'rmset') x.sets.pop();
    if (m === 'rm') a.exercises.splice(i, 1);
    await saveActive(); rerender();
  });
}

async function connectHR(rerender) {
  if (hr.device) { if (await confirmBox('Déconnecter le capteur cardio ?', 'Déconnecter')) { hr.disconnect(); rerender(); } return; }
  try { const n = await hr.connect(); toast(`Connecté : ${n}`); rerender(); } catch (e) { if (e.name !== 'NotFoundError') toast(e.message, 5000); }
}

async function finishSession() {
  const a = S.active;
  const minutes = Math.round((Date.now() - a.start) / 60000);
  const list = await allSessions();
  // records
  const prs = [];
  let volume = 0, setsDone = 0;
  for (const x of a.exercises) {
    if (!x.sets) continue;
    const done = x.sets.filter(s => s.done && s.secs === undefined);
    setsDone += x.sets.filter(s => s.done).length;
    for (const s of done) volume += (+s.w || 0) * (+s.r || 0);
    const best = Math.max(0, ...done.map(s => e1rm(+s.w, +s.r)));
    if (!best) continue;
    let prev = 0;
    for (const o of list) for (const ox of o.exercises || []) if (ox.exId === x.exId) for (const s of ox.sets || []) if (s.done) prev = Math.max(prev, e1rm(+s.w, +s.r));
    if (best > prev && prev > 0) prs.push({ name: exById(x.exId).name, val: best, prev });
  }
  const hrStats = hr.stats(a.start);
  const draft = { id: a.id, date: new Date(a.start).toISOString(), name: a.name, dayId: a.dayId, dayIds: a.dayIds || [], week: a.week, minutes, volume: Math.round(volume), exercises: a.exercises.map(({ last, sug, ...rest }) => rest), note: a.note, avgHr: hrStats?.avg, maxHr: hrStats?.max };
  draft.kcal = sessionKcal(draft, S.profile?.weight);
  const w = sheet(`<h3>Bravo 🔥</h3>
    <div class="stats3"><div><b>${fmtDur(minutes)}</b><small>Durée</small></div><div><b>${setsDone}</b><small>Séries</small></div><div><b>${num(volume / 1000, 2)} t</b><small>Volume</small></div></div>
    <div class="stats3"><div><b>~${draft.kcal}</b><small>kcal dépensées</small></div><div><b>${hrStats ? hrStats.avg : '—'}</b><small>FC moy.</small></div><div><b>${hrStats ? hrStats.max : '—'}</b><small>FC max</small></div></div>
    ${prs.length ? `<div class="prs"><b>🏆 Nouveaux records (1RM estimé)</b>${prs.map(p => `<div>${esc(p.name)} : ${num(p.val)} kg <small>(avant ${num(p.prev)})</small></div>`).join('')}</div>` : ''}
    <label class="field">Difficulté ressentie : <b id="rpev">7</b>/10<input type="range" min="1" max="10" value="7" id="rpe"></label>
    <button class="btn block" id="savesess">Enregistrer</button>`);
  $('#rpe', w).oninput = (e) => { $('#rpev', w).textContent = e.target.value; };
  $('#savesess', w).onclick = async () => {
    draft.rpe = +$('#rpe', w).value;
    await sessions.put(draft); invalidateSessions();
    S.active = null; await kv.del('active'); stopRest(); releaseWakeLock();
    w.close(); toast('Séance enregistrée ✓'); location.hash = '#/progres';
  };
}

async function showSession(id, rerender) {
  const s = await sessions.get(id); if (!s) return;
  const w = sheet(`<h3>${esc(s.name)}</h3><p class="muted">${fmtDate(s.date, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })} · ${fmtDur(s.minutes || 0)}${s.rpe ? ' · ressenti ' + s.rpe + '/10' : ''}${s.avgHr ? ' · FC ' + s.avgHr + ' moy.' : ''}${s.kcal ? ' · ~' + s.kcal + ' kcal' : ''}</p>
    ${(s.exercises || []).map(x => { const e = exById(x.exId);
      if (x.cardio) return `<div class="hist-ex"><b>${esc(e.name)}</b><span>${x.cardio.minutes || 0} min${x.cardio.km ? ' · ' + x.cardio.km + ' km' : ''}${x.cardio.hr ? ' · ' + x.cardio.hr + ' bpm' : ''}</span></div>`;
      if (x.hiit) return `<div class="hist-ex"><b>${esc(e.name)}</b><span>${x.hiit.done} × ${x.hiit.work}s/${x.hiit.restWork}s</span></div>`;
      const d = (x.sets || []).filter(z => z.done); if (!d.length) return '';
      return `<div class="hist-ex"><b>${esc(e.name)}</b><span>${d.map(z => z.secs ? z.secs + ' s' : `${num(z.w || 0)} kg × ${z.r}`).join(' · ')}</span></div>`; }).join('')}
    ${s.note ? `<p class="note">${esc(s.note)}</p>` : ''}
    <button class="btn ghost danger block" id="dels">Supprimer cette séance</button>`);
  $('#dels', w).onclick = async () => { if (!(await confirmBox('Supprimer définitivement cette séance ?', 'Supprimer'))) return; await sessions.del(id); invalidateSessions(); w.close(); rerender(); };
}

// ————— Minuteur de repos (barre flottante) —————
let restInt;
export function startRest(sec, label = '') {
  const bar = $('#restbar');
  S.rest = { end: Date.now() + sec * 1000, total: sec, label };
  bar.hidden = false;
  clearInterval(restInt);
  const upd = () => {
    if (!S.rest) return;
    const left = (S.rest.end - Date.now()) / 1000;
    $('#restleft').textContent = fmtTime(left);
    $('#restlabel').textContent = 'Repos' + (S.rest.label ? ' · ' + S.rest.label : '');
    $('#restfill').style.width = Math.max(0, Math.min(100, (1 - left / S.rest.total) * 100)) + '%';
    const sec = Math.ceil(left);
    if (left > 0 && sec <= 3 && sec !== S.rest.tick) { S.rest.tick = sec; beep(1, false); } // décompte 3-2-1
    if (left <= 0) { beep(3); stopRest(); toast('C’est reparti ! 💥'); }
  };
  upd(); restInt = setInterval(upd, 250);
}
export function stopRest() { clearInterval(restInt); S.rest = null; const b = $('#restbar'); if (b) b.hidden = true; }
export function adjustRest(d) { if (S.rest) { S.rest.end += d * 1000; S.rest.total = Math.max(1, S.rest.total + d); } }

// ————— Chronomètre & minuteur (accessible partout via ⏱) —————
const SW = { start: null, acc: 0, laps: [] };
const swNow = () => SW.acc + (SW.start ? Date.now() - SW.start : 0);
const fmtMs = (ms) => { const t = Math.floor(ms / 100); return `${Math.floor(t / 600)}:${String(Math.floor(t / 10) % 60).padStart(2, '0')}.${t % 10}`; };
export function chronoSheet() {
  unlockAudio();
  let tab = 'cd', custom = S.settings.lastRest || 90;
  const w = sheet(`<h3>⏱ Chrono</h3>
    <div class="seg sm" id="ctabs"><button data-t="cd" class="on">Minuteur de repos</button><button data-t="sw">Chronomètre</button></div>
    <div id="cbody"></div>`, { onClose: () => clearInterval(iv) });
  let iv;
  const draw = () => {
    clearInterval(iv);
    const b = $('#cbody', w);
    if (tab === 'cd') {
      b.innerHTML = `<div class="chips wrapchips">${[30, 45, 60, 75, 90, 120, 150, 180, 240].map(s => `<button class="chip" data-s="${s}">${fmtTime(s)}</button>`).join('')}</div>
        <div class="row gap center-row"><button class="icon-btn" data-adj="-15">−15</button><div class="bigtime" id="cdv">${fmtTime(custom)}</div><button class="icon-btn" data-adj="15">+15</button></div>
        <button class="btn block" id="cdgo">Lancer le repos</button>
        <p class="muted small">Le repos s’affiche en bas de l’écran sur toutes les pages, avec bip et vibration à la fin (décompte 3-2-1).</p>`;
      b.onclick = async (e) => {
        const c = e.target.closest('[data-s]'); if (c) { custom = +c.dataset.s; $('#cdv', w).textContent = fmtTime(custom); }
        const a = e.target.closest('[data-adj]'); if (a) { custom = Math.max(5, custom + +a.dataset.adj); $('#cdv', w).textContent = fmtTime(custom); }
        if (e.target.id === 'cdgo') { S.settings.lastRest = custom; kv.set('settings', S.settings); startRest(custom, 'Minuteur'); w.close(); }
      };
    } else {
      b.innerHTML = `<div class="bigtime sw" id="swv">${fmtMs(swNow())}</div>
        <div class="row gap"><button class="btn grow" id="swgo">${SW.start ? 'Pause' : swNow() ? 'Reprendre' : 'Démarrer'}</button><button class="btn ghost grow" id="swlap" ${SW.start ? '' : 'disabled'}>Tour</button><button class="btn ghost grow" id="swrst">Remise à 0</button></div>
        <div class="table" id="swlaps">${SW.laps.map((l, i) => `<div class="tr"><span>Tour ${i + 1}</span><b>${fmtMs(l - (SW.laps[i - 1] || 0))}</b><small>${fmtMs(l)}</small></div>`).reverse().join('')}</div>`;
      iv = setInterval(() => { const v = $('#swv', w); if (v) v.textContent = fmtMs(swNow()); }, 100);
      $('#swgo', w).onclick = () => { if (SW.start) { SW.acc += Date.now() - SW.start; SW.start = null; } else SW.start = Date.now(); draw(); };
      $('#swlap', w).onclick = () => { SW.laps.push(swNow()); draw(); };
      $('#swrst', w).onclick = () => { SW.start = null; SW.acc = 0; SW.laps = []; draw(); };
    }
  };
  $('#ctabs', w).onclick = (e) => { const b = e.target.closest('[data-t]'); if (!b) return; tab = b.dataset.t; $$('#ctabs button', w).forEach(x => x.classList.toggle('on', x === b)); draw(); };
  draw();
}

// ————— Minuteur d'intervalles plein écran —————
function intervalTimer({ rounds, work, restWork, title, start = 0, onRound }) {
  unlockAudio();
  const ov = document.createElement('div');
  ov.className = 'interval';
  ov.innerHTML = `<div class="iv-title">${esc(title)}</div><div class="iv-phase" id="ivp">Prépare-toi</div><div class="iv-time" id="ivt">0:05</div><div class="iv-round" id="ivr"></div>
    <div class="row gap"><button class="btn ghost grow" id="ivpause">Pause</button><button class="btn ghost grow" id="ivskip">Passer</button><button class="btn danger grow" id="ivstop">Stop</button></div>`;
  document.body.appendChild(ov);
  let round = start, phase = 'prep', end = Date.now() + 5000, paused = null;
  const set = (p, sec) => { phase = p; end = Date.now() + sec * 1000; };
  const next = async () => {
    if (phase === 'prep' || phase === 'rest') { round++; set('work', work); beep(2); }
    else if (phase === 'work') {
      onRound && await onRound(round);
      if (round >= rounds) { beep(4); close(); toast('Terminé ✓'); return; }
      if (restWork > 0) { set('rest', restWork); beep(1); } else { round++; set('work', work); beep(2); }
    }
  };
  const draw = () => {
    if (paused) return;
    const left = (end - Date.now()) / 1000;
    if (left <= 0) { next(); return; }
    if (left <= 3.05 && Math.abs(left - Math.round(left)) < 0.13 && phase !== 'prep') { /* petits tops */ }
    $('#ivt', ov).textContent = fmtTime(Math.ceil(left));
    $('#ivp', ov).textContent = phase === 'work' ? 'EFFORT' : phase === 'rest' ? 'Récupération' : 'Prépare-toi';
    ov.dataset.phase = phase;
    $('#ivr', ov).textContent = rounds > 1 ? `Round ${Math.max(1, round)} / ${rounds}` : '';
  };
  const int = setInterval(draw, 200); draw();
  const close = () => { clearInterval(int); ov.remove(); };
  $('#ivstop', ov).onclick = close;
  $('#ivskip', ov).onclick = () => next();
  $('#ivpause', ov).onclick = (e) => {
    if (paused) { end = Date.now() + paused; paused = null; e.target.textContent = 'Pause'; }
    else { paused = end - Date.now(); e.target.textContent = 'Reprendre'; }
  };
}

// ————— Écran allumé pendant la séance —————
let wakeLock;
async function requestWakeLock() { try { if ('wakeLock' in navigator && !wakeLock) { wakeLock = await navigator.wakeLock.request('screen'); wakeLock.addEventListener('release', () => { wakeLock = null; }); } } catch (e) { } }
function releaseWakeLock() { try { wakeLock?.release(); } catch (e) { } wakeLock = null; }
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && S.active) requestWakeLock(); });
