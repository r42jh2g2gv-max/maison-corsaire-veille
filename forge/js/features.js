// FORGE — objectif de masse grasse, bilan de la semaine, séances manquées.
import { S, esc, $, toast, sheet, today, num, targets, goalOf, GOALS, adaptiveAdvice, fmtDate, exById } from './ui.js';
import { body, food, sessions, kv } from './db.js';
import { weekInfo, applyBlock, fitDayToTime } from './data.js';
import { startCustom, allSessions } from './train.js';

const iso = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
export function weekBounds(offset = 0) {
  const s = new Date(); s.setHours(0, 0, 0, 0); s.setDate(s.getDate() - ((s.getDay() + 6) % 7) + offset * 7);
  const e = new Date(s); e.setDate(s.getDate() + 7);
  return { start: s, end: e, key: iso(s) };
}

// ————— 1. Objectif de masse grasse —————
export function bfGoalCard(entries) {
  const p = S.profile || {};
  const withBf = entries.filter(e => e.bf && e.weight);
  const last = withBf[withBf.length - 1];
  if (!last) return `<section class="card bfgoal"><h3>🎯 Objectif masse grasse</h3><p class="small muted">Ajoute une mesure avec <b>tour de cou</b> et <b>tour de taille</b> (et hanches pour une femme) : FORGE estime ton % de masse grasse et calcule ton poids cible.</p><button class="btn sm" data-act="body-add">+ Mesure</button></section>`;
  const goalBF = +p.goalBF;
  const lean = last.weight * (1 - last.bf / 100);
  if (!goalBF) {
    return `<section class="card bfgoal"><h3>🎯 Objectif masse grasse</h3><p class="small">Tu es à <b>${num(last.bf)} %</b> (${num(lean)} kg de masse maigre). Quel % vises-tu ?</p>
      <div class="chips">${[last.bf - 3, last.bf - 5, last.bf - 8].map(v => Math.max(p.sex === 'f' ? 16 : 8, Math.round(v))).filter((v, i, a) => a.indexOf(v) === i && v < last.bf).map(v => `<button class="chip" data-act="setbf" data-v="${v}">${v} %</button>`).join('')}</div></section>`;
  }
  const target = lean / (1 - goalBF / 100);
  const toLose = last.weight - target;
  if (toLose <= 0.3) return `<section class="card bfgoal done"><h3>🎯 Objectif atteint 🏆</h3><p class="small">Tu es à ${num(last.bf)} % pour un objectif de ${num(goalBF)} %. Passe en <b>Maintien</b> ou fixe un nouvel objectif.</p><div class="chips"><button class="chip" data-act="setgoal" data-g="maintien">Passer en maintien</button><button class="chip" data-act="setbf" data-v="0">Nouvel objectif</button></div></section>`;
  const adv = adaptiveAdvice(p, entries);
  const g = goalOf(p);
  let rate = adv?.ready && adv.slope < -0.05 ? -adv.slope : (g.rate < 0 ? -g.rate / 100 * last.weight : 0);
  const real = adv?.ready && adv.slope < -0.05;
  const weeks = rate ? toLose / rate : null;
  const eta = weeks ? new Date(Date.now() + weeks * 7 * 86400000) : null;
  const pct = Math.max(0, Math.min(100, ((withBf[0].bf - last.bf) / Math.max(0.1, withBf[0].bf - goalBF)) * 100));
  const needCut = g.rate >= 0;
  return `<section class="card bfgoal"><div class="row between"><h3>🎯 Objectif ${num(goalBF)} % de masse grasse</h3><button class="icon-btn sm" data-act="setbf" data-v="0" aria-label="Changer l’objectif">✎</button></div>
    <div class="stats3"><div><b>${num(target)} kg</b><small>poids cible</small></div><div><b>−${num(toLose)} kg</b><small>de gras à perdre</small></div><div><b>${eta ? eta.toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' }) : '—'}</b><small>arrivée estimée</small></div></div>
    <div class="pbar"><i style="width:${pct}%"></i></div>
    <p class="small muted">Calcul à masse maigre constante (${num(lean)} kg) : tu gardes ton muscle, tu perds le gras. ${eta ? `Rythme ${real ? 'réel' : 'prévu'} : −${num(rate, 2)} kg/semaine (${Math.round(weeks)} semaines).` : ''}</p>
    ${needCut ? `<p class="small"><b>Ton objectif actuel (« ${g.short} ») ne fait pas baisser le gras.</b> Pour l’atteindre :</p><div class="chips"><button class="chip on" data-act="setgoal" data-g="seche">Passer en Sèche</button><button class="chip" data-act="setgoal" data-g="recompo">Recompo (plus lent)</button></div>` : ''}
    ${!needCut && weeks > 26 && !['seche', 'perte'].includes(p.goal) ? `<p class="small">À ce rythme il faut plus de 6 mois. Pour accélérer (~${Math.round(toLose / (0.005 * last.weight))} semaines) :</p><div class="chips"><button class="chip on" data-act="setgoal" data-g="seche">Passer en Sèche</button></div>` : ''}
    ${!needCut && real && adv.slope > -0.1 ? '<p class="small">Ton poids stagne : accepte l’ajustement de calories proposé dans Nutrition, ou ajoute 2 × 20 min de marche par semaine.</p>' : ''}
  </section>`;
}

export async function onFeatureAction(act, el, rerender) {
  if (act === 'setbf') {
    if (+el.dataset.v) { S.profile.goalBF = +el.dataset.v; await kv.set('profile', S.profile); toast(`Objectif : ${el.dataset.v} % de masse grasse`); return rerender(); }
    const w = sheet(`<h3>Objectif de masse grasse</h3><label class="field">% visé<input type="number" step="0.5" id="bfv" value="${S.profile.goalBF || ''}"></label><button class="btn block" id="bfok">Enregistrer</button>`, { onClose: rerender });
    $('#bfok', w).onclick = async () => { S.profile.goalBF = +$('#bfv', w).value || null; await kv.set('profile', S.profile); w.close(); };
    return true;
  }
  if (act === 'setgoal') { S.profile.goal = el.dataset.g; await kv.set('profile', S.profile); toast('Objectif : ' + GOALS[el.dataset.g].label + ' (calories mises à jour)'); return rerender(); }
  if (act === 'review-week') { reviewOffset += +el.dataset.d; return rerender(); }
  if (act === 'miss-now') return startMissed(el.dataset.id, null);
  if (act === 'miss-combine') return startMissed(el.dataset.id, el.dataset.today);
  if (act === 'miss-skip') {
    const k = weekBounds().key; S.skip = (await kv.get('skip')) || {}; (S.skip[k] ||= []).push(el.dataset.id); await kv.set('skip', S.skip);
    toast('Séance passée pour cette semaine'); return rerender();
  }
  return false;
}

// ————— 2. Bilan de la semaine —————
let reviewOffset = -1;
export const setReviewOffset = (o) => { reviewOffset = o; };
export async function weekReview(offset = reviewOffset) {
  const { start, end } = weekBounds(offset);
  const inW = (d) => { const t = new Date(d.length === 10 ? d + 'T12:00:00' : d); return t >= start && t < end; };
  const p = S.profile || {};
  const ss = (await sessions.all()).filter(s => inW(s.date));
  const planned = S.program?.days.length || p.days || 0;
  const vol = ss.reduce((a, s) => a + (s.volume || 0), 0);
  let cardio = 0;
  for (const s of ss) for (const x of s.exercises || []) { if (x.cardio) cardio += +x.cardio.minutes || 0; if (x.hiit) cardio += Math.round((x.hiit.done || 0) * ((+x.hiit.work || 0) + (+x.hiit.restWork || 0)) / 60); }
  const rpe = ss.filter(s => s.rpe).map(s => s.rpe);
  const ff = (await food.all()).filter(f => inW(f.date));
  const days = [...new Set(ff.map(f => f.date))];
  const kcal = days.length ? ff.reduce((a, f) => a + (+f.kcal || 0), 0) / days.length : 0;
  const prot = days.length ? ff.reduce((a, f) => a + (+f.p || 0), 0) / days.length : 0;
  const tgt = days.length ? days.reduce((a, d) => a + targets(p, d).kcal, 0) / days.length : targets(p).kcal;
  const tP = targets(p).p;
  const ecarts = new Set(ff.filter(f => f.ecart).map(f => f.date)).size;
  const alc = ff.reduce((a, f) => a + (+f.alc || 0), 0) / 10;
  const bb = await body.all();
  const avgW = (s, e) => { const x = bb.filter(b => b.weight && new Date(b.date + 'T12:00:00') >= s && new Date(b.date + 'T12:00:00') < e); return x.length ? x.reduce((a, b) => a + +b.weight, 0) / x.length : null; };
  const wNow = avgW(start, end), prevS = new Date(start); prevS.setDate(prevS.getDate() - 7);
  const wPrev = avgW(prevS, start);
  const hh = Object.entries(S.health || {}).filter(([d]) => inW(d)).map(([, h]) => h);
  const steps = hh.filter(h => h.steps).length ? hh.reduce((a, h) => a + (+h.steps || 0), 0) / hh.filter(h => h.steps).length : null;
  const g = goalOf(p);
  // conseils
  const tips = [];
  if (planned && ss.length < planned) tips.push(`🏋️ ${ss.length}/${planned} séances : bloque tes créneaux à l’avance${p.sessionMinutes > 45 ? ', ou passe à des séances plus courtes les jours chargés' : ''}. La régularité compte plus que l’intensité.`);
  if (days.length && prot < tP * 0.85) tips.push(`🥩 Protéines : ${Math.round(prot)} g/jour pour ${tP} g visés. Ajoute un skyr, 3 œufs ou une dose de whey par jour.`);
  if (days.length && g.rate < 0 && kcal > tgt + 150) tips.push(`🔥 Tu as mangé en moyenne ${Math.round(kcal - tgt)} kcal de plus que ta cible. Planifie tes repas dans « Menu semaine » pour garder le contrôle.`);
  if (days.length && g.rate > 0 && kcal < tgt - 150) tips.push(`🍚 Pour prendre du muscle, il te manque ~${Math.round(tgt - kcal)} kcal/jour : ajoute une collation (flocons d’avoine, beurre de cacahuète, lait).`);
  if (wNow && wPrev && g.rate < 0 && wNow > wPrev + 0.2) tips.push(`⚖️ Poids moyen en hausse (+${num(wNow - wPrev)} kg). Si ça se répète la semaine prochaine, accepte l’ajustement de calories proposé.`);
  if (ecarts >= 2 || alc > 7) tips.push(`🍻 ${ecarts} jour(s) d’écart${alc ? `, ${num(alc, 1)} unités d’alcool` : ''}. Garde 1 écart par semaine maximum pendant ta phase d’objectif.`);
  if (steps && steps < 7000) tips.push(`🚶 ${Math.round(steps)} pas/jour en moyenne : vise 8 000. 15 min de marche après le repas suffisent.`);
  if (days.length < 4) tips.push('📝 Note tes repas au moins 5 jours par semaine : sans ça, impossible d’ajuster précisément tes calories.');
  if (rpe.length && rpe.reduce((a, b) => a + b, 0) / rpe.length >= 9) tips.push('😮‍💨 Séances très dures (ressenti ≥ 9/10) : dors 7–8 h et garde 1–2 reps en réserve pour progresser sans te cramer.');
  if (!tips.length) tips.push('✅ Semaine solide ! Continue : vise +1 rep ou +2,5 kg sur tes exercices principaux.');
  return { start, ss, planned, vol, cardio, days: days.length, kcal, prot, tgt, tP, ecarts, alc, wNow, wPrev, steps, tips: tips.slice(0, 3) };
}

export async function reviewHtml() {
  const r = await weekReview();
  const label = reviewOffset === 0 ? 'Cette semaine' : reviewOffset === -1 ? 'Semaine dernière' : 'Semaine du ' + fmtDate(r.start.toISOString(), { day: 'numeric', month: 'long' });
  return `<div class="daynav"><button class="icon-btn" data-act="review-week" data-d="-1" aria-label="Semaine précédente">‹</button><b>${label}</b><button class="icon-btn" data-act="review-week" data-d="1" ${reviewOffset >= 0 ? 'disabled' : ''} aria-label="Semaine suivante">›</button></div>
  <section class="card"><h3>📊 Bilan</h3>
    <div class="stats4">
      <div class="stat"><b>${r.ss.length}/${r.planned || '–'}</b><small>séances</small></div>
      <div class="stat"><b>${num(r.vol / 1000, 1)} t</b><small>soulevées</small></div>
      <div class="stat"><b>${r.cardio} min</b><small>cardio</small></div>
      <div class="stat"><b>${r.wNow ? num(r.wNow) + ' kg' : '—'}</b><small>${r.wNow && r.wPrev ? (r.wNow - r.wPrev > 0 ? '+' : '') + num(r.wNow - r.wPrev) + ' kg vs sem. préc.' : 'poids moyen'}</small></div>
      <div class="stat"><b>${r.days ? Math.round(r.kcal) : '—'}</b><small>kcal/jour (cible ${Math.round(r.tgt)})</small></div>
      <div class="stat"><b>${r.days ? Math.round(r.prot) + ' g' : '—'}</b><small>protéines/jour (cible ${r.tP})</small></div>
      <div class="stat"><b>${r.ecarts}</b><small>jour(s) d’écart${r.alc ? ` · ${num(r.alc, 1)} u. alcool` : ''}</small></div>
      <div class="stat"><b>${r.steps ? Math.round(r.steps).toLocaleString('fr-FR') : '—'}</b><small>pas/jour</small></div>
    </div>
  </section>
  <section class="card tip"><h3>🎯 3 priorités pour la semaine prochaine</h3>${r.tips.map(t => `<p>${t}</p>`).join('')}
    <a class="btn ghost block" href="#/coach">🤖 Analyse détaillée par Claude</a></section>`;
}

// ————— 6. Séances manquées —————
export async function missedCard() {
  if (!S.program || !S.program.days.some(d => d.weekday != null)) return '';
  const { start, key } = weekBounds();
  const td = (new Date().getDay() + 6) % 7;
  const list = (await allSessions()).filter(s => new Date(s.date) >= start);
  const done = new Set(list.flatMap(s => [s.dayId, ...(s.dayIds || [])]));
  const skip = ((await kv.get('skip')) || {})[key] || [];
  const missed = S.program.days.filter(d => d.weekday != null && d.weekday < td && !done.has(d.id) && !skip.includes(d.id));
  if (!missed.length) return '';
  const todayDay = S.program.days.find(d => d.weekday === td && !done.has(d.id));
  const m = missed[missed.length - 1];
  return `<section class="card missed"><h3>😬 Séance manquée : ${esc(m.name)}</h3>
    <p class="small muted">Pas de panique, on rattrape intelligemment${missed.length > 1 ? ` (${missed.length} séances en retard, on garde la plus récente)` : ''} :</p>
    <button class="btn block" data-act="miss-now" data-id="${m.id}">▶ La faire maintenant${todayDay ? ' (à la place d’aujourd’hui)' : ''}</button>
    ${todayDay ? `<button class="btn ghost block" data-act="miss-combine" data-id="${m.id}" data-today="${todayDay.id}">⚡ Combiner avec la séance du jour (${S.program.minutes || S.profile?.sessionMinutes || 60} min max)</button>` : ''}
    <button class="btn ghost block" data-act="miss-skip" data-id="${m.id}">Passer pour cette semaine</button></section>`;
}

async function startMissed(missedId, todayId) {
  const missed = S.program.days.find(d => d.id === missedId);
  if (!todayId) return startCustom(missed.name + ' (rattrapage)', missed.items.map(i => ({ ...i })), [missedId]);
  const today = S.program.days.find(d => d.id === todayId);
  const prio = (d) => [...d.items].sort((a, b) => ['force', 'hyper', 'hiit', 'iso', 'core', 'cardio'].indexOf(a.role) - ['force', 'hyper', 'hiit', 'iso', 'core', 'cardio'].indexOf(b.role));
  const A = prio(today), B = prio(missed), items = [], seen = new Set();
  // on alterne : l'essentiel des deux séances d'abord
  for (let i = 0; i < Math.max(A.length, B.length); i++) for (const it of [A[i], B[i]]) if (it && !seen.has(it.exId)) { seen.add(it.exId); items.push({ ...it }); }
  const day = { items };
  fitDayToTime(day, S.program.minutes || S.profile?.sessionMinutes || 60, S.profile?.goal, S.program.periodize !== false);
  return startCustom(`Combinée : ${today.name.split(' · ')[1] || today.name} + ${missed.name.split(' · ')[1] || missed.name}`, day.items, [todayId, missedId]);
}
