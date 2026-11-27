// FORGE — progrès : performances, corps (poids, mensurations, % MG), photos avant/après.
import { S, esc, $, $$, exById, toast, sheet, confirmBox, fmtDate, num, e1rm, today, navyBF, dayKey } from './ui.js';
import { body, photos, uid, kv } from './db.js';
import { lineChart, barChart, bindCharts } from './charts.js';
import { allSessions } from './train.js';
import { bfGoalCard, reviewHtml, onFeatureAction } from './features.js';

let tab = 'perf', exSel = null, bodyMetric = 'weight';
export const setProgressTab = (t) => { tab = t; };

export async function renderProgress(view) {
  view.innerHTML = `<div class="seg" role="tablist">${[['perf', 'Perfs'], ['bilan', 'Bilan'], ['corps', 'Corps'], ['photos', 'Photos']].map(([k, l]) => `<button class="${tab === k ? 'on' : ''}" data-act="ptab" data-t="${k}">${l}</button>`).join('')}</div><div id="ptab"></div>`;
  const el = $('#ptab', view);
  if (tab === 'perf') await perf(el);
  if (tab === 'corps') await corps(el);
  if (tab === 'bilan') el.innerHTML = await reviewHtml();
  if (tab === 'photos') await gallery(el);
  bindCharts(view);
}

function weekStart(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x; }

function healthCharts() {
  const h = Object.entries(S.health || {}).sort((a, b) => a[0].localeCompare(b[0])).slice(-60);
  if (!h.length) return '';
  const steps = h.filter(([, v]) => v.steps != null).map(([d, v]) => ({ x: d, y: v.steps }));
  const rhr = h.filter(([, v]) => v.rhr != null).map(([d, v]) => ({ x: d, y: v.rhr }));
  const act = h.filter(([, v]) => v.active != null).map(([d, v]) => ({ x: d, y: v.active }));
  return `${steps.length ? `<section class="card"><h3>⌚ Pas par jour</h3>${lineChart(steps, { unit: 'pas', area: true })}</section>` : ''}
    ${act.length ? `<section class="card"><h3>⌚ Calories actives (montre)</h3>${lineChart(act, { unit: 'kcal' })}</section>` : ''}
    ${rhr.length ? `<section class="card"><h3>❤ FC au repos</h3>${lineChart(rhr, { unit: 'bpm', area: false })}<p class="muted small">Une FC de repos qui baisse = cardio qui progresse. Une hausse soudaine de 5+ bpm = fatigue : allège la séance.</p></section>` : ''}`;
}

async function perf(el) {
  const list = await allSessions();
  if (!list.length) { el.innerHTML = `<section class="card hero"><h2>Rien à afficher… pour l’instant</h2><p>Termine ta première séance pour voir tes courbes de progression.</p></section>${healthCharts()}`; return; }
  const now = Date.now();
  const last30 = list.filter(s => now - new Date(s.date) < 30 * 86400000);
  // semaines
  const weeks = [];
  for (let i = 11; i >= 0; i--) { const ws = weekStart(new Date(now - i * 7 * 86400000)); weeks.push({ ws, label: ws.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }), n: 0, vol: 0, cardio: 0 }); }
  for (const s of list) {
    const ws = weekStart(new Date(s.date)).getTime();
    const w = weeks.find(x => x.ws.getTime() === ws); if (!w) continue;
    w.n++; w.vol += s.volume || 0;
    for (const x of s.exercises || []) { if (x.cardio?.done || x.cardio?.minutes) w.cardio += +x.cardio.minutes || 0; if (x.hiit) w.cardio += Math.round((x.hiit.done || 0) * ((+x.hiit.work || 0) + (+x.hiit.restWork || 0)) / 60); }
  }
  // série de semaines actives
  let streak = 0; for (let i = weeks.length - 1; i >= 0; i--) { if (weeks[i].n > 0) streak++; else if (i !== weeks.length - 1) break; }
  // records & séries e1RM
  const byEx = {};
  for (const s of [...list].reverse()) for (const x of s.exercises || []) {
    const d = (x.sets || []).filter(z => z.done && +z.w && +z.r);
    if (!d.length) continue;
    const best = Math.max(...d.map(z => e1rm(+z.w, +z.r)));
    const top = d.reduce((a, z) => (+z.w > +a.w ? z : a), d[0]);
    (byEx[x.exId] ||= []).push({ x: s.date, y: Math.round(best * 10) / 10, label: `${num(top.w)} kg × ${top.r}` });
  }
  const exIds = Object.keys(byEx).sort((a, b) => byEx[b].length - byEx[a].length);
  if (!exSel || !byEx[exSel]) exSel = exIds[0];
  const records = exIds.map(id => ({ id, best: Math.max(...byEx[id].map(p => p.y)), first: byEx[id][0].y })).sort((a, b) => b.best - a.best);

  el.innerHTML = `
  <div class="stats4">
    <div class="stat"><b>${last30.length}</b><small>séances / 30 j</small></div>
    <div class="stat"><b>${streak}</b><small>sem. d’affilée</small></div>
    <div class="stat"><b>${num(last30.reduce((a, s) => a + (s.minutes || 0), 0) / 60, 1)} h</b><small>entraînement / 30 j</small></div>
    <div class="stat"><b>${num(last30.reduce((a, s) => a + (s.kcal || 0), 0) / 1000, 1)}k</b><small>kcal brûlées / 30 j</small></div>
  </div>
  ${exIds.length ? `<section class="card"><h3>Force — 1RM estimé</h3>
    <select class="select" data-act="exsel">${exIds.map(id => `<option value="${id}" ${id === exSel ? 'selected' : ''}>${esc(exById(id).name)}</option>`).join('')}</select>
    ${lineChart(byEx[exSel], { unit: 'kg' })}
    <p class="muted small">1RM estimé (formule d’Epley) à partir de ta meilleure série de chaque séance.</p></section>` : ''}
  <section class="card"><h3>Volume soulevé par semaine</h3>${barChart(weeks.map(w => ({ label: w.label, y: Math.round(w.vol / 100) / 10 })), { unit: 't' })}</section>
  <section class="card"><h3>Minutes de cardio par semaine</h3>${barChart(weeks.map(w => ({ label: w.label, y: w.cardio })), { unit: 'min' })}</section>
  <section class="card"><h3>Séances par semaine</h3>${barChart(weeks.map(w => ({ label: w.label, y: w.n })), { unit: 'séances' })}</section>
  ${healthCharts()}
  ${records.length ? `<section class="card"><h3>🏆 Records</h3><div class="table">${records.map(r => `<div class="tr"><span>${esc(exById(r.id).name)}</span><b>${num(r.best)} kg</b><small class="${r.best > r.first ? 'up' : ''}">${r.best > r.first ? '+' + num(r.best - r.first) : '='}</small></div>`).join('')}</div></section>` : ''}`;
}

const METRICS = [['weight', 'Poids', 'kg'], ['bf', '% masse grasse', '%'], ['lean', 'Masse maigre', 'kg'], ['waist', 'Tour de taille', 'cm'], ['chest', 'Poitrine', 'cm'], ['arm', 'Bras', 'cm'], ['thigh', 'Cuisse', 'cm'], ['hip', 'Hanches', 'cm']];

async function corps(el) {
  const p = S.profile || {};
  const entries = (await body.all()).sort((a, b) => a.date.localeCompare(b.date));
  const last = entries[entries.length - 1] || {};
  const first = entries[0] || {};
  const pts = entries.filter(e => e[bodyMetric] != null && e[bodyMetric] !== '').map(e => ({ x: e.date, y: +e[bodyMetric] }));
  const m = METRICS.find(x => x[0] === bodyMetric);
  const goalW = +p.goalWeight, goalBF = +p.goalBF;
  const prog = (cur, start, goal) => (!cur || !start || !goal || start === goal) ? null : Math.max(0, Math.min(100, ((start - cur) / (start - goal)) * 100));
  const pw = prog(+last.weight, +first.weight, goalW), pb = prog(+last.bf, +first.bf, goalBF);
  el.innerHTML = `
  <section class="card">
    <div class="row between"><h3>Mon corps sur mesure</h3><button class="btn sm" data-act="body-add">+ Mesure</button></div>
    <div class="stats3">
      <div><b>${num(last.weight)} kg</b><small>Poids</small></div>
      <div><b>${last.bf ? num(last.bf) + ' %' : '—'}</b><small>Masse grasse</small></div>
      <div><b>${last.lean ? num(last.lean) + ' kg' : '—'}</b><small>Masse maigre</small></div>
    </div>
    ${goalW ? `<div class="goal"><span>Objectif poids : ${num(goalW)} kg</span><div class="pbar"><i style="width:${pw ?? 0}%"></i></div></div>` : ''}
    ${goalBF ? `<div class="goal"><span>Objectif masse grasse : ${num(goalBF)} %</span><div class="pbar"><i style="width:${pb ?? 0}%"></i></div></div>` : ''}
    ${!goalW && !goalBF ? '<p class="muted small">Fixe un poids et un % de masse grasse cibles dans ton profil pour suivre ta progression vers ton corps idéal.</p>' : ''}
  </section>
  ${bfGoalCard(entries)}
  <section class="card"><div class="chips">${METRICS.map(([k, l]) => `<button class="chip ${k === bodyMetric ? 'on' : ''}" data-act="bmetric" data-m="${k}">${l}</button>`).join('')}</div>
    ${lineChart(pts, { unit: m[2] })}</section>
  <section class="card"><h3>Historique des mesures</h3>
  ${entries.length ? `<div class="table">${[...entries].reverse().map(e => `<button class="tr" data-act="body-edit" data-id="${e.id}"><span>${fmtDate(e.date)}</span><b>${num(e.weight)} kg</b><small>${e.waist ? 'taille ' + num(e.waist) + ' cm' : ''}${e.bf ? ' · ' + num(e.bf) + ' %' : ''}</small></button>`).join('')}</div>` : '<p class="muted">Ajoute ta première mesure (poids + tour de taille au minimum).</p>'}
  </section>`;
}

function bodyForm(entry, rerender) {
  const p = S.profile || {};
  const e = entry || { id: uid('b'), date: today(), weight: p.weight };
  const f = (k, l, step = 0.1) => `<label class="mini">${l}<input type="number" inputmode="decimal" step="${step}" name="${k}" value="${e[k] ?? ''}"></label>`;
  const w = sheet(`<h3>${entry ? 'Modifier' : 'Nouvelle'} mesure</h3>
    <label class="field">Date<input type="date" name="date" value="${e.date}"></label>
    <div class="grid3">${f('weight', 'Poids kg')}${f('neck', 'Cou cm')}${f('waist', 'Taille (nombril) cm')}${f('hip', 'Hanches cm')}${f('chest', 'Poitrine cm')}${f('arm', 'Bras cm')}${f('thigh', 'Cuisse cm')}${f('bfManual', '% MG (balance)')}</div>
    <p class="muted small" id="bfcalc"></p>
    <div class="row gap">${entry ? '<button class="btn ghost danger grow" id="bdel">Supprimer</button>' : ''}<button class="btn grow" id="bsave">Enregistrer</button></div>`);
  const read = () => { const o = { ...e }; $$('input', w).forEach(i => { o[i.name] = i.type === 'date' ? i.value : (i.value === '' ? null : +i.value); }); return o; };
  const calc = () => {
    const o = read();
    const nb = navyBF(p.sex, p.height, o.neck, o.waist, o.hip);
    $('#bfcalc', w).textContent = o.bfManual ? `% MG retenu : ${num(o.bfManual)} % (balance)` : nb ? `% MG estimé (méthode US Navy) : ${num(nb)} %` : 'Renseigne cou + taille (+ hanches pour les femmes) pour estimer ton % de masse grasse.';
  };
  w.addEventListener('input', calc); calc();
  $('#bsave', w).onclick = async () => {
    const o = read();
    const nb = navyBF(p.sex, p.height, o.neck, o.waist, o.hip);
    o.bf = o.bfManual || (nb ? Math.round(nb * 10) / 10 : null);
    o.lean = o.weight && o.bf ? Math.round(o.weight * (1 - o.bf / 100) * 10) / 10 : null;
    if (!entry) { const same = (await body.all()).find(x => x.date === o.date); if (same) o.id = same.id; } // une mesure par jour
    await body.put(o);
    // le profil suit le dernier poids (pour les calculs caloriques)
    const all = (await body.all()).sort((a, b) => a.date.localeCompare(b.date));
    const lastE = all[all.length - 1];
    if (S.profile && lastE?.weight) { S.profile.weight = lastE.weight; if (lastE.bf) S.profile.bodyfat = lastE.bf; await kv.set('profile', S.profile); }
    w.close(); toast('Mesure enregistrée'); rerender();
  };
  if (entry) $('#bdel', w).onclick = async () => { if (await confirmBox('Supprimer cette mesure ?', 'Supprimer')) { await body.del(e.id); w.close(); rerender(); } };
}

// ————— Photos —————
let compareSel = [];
async function gallery(el) {
  const all = (await photos.all()).sort((a, b) => b.date.localeCompare(a.date));
  for (const p of all) p.url = URL.createObjectURL(p.blob);
  const byDate = {};
  for (const p of all) (byDate[p.date] ||= []).push(p);
  el.innerHTML = `
  <section class="card"><h3>Photos de progression</h3>
    <p class="muted small">Même lumière, même heure (le matin à jeun), mêmes poses : face, profil, dos. Une série toutes les 2 à 4 semaines.</p>
    <div class="row gap wrap">
      <select class="select grow" id="pose"><option value="face">Face</option><option value="profil">Profil</option><option value="dos">Dos</option><option value="autre">Autre</option></select>
      <label class="btn grow">📷 Prendre une photo<input type="file" accept="image/*" capture="user" data-act="photo-add" hidden></label>
      <label class="btn ghost grow">🖼 Depuis la galerie<input type="file" accept="image/*" multiple data-act="photo-add" hidden></label>
    </div>
    ${all.length >= 2 ? `<button class="btn ghost block" data-act="compare-mode">${compareSel.length ? `Comparer (${compareSel.length}/2 sélectionnées)` : '⇆ Comparer avant / après'}</button>` : ''}
  </section>
  ${Object.entries(byDate).map(([d, ps]) => `<h3 class="sec">${fmtDate(d, { day: 'numeric', month: 'long', year: 'numeric' })}</h3>
    <div class="photos">${ps.map(p => `<button class="ph ${compareSel.includes(p.id) ? 'sel' : ''}" data-act="photo" data-id="${p.id}"><img src="${p.url}" alt="Photo ${esc(p.pose)} du ${d}" loading="lazy"><span>${esc(p.pose)}</span></button>`).join('')}</div>`).join('') || '<p class="muted center">Aucune photo pour l’instant.</p>'}`;
}

function compress(file, max = 1600) {
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement('canvas'); c.width = img.width * k; c.height = img.height * k;
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      c.toBlob(b => { URL.revokeObjectURL(img.src); res(b); }, 'image/jpeg', 0.85);
    };
    img.onerror = rej; img.src = URL.createObjectURL(file);
  });
}

async function compareView(ids) {
  const [a, b] = await Promise.all(ids.map(id => photos.get(id)));
  const [older, newer] = a.date <= b.date ? [a, b] : [b, a];
  const ua = URL.createObjectURL(older.blob), ub = URL.createObjectURL(newer.blob);
  const w = sheet(`<h3>Avant / Après</h3><p class="muted">${fmtDate(older.date)} → ${fmtDate(newer.date)}</p>
    <div class="compare"><img src="${ua}" alt="Avant"><div class="after" id="cafter"><img src="${ub}" alt="Après"></div><input type="range" min="0" max="100" value="50" id="cslider" aria-label="Glisser pour comparer"></div>
    <div class="side"><figure><img src="${ua}" alt=""><figcaption>${fmtDate(older.date)}</figcaption></figure><figure><img src="${ub}" alt=""><figcaption>${fmtDate(newer.date)}</figcaption></figure></div>`);
  const upd = () => { $('#cafter', w).style.clipPath = `inset(0 0 0 ${$('#cslider', w).value}%)`; };
  $('#cslider', w).oninput = upd; upd();
}

export async function onProgressAction(act, el, rerender) {
  if (['setbf', 'setgoal', 'review-week'].includes(act)) return onFeatureAction(act, el, rerender);
  if (act === 'ptab') { tab = el.dataset.t; compareSel = []; return rerender(); }
  if (act === 'bmetric') { bodyMetric = el.dataset.m; return rerender(); }
  if (act === 'body-add') return bodyForm(null, rerender);
  if (act === 'body-edit') return bodyForm(await body.get(el.dataset.id), rerender);
  if (act === 'compare-mode') {
    if (compareSel.length === 2) { compareView(compareSel); compareSel = []; return rerender(); }
    toast('Touche 2 photos à comparer'); compareSel = compareSel.length ? compareSel : ['_']; return;
  }
  if (act === 'photo') {
    if (compareSel.length) {
      compareSel = compareSel.filter(x => x !== '_');
      if (compareSel.includes(el.dataset.id)) compareSel = compareSel.filter(x => x !== el.dataset.id); else compareSel.push(el.dataset.id);
      if (compareSel.length === 2) { const ids = compareSel; compareSel = []; compareView(ids); rerender(); return; }
      if (!compareSel.length) compareSel = ['_'];
      el.classList.toggle('sel'); return;
    }
    const p = await photos.get(el.dataset.id);
    const u = URL.createObjectURL(p.blob);
    const w = sheet(`<img class="full" src="${u}" alt="Photo ${esc(p.pose)}"><p class="muted">${fmtDate(p.date)} · ${esc(p.pose)}</p><button class="btn ghost danger block" id="phdel">Supprimer</button>`);
    $('#phdel', w).onclick = async () => { if (await confirmBox('Supprimer cette photo ?', 'Supprimer')) { await photos.del(p.id); w.close(); rerender(); } };
  }
}

export async function onProgressChange(act, el, rerender) {
  if (act === 'exsel') { exSel = el.value; return rerender(); }
  if (act === 'photo-add' && el.files.length) {
    const pose = $('#pose')?.value || 'face';
    for (const f of el.files) {
      const blob = await compress(f);
      const d = f.lastModified && el.files.length > 1 ? dayKey(new Date(f.lastModified).toISOString()) : today();
      await photos.put({ id: uid('ph'), date: d, pose, blob });
    }
    toast('Photo enregistrée sur ton appareil'); rerender();
  }
}
