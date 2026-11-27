// FORGE — point d'entrée : navigation, accueil, profil & réglages.
import { S, loadState, esc, $, $$, toast, sheet, confirmBox, targets, today, num, fmtDate, ACTIVITY, unlockAudio, exById, GOALS, WEEKDAYS, defaultTrainingDays } from './ui.js';
import { healthCard, importFromClipboard, runShortcut, exportDayText, SHORTCUT_GUIDE, SC_IN, SC_OUT } from './health.js';
import { kv, body, food, exportAll, importAll, wipe } from './db.js';
import { generateProgram, weekInfo, applyBlock } from './data.js';
import { renderTrain, onTrainAction, onTrainChange, renderSession, onSessionAction, onSessionInput, allSessions, stopRest, adjustRest, prescription } from './train.js';
import { renderProgress, onProgressAction, onProgressChange } from './progress.js';
import { renderNutrition, onNutritionAction } from './nutrition.js';
import { renderCoach, onCoachAction, onCoachChange, onCoachSubmit } from './coach.js';
import { hr } from './devices.js';
import { bindCharts } from './charts.js';

const ROUTES = {
  '': { title: 'Aujourd’hui', render: renderHome, tab: 'accueil' },
  accueil: { title: 'Aujourd’hui', render: renderHome, tab: 'accueil' },
  entrainement: { title: 'Entraînement', render: renderTrain, tab: 'entrainement', action: onTrainAction, change: onTrainChange },
  seance: { title: 'Séance', render: renderSession, tab: 'entrainement', action: onSessionAction, input: onSessionInput },
  progres: { title: 'Progrès', render: renderProgress, tab: 'progres', action: onProgressAction, change: onProgressChange },
  nutrition: { title: 'Nutrition', render: renderNutrition, tab: 'nutrition', action: onNutritionAction },
  coach: { title: 'Coach Claude', render: renderCoach, tab: 'coach', action: onCoachAction, change: onCoachChange },
  profil: { title: 'Profil & réglages', render: renderProfile, tab: '', action: onProfileAction, change: onProfileChange },
};
const route = () => ROUTES[location.hash.replace(/^#\/?/, '').split('?')[0]] || ROUTES[''];

async function render() {
  const r = route();
  const view = $('#view');
  $('#title').textContent = r.title;
  document.querySelectorAll('.tabbar a').forEach(a => a.classList.toggle('on', a.dataset.tab === r.tab));
  $('#sessdot').hidden = !S.active;
  await r.render(view);
  bindCharts(view);
}
const rerender = () => render();

// ————— Délégation d'événements —————
document.addEventListener('click', async (e) => {
  const el = e.target.closest('[data-act]');
  if (!el || el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'FORM') return;
  if (!$('#view').contains(el)) return;
  e.preventDefault();
  if (el.dataset.act === 'hsync') return healthSync();
  const r = route();
  if (r.action) await r.action(el.dataset.act, el, rerender);
});
document.addEventListener('change', async (e) => {
  const el = e.target;
  if (!$('#view').contains(el)) return;
  const r = route();
  if (el.dataset.act && r.change) return r.change(el.dataset.act, el, rerender);
  if (r.input && (el.dataset.f || el.dataset.c || el.dataset.h)) return r.input(el);
});
document.addEventListener('input', (e) => {
  const el = e.target;
  if (!$('#view').contains(el)) return;
  const r = route();
  if (r.input && el.dataset.k === 'note') r.input(el);
});
document.addEventListener('submit', async (e) => {
  const f = e.target.closest('[data-act="chat-send"]');
  if (!f) return; e.preventDefault(); await onCoachSubmit(f);
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey && e.target.id === 'msg') { e.preventDefault(); e.target.form.requestSubmit(); }
});
window.addEventListener('hashchange', () => { document.querySelectorAll('.sheet-wrap').forEach(s => s.close ? s.close() : s.remove()); window.scrollTo(0, 0); render(); });
document.addEventListener('pointerdown', unlockAudio, { once: true });

// barre de repos
$('#restbar').addEventListener('click', (e) => {
  const b = e.target.closest('[data-r]'); if (!b) return;
  if (b.dataset.r === 'skip') stopRest(); else adjustRest(+b.dataset.r);
});

// ————— Accueil —————
async function renderHome(view) {
  if (!S.profile) { view.innerHTML = welcome(); return; }
  const p = S.profile, t = targets(p, today());
  const list = await allSessions();
  const info = weekInfo(S.program);
  const ws = new Date(); ws.setHours(0, 0, 0, 0); ws.setDate(ws.getDate() - ((ws.getDay() + 6) % 7));
  const thisWeek = list.filter(s => new Date(s.date) >= ws);
  const doneIds = new Set(thisWeek.map(s => s.dayId));
  const next = S.program?.days.find(d => !doneIds.has(d.id)) || S.program?.days[0];
  const todayFood = (await food.all()).filter(f => f.date === today());
  const kcal = todayFood.reduce((a, f) => a + (+f.kcal || 0), 0), prot = todayFood.reduce((a, f) => a + (+f.p || 0), 0);
  const bodies = (await body.all()).sort((a, b) => a.date.localeCompare(b.date));
  const lastB = bodies[bodies.length - 1], prevB = bodies.length > 1 ? bodies[0] : null;
  const delta = lastB && prevB ? lastB.weight - prevB.weight : null;
  const h = new Date().getHours();
  view.innerHTML = `
  <section class="greet"><div class="eyebrow">${fmtDate(new Date().toISOString(), { weekday: 'long', day: 'numeric', month: 'long' })}</div>
    <h1>${h < 12 ? 'Bonjour' : h < 18 ? 'Salut' : 'Bonsoir'} ${esc(p.name || '')} 👊</h1></section>
  ${S.active ? `<a class="card resume" href="#/seance"><b>▶ Reprendre la séance</b><span>${esc(S.active.name)}</span></a>` : ''}
  ${next ? `<section class="card next">
    <div class="eyebrow">Prochaine séance · Semaine ${info.week} · ${info.phase}</div>
    <h2>${esc(next.name)}</h2>
    <ul class="exlist">${next.items.slice(0, 6).map(it => `<li><span>${esc(exById(it.exId).name)}</span><small>${prescription(applyBlock(it, info))}</small></li>`).join('')}</ul>
    <button class="btn block" data-act="start" data-id="${next.id}">Démarrer maintenant</button>
  </section>` : ''}
  <div class="stats4">
    <a class="stat" href="#/entrainement"><b>${thisWeek.length}/${S.program?.days.length || p.days}</b><small>séances cette semaine</small></a>
    <a class="stat" href="#/nutrition"><b>${Math.round(kcal)}</b><small>/ ${t.kcal} kcal</small></a>
    <a class="stat" href="#/nutrition"><b>${Math.round(prot)} g</b><small>/ ${t.p} g protéines</small></a>
    <a class="stat" href="#/progres"><b>${lastB ? num(lastB.weight) : num(p.weight)} kg</b><small>${delta != null ? (delta <= 0 ? '' : '+') + num(delta) + ' kg depuis le début' : 'poids'}</small></a>
  </div>
  <div class="quick">
    <a class="qbtn" href="#/nutrition">🍽<span>Repas</span></a>
    <a class="qbtn" href="#/progres">📏<span>Mesure</span></a>
    <a class="qbtn" href="#/coach">🤖<span>Coach</span></a>
    <a class="qbtn" href="#/profil">⚙️<span>Réglages</span></a>
  </div>
  ${healthCard()}
  ${tip(info, thisWeek.length, prot, t)}`;
}

function tip(info, n, prot, t) {
  const tips = [];
  if (info.deload) tips.push('Semaine de décharge : baisse les charges de 10 %, dors bien, marche beaucoup. C’est là que le corps se reconstruit.');
  if (prot < t.p * 0.5 && new Date().getHours() > 14) tips.push(`Il te manque encore ${Math.round(t.p - prot)} g de protéines aujourd’hui : skyr, œufs, poulet ou whey.`);
  if (n === 0 && new Date().getDay() >= 3) tips.push('Pas encore de séance cette semaine : même 30 minutes comptent. Lance ta prochaine séance !');
  tips.push('Double progression : quand tu fais le haut de la fourchette sur toutes les séries, FORGE te propose d’augmenter la charge.');
  return `<section class="card tip"><b>💡 Conseil</b><p>${tips[0]}</p></section>`;
}

function welcome() {
  return `<section class="hero-welcome">
    <div class="logo-big">FORGE</div>
    <h1>Forge ton corps sur mesure</h1>
    <p>Programme hybride <b>force · muscle · cardio · endurance</b>, suivi des séances avec temps de repos, graphiques de progression, photos, calories et coach Claude.</p>
    <a class="btn block" href="#/profil">Créer mon profil (1 min)</a>
    <p class="muted small">Tes données restent sur ton téléphone.</p>
  </section>`;
}

// ————— Profil & réglages —————
function renderProfile(view) {
  const p = S.profile || { sex: 'h', age: 30, height: 178, weight: 80, goal: 'recompo', level: 'inter', days: 4, equipment: 'salle', activity: 1.45 };
  const st = S.settings;
  const sel = (name, opts, val) => `<select name="${name}">${opts.map(([k, l]) => `<option value="${k}" ${String(k) === String(val) ? 'selected' : ''}>${l}</option>`).join('')}</select>`;
  const isIOS = /iP(hone|ad|od)/.test(navigator.userAgent);
  view.innerHTML = `
  <form class="card" id="pform">
    <h2>Mon profil</h2>
    <label class="field">Prénom<input name="name" value="${esc(p.name || '')}" autocomplete="given-name"></label>
    <div class="grid3">
      <label class="mini">Sexe${sel('sex', [['h', 'Homme'], ['f', 'Femme']], p.sex)}</label>
      <label class="mini">Âge<input type="number" name="age" value="${p.age}"></label>
      <label class="mini">Taille cm<input type="number" name="height" value="${p.height}"></label>
      <label class="mini">Poids kg<input type="number" step="0.1" name="weight" value="${p.weight}"></label>
      <label class="mini">% MG (opt.)<input type="number" step="0.1" name="bodyfat" value="${p.bodyfat || ''}"></label>
      <label class="mini">Niveau${sel('level', [['debutant', 'Débutant'], ['inter', 'Intermédiaire'], ['avance', 'Avancé']], p.level)}</label>
    </div>
    <h3>Objectif</h3>
    <label class="field">Priorité${sel('goal', Object.entries(GOALS).map(([k, g]) => [k, g.label]), p.goal)}</label>
    <p class="muted small">${(GOALS[p.goal] || GOALS.recompo).desc}</p>
    <label class="check-row"><input type="checkbox" name="carbCycle" ${p.carbCycle !== false ? 'checked' : ''}> Plus de glucides les jours d’entraînement, moins les jours de repos (perte, sèche, recompo)</label>
    <div class="grid2"><label class="mini">Poids cible kg<input type="number" step="0.1" name="goalWeight" value="${p.goalWeight || ''}"></label><label class="mini">% MG cible<input type="number" step="0.1" name="goalBF" value="${p.goalBF || ''}"></label></div>
    <h3>Entraînement</h3>
    <div class="grid2">
      <label class="mini">Séances / semaine${sel('days', [[2, '2'], [3, '3'], [4, '4'], [5, '5'], [6, '6']], p.days)}</label>
      <label class="mini">Matériel${sel('equipment', [['salle', 'Salle de sport'], ['maison', 'Maison (haltères, barre de traction)'], ['pdc', 'Poids du corps']], p.equipment)}</label>
    </div>
    <div class="field">Jours d’entraînement<div class="wdays">${WEEKDAYS.map((d, i) => `<label><input type="checkbox" name="td" value="${i}" ${(p.trainingDays?.length ? p.trainingDays : defaultTrainingDays(+p.days || 4)).includes(i) ? 'checked' : ''}><span>${d}</span></label>`).join('')}</div></div>
    <label class="field">Activité quotidienne${sel('activity', Object.entries(ACTIVITY), p.activity)}</label>
    <label class="field">Notes pour le coach (blessures, préférences…)<textarea name="notes" rows="2">${esc(p.notes || '')}</textarea></label>
    <button class="btn block" data-act="psave">${S.profile ? 'Enregistrer' : 'Créer mon programme'}</button>
    ${S.profile ? '<button class="btn ghost block" data-act="pregen">Enregistrer et régénérer le programme</button>' : ''}
  </form>

  <section class="card"><h2>Claude</h2>
    <p class="small"><b>Avec ton abonnement Claude</b> : rien à configurer. Dans l’onglet Coach, FORGE copie tes données ; tu les colles dans l’app Claude.</p>
    <p class="small"><b>Coach intégré</b> : nécessite une clé API Anthropic (créée sur console.anthropic.com, facturée à l’usage, indépendante de l’abonnement claude.ai). Elle est stockée uniquement sur cet appareil et envoyée seulement à api.anthropic.com.</p>
    <label class="field">Clé API<input type="password" id="apikey" placeholder="sk-ant-…" value="${esc(st.apiKey || '')}" autocomplete="off"></label>
    <label class="field">Modèle<select id="model">${[['claude-opus-5-5', 'Claude Opus 5.5 (recommandé)'], ['claude-sonnet-5-5', 'Claude Sonnet 5.5 (moins cher)'], ['claude-haiku-5-5', 'Claude Haiku 5.5 (très économique)']].map(([k, l]) => `<option value="${k}" ${k === (st.model || 'claude-opus-5-5') ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <button class="btn ghost block" data-act="savekey">Enregistrer</button>
  </section>

  <section class="card" id="watch"><h2>⌚ Apple Watch & Apple Santé</h2>
    <div class="row gap wrap"><button class="btn grow" data-act="hsync">Synchroniser maintenant</button><button class="btn ghost grow" data-act="hout">Journal → Santé</button></div>
    <label class="check-row"><input type="checkbox" id="usewatch" data-act="usewatch" ${p.useWatch ? 'checked' : ''}> Caler mes calories du jour sur la dépense réelle mesurée par la montre</label>
    <details class="guidebox"><summary>Installer les raccourcis (une fois)</summary>${SHORTCUT_GUIDE}</details>
  </section>
  <section class="card"><h2>Autres appareils</h2>
    <div class="dev"><b>❤ Ceinture / montre cardio Bluetooth</b><p class="small muted">Polar H10, Garmin HRM, Wahoo, Coospo, montres en mode « diffusion FC »… La fréquence cardiaque s’affiche pendant la séance et est enregistrée (FC moyenne et max). ${isIOS ? 'Sur iPhone, Safari ne gère pas le Bluetooth : ouvre FORGE dans l’app gratuite « Bluefy ».' : 'Fonctionne avec Chrome sur Android et ordinateur.'}</p>
      <button class="btn ghost block" data-act="hr">${hr.device ? `Connecté · ${hr.bpm ?? '…'} bpm — déconnecter` : 'Connecter un capteur'}</button></div>
    <div class="dev"><b>⌚ Montres & applis (Garmin, Strava, Apple Watch, Polar, Coros…)</b><p class="small muted">Exporte une activité en <b>GPX</b> ou <b>TCX</b> (Strava : ⋯ → Exporter GPX ; Garmin Connect : ⚙ → Exporter TCX ; Apple Santé : via l’app « HealthFit » ou « RunGap ») puis importe-la : durée, distance, FC et calories sont ajoutées à ton historique.</p>
      <label class="btn ghost block">Importer un fichier GPX / TCX<input type="file" accept=".gpx,.tcx,application/gpx+xml,application/xml,text/xml" data-act="import-activity" hidden></label></div>
  </section>

  <section class="card"><h2>Installer l’app</h2>
    <p class="small">${isIOS ? 'Dans Safari : bouton Partager ⎋ → « Sur l’écran d’accueil ». FORGE s’ouvre alors en plein écran, comme une vraie app, et fonctionne hors connexion.' : 'Dans Chrome : menu ⋮ → « Installer l’application » / « Ajouter à l’écran d’accueil ». Fonctionne ensuite hors connexion.'}</p>
  </section>

  <section class="card"><h2>Mes données</h2>
    <p class="small muted">Tout est stocké sur cet appareil. Fais une sauvegarde régulièrement (ex : dans iCloud Drive / Google Drive).</p>
    <div class="row gap wrap"><button class="btn ghost grow" data-act="export">⇩ Sauvegarder</button>
    <label class="btn ghost grow">⇧ Restaurer<input type="file" accept="application/json,.json" data-act="import" hidden></label></div>
    <button class="btn ghost danger block" data-act="wipe">Tout effacer</button>
  </section>
  <p class="muted small center">FORGE · v1.0</p>`;
}

function readProfile() {
  const f = $('#pform'); const o = {};
  for (const el of f.elements) { if (!el.name || el.type === 'checkbox') continue; o[el.name] = el.type === 'number' ? (el.value === '' ? null : +el.value) : el.value; }
  o.days = +o.days; o.activity = +o.activity;
  o.carbCycle = f.elements.carbCycle.checked;
  o.trainingDays = $$('input[name=td]:checked', f).map(x => +x.value);
  return { ...(S.profile || {}), ...o }; // conserve les réglages hors formulaire
}

async function onProfileAction(act, el) {
  if (act === 'psave' || act === 'pregen') {
    const p = readProfile();
    if (!p.age || !p.height || !p.weight) return toast('Âge, taille et poids sont nécessaires');
    const isNew = !S.profile;
    S.profile = p; await kv.set('profile', p);
    if (!p.trainingDays.length) p.trainingDays = defaultTrainingDays(p.days);
    if (isNew) await body.put({ id: 'b' + Date.now().toString(36), date: today(), weight: p.weight, bf: p.bodyfat || null, lean: p.bodyfat ? Math.round(p.weight * (1 - p.bodyfat / 100) * 10) / 10 : null });
    if (!S.program || act === 'pregen') {
      if (act === 'pregen' && !(await confirmBox('Remplacer ton programme par un nouveau généré depuis ce profil ?', 'Régénérer'))) return;
      S.program = generateProgram(p); await kv.set('program', S.program);
      toast('Programme hybride créé 💪'); location.hash = '#/entrainement'; return;
    }
    toast('Profil enregistré');
  }
  if (act === 'hout') {
    const txt = await exportDayText();
    try { await navigator.clipboard.writeText(txt); } catch (e) { }
    toast('Journal du jour copié → raccourci « ' + SC_OUT + ' »'); setTimeout(() => runShortcut(SC_OUT), 500);
  }
  if (act === 'savekey') {
    const k = $('#apikey').value.trim();
    if (k && !k.startsWith('sk-ant-')) return toast('Une clé API Anthropic commence par « sk-ant- »');
    S.settings.apiKey = k; S.settings.model = $('#model').value; await kv.set('settings', S.settings);
    S.coachMode = k ? 'api' : 'abo';
    toast(k ? 'Clé enregistrée : coach intégré activé' : 'Clé retirée');
  }
  if (act === 'hr') {
    if (hr.device) { hr.disconnect(); render(); return; }
    try { const n = await hr.connect(); toast('Connecté : ' + n); hr.listeners.add(() => { }); render(); } catch (e) { if (e.name !== 'NotFoundError') toast(e.message, 5000); }
  }
  if (act === 'export') {
    const data = await exportAll(true);
    const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
    const name = `forge-sauvegarde-${today()}.json`;
    const file = new File([blob], name, { type: 'application/json' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) { try { await navigator.share({ files: [file], title: 'Sauvegarde FORGE' }); return; } catch (e) { if (e.name === 'AbortError') return; } }
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click();
  }
  if (act === 'wipe') {
    if (!(await confirmBox('Effacer TOUTES tes données (séances, photos, repas, profil) ? Irréversible.', 'Tout effacer'))) return;
    await wipe(); await loadState(); toast('Données effacées'); location.hash = '#/';
  }
}

async function onProfileChange(act, el) {
  if (el.id === 'usewatch') { if (!S.profile) return; S.profile.useWatch = el.checked; await kv.set('profile', S.profile); toast(el.checked ? 'Calories calées sur ta montre (une fois synchronisée)' : 'Calories calculées depuis ton profil'); return; }
  if (act === 'import' && el.files[0]) {
    try { await importAll(JSON.parse(await el.files[0].text())); await loadState(); toast('Sauvegarde restaurée ✓'); render(); }
    catch (e) { toast('Restauration impossible : ' + e.message, 5000); }
  }
  if (act === 'import-activity') return onTrainChange(act, el, () => { location.hash = '#/entrainement'; });
}

// ————— Synchro Apple Santé —————
function healthSync() {
  const w = sheet(`<h3>⌚ Synchroniser Apple Santé</h3>
    <p class="small">1. Lance le raccourci : il lit ta montre dans Santé et copie les valeurs.<br>2. Reviens dans FORGE et colle.</p>
    <button class="btn block" id="hrun">1 · Lancer « ${SC_IN} »</button>
    <button class="btn block" id="hpaste">2 · Coller les données</button>
    <p class="muted small">Raccourci pas encore créé ? Profil → Apple Watch → « Installer les raccourcis ».</p>`, { onClose: render });
  $('#hrun', w).onclick = () => runShortcut(SC_IN);
  $('#hpaste', w).onclick = async () => {
    try { const h = await importFromClipboard(); if (h) { toast(`Santé importée : ${h.steps ?? '–'} pas, ${h.active ?? '–'} kcal actives${h.weight ? ', ' + h.weight + ' kg' : ''}`, 4000); w.close(); } }
    catch (e) { toast(e.message, 4000); }
  };
}

// ————— Démarrage —————
(async () => {
  await loadState();
  if (location.hash.startsWith('#/seance') && !S.active) location.hash = '#/';
  await render();
  $('#splash')?.remove();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => { });
  if (navigator.storage?.persist) navigator.storage.persist().catch(() => { });
})();

// l'accueil réutilise l'action « démarrer » de l'entraînement
ROUTES[''].action = ROUTES.accueil.action = (act, el, rr) => act === 'start' ? onTrainAction(act, el, rr) : null;
