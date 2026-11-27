// FORGE — point d'entrée : navigation, accueil, profil & réglages.
import { S, loadState, esc, $, $$, toast, sheet, confirmBox, targets, today, num, fmtDate, ACTIVITY, unlockAudio, exById, GOALS, WEEKDAYS, defaultTrainingDays } from './ui.js';
import { healthCard, importFromClipboard, saveHealth, runShortcut, exportDayText, SHORTCUT_GUIDE_V2, SHORTCUT_TEMPLATE, SC_IN, SC_OUT } from './health.js';
import { kv, body, food, exportAll, importAll, wipe } from './db.js';
import { generateProgram, weekInfo, applyBlock, dayForDate, dayMinutes, WEEKDAY_LONG, fitProgramToTime } from './data.js';
import { initOffline } from './offline.js';
import { missedCard, onFeatureAction, setReviewOffset } from './features.js';
import { PRICES } from './claude.js';
import { chronoSheet, renderTrain, onTrainAction, onTrainChange, renderSession, onSessionAction, onSessionInput, allSessions, stopRest, adjustRest, prescription } from './train.js';
import { renderProgress, onProgressAction, onProgressChange, setProgressTab } from './progress.js';
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
document.addEventListener('click', (e) => { if (e.target.closest('[data-review]')) { setProgressTab('bilan'); setReviewOffset(new Date().getDay() === 0 ? 0 : -1); } }, true);
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
  const doneIds = new Set(thisWeek.flatMap(s => [s.dayId, ...(s.dayIds || [])]));
  const scheduled = S.program?.days.some(d => d.weekday != null);
  const todayDay = dayForDate(S.program);
  let next = todayDay || S.program?.days.find(d => !doneIds.has(d.id)) || S.program?.days[0];
  let nextLabel = todayDay ? 'Séance du jour' : 'Prochaine séance';
  if (scheduled && !todayDay) {
    const wd = (new Date().getDay() + 6) % 7;
    const up = [...S.program.days].filter(d => d.weekday != null).sort((a, b) => ((a.weekday - wd + 7) % 7) - ((b.weekday - wd + 7) % 7))[0];
    if (up) { next = up; nextLabel = `Repos aujourd’hui · prochaine : ${WEEKDAY_LONG[up.weekday].toLowerCase()}`; }
  }
  const doneToday = todayDay && thisWeek.some(s => (s.dayId === todayDay.id || (s.dayIds || []).includes(todayDay.id)) && new Date(s.date).toDateString() === new Date().toDateString());
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
  ${await missedCard()}
  ${[0, 1].includes(new Date().getDay()) ? `<a class="card review-cta" href="#/progres" data-review="1"><b>📊 Ton bilan de la semaine est prêt</b><span>›</span></a>` : ''}
  ${next ? `<section class="card next">
    <div class="eyebrow">${nextLabel} · Semaine ${info.week} · ${info.phase}</div>
    <h2>${esc(next.name)}${doneToday ? ' ✓' : ''}</h2>
    <div class="muted small">≈ ${dayMinutes(next, S.program.periodize !== false)} min max · ${next.items.length} exercices</div>
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
async function renderProfile(view) {
  S.usage = (await kv.get('usage')) || {};
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
      <label class="mini">Temps max par séance (min)<input type="number" name="sessionMinutes" inputmode="numeric" min="20" max="180" step="5" value="${p.sessionMinutes || 60}"></label>
      <label class="mini">Matériel${sel('equipment', [['salle', 'Salle de sport'], ['maison', 'Maison (haltères, barre de traction)'], ['pdc', 'Poids du corps']], p.equipment)}</label>
    </div>
    <div class="field">Jours d’entraînement (le programme suit ces jours)<div class="wdays">${WEEKDAYS.map((d, i) => `<label><input type="checkbox" name="td" value="${i}" ${(p.trainingDays?.length ? p.trainingDays : defaultTrainingDays(+p.days || 4)).includes(i) ? 'checked' : ''}><span>${d}</span></label>`).join('')}</div></div>
    <label class="field">Activité quotidienne${sel('activity', Object.entries(ACTIVITY), p.activity)}</label>
    <label class="field">Notes pour le coach (blessures, préférences…)<textarea name="notes" rows="2">${esc(p.notes || '')}</textarea></label>
    <button class="btn block" data-act="psave">${S.profile ? 'Enregistrer' : 'Créer mon programme'}</button>
    ${S.profile ? '<button class="btn ghost block" data-act="pregen">Enregistrer et régénérer le programme</button>' : ''}
  </form>

  <section class="card"><h2>⏱ Temps de repos</h2>
    <label class="check-row"><input type="checkbox" data-act="set-restAuto" ${st.restAuto !== false ? 'checked' : ''}> Lancer le repos automatiquement quand je valide une série</label>
    <label class="check-row"><input type="checkbox" data-act="set-restSound" ${st.restSound !== false ? 'checked' : ''}> Bip (décompte 3-2-1 et fin du repos)</label>
    <label class="check-row"><input type="checkbox" data-act="set-restVibe" ${st.restVibe !== false ? 'checked' : ''}> Vibration (Android ; l’iPhone ne vibre pas depuis une app web)</label>
    <label class="check-row"><input type="checkbox" data-act="set-restWatch" ${st.restWatch ? 'checked' : ''}> ⌚ Lancer aussi le repos sur mon <b>Apple Watch</b> (raccourci « FORGE Repos »)</label>
    <details class="guidebox" ${st.restWatch ? '' : 'open'}><summary>Créer le raccourci « FORGE Repos » (1 min)</summary>
      <ol class="small guide">
        <li>Ouvre <b>Raccourcis</b> → <b>+</b>. Dans « Décrire un raccourci », tape :<br><code>Démarre un minuteur dont la durée en secondes est le texte reçu en entrée</code> puis Entrée ↵.</li>
        <li>Touche le <b>⌄</b> à côté du nom en haut → <b>Renommer</b> → <code>FORGE Repos</code>.</li>
        <li>Reviens ici, coche la case ci-dessus et touche « Tester » : l’app Horloge doit lancer un minuteur de 30 s.</li>
        <li>Sur la montre, le minuteur s’affiche dans le Smart Stack (tourne la Digital Crown) et la montre <b>vibre à la fin du repos</b>, iPhone verrouillé ou dans la poche.</li>
      </ol>
      <p class="small muted">À chaque série validée, l’iPhone passe une seconde par Raccourcis : touche « ◀ » en haut à gauche pour revenir dans FORGE. Le chrono FORGE continue en parallèle.</p>
    </details>
    <button class="btn ghost block" data-act="testwatch">⌚ Tester (minuteur de 30 s)</button>
    <p class="muted small">Le temps de repos de chaque exercice se règle dans Entraînement → ✎ Modifier. Le bouton ⏱ en haut de l’écran ouvre un minuteur et un chronomètre à tout moment. L’écran reste allumé pendant la séance.</p>
  </section>

  <section class="card"><h2>Claude</h2>
    <p class="small"><b>Avec ton abonnement Claude</b> : rien à configurer. Dans l’onglet Coach, FORGE copie tes données ; tu les colles dans l’app Claude.</p>
    <p class="small"><b>Coach intégré</b> : nécessite une clé API Anthropic (créée sur console.anthropic.com, facturée à l’usage, indépendante de l’abonnement claude.ai). Elle est stockée uniquement sur cet appareil et envoyée seulement à api.anthropic.com.</p>
    <label class="field">Clé API<input type="password" id="apikey" placeholder="sk-ant-…" value="${esc(st.apiKey || '')}" autocomplete="off"></label>
    <label class="field">Modèle<select id="model">${[['claude-opus-5-5', 'Claude Opus 5.5 (recommandé)'], ['claude-sonnet-5-5', 'Claude Sonnet 5.5 (moins cher)'], ['claude-haiku-5-5', 'Claude Haiku 5.5 (très économique)']].map(([k, l]) => `<option value="${k}" ${k === (st.model || 'claude-opus-5-5') ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <button class="btn ghost block" data-act="savekey">Enregistrer</button>
    ${costBlock()}
  </section>

  <section class="card" id="watch"><h2>⌚ Apple Watch & Apple Santé</h2>
    <div class="row gap wrap"><button class="btn grow" data-act="hsync">Synchroniser maintenant</button><button class="btn ghost grow" data-act="hout">Journal → Santé</button></div>
    <label class="check-row"><input type="checkbox" id="usewatch" data-act="usewatch" ${p.useWatch ? 'checked' : ''}> Caler mes calories du jour sur la dépense réelle mesurée par la montre</label>
    <details class="guidebox" ${Object.keys(S.health || {}).length ? '' : 'open'}><summary>Créer le raccourci (une fois)</summary>${SHORTCUT_GUIDE_V2}
      <button class="btn block" data-act="hcopytpl">⧉ Copier le modèle de texte</button>
      <p class="muted small center"><code>${SHORTCUT_TEMPLATE}</code></p></details>
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
  <section class="card"><h2>🔄 Mise à jour</h2>
    <p class="small muted">Si l’app semble ancienne ou bloquée : FORGE retélécharge sa dernière version. <b>Tes données (séances, repas, photos…) ne sont pas touchées.</b></p>
    <button class="btn block" data-act="reboot">🔄 Recharger FORGE</button></section>
  <p class="muted small center">FORGE · ${APP_VERSION}</p>`;
}

function readProfile() {
  const f = $('#pform'); const o = {};
  for (const el of f.elements) { if (!el.name || el.type === 'checkbox') continue; o[el.name] = el.type === 'number' ? (el.value === '' ? null : +el.value) : el.value; }
  o.activity = +o.activity; o.sessionMinutes = Math.min(180, Math.max(20, Math.round((+o.sessionMinutes || 60) / 5) * 5));
  o.carbCycle = f.elements.carbCycle.checked;
  o.trainingDays = $$('input[name=td]:checked', f).map(x => +x.value);
  if (!o.trainingDays.length) o.trainingDays = defaultTrainingDays(+(S.profile?.days) || 4);
  o.days = o.trainingDays.length;
  return { ...(S.profile || {}), ...o }; // conserve les réglages hors formulaire
}

async function onProfileAction(act, el) {
  if (act === 'psave' || act === 'pregen') {
    const p = readProfile();
    if (!p.age || !p.height || !p.weight) return toast('Âge, taille et poids sont nécessaires');
    const isNew = !S.profile;
    const oldMin = S.profile?.sessionMinutes;
    S.profile = p; await kv.set('profile', p);
    if (isNew) await body.put({ id: 'b' + Date.now().toString(36), date: today(), weight: p.weight, bf: p.bodyfat || null, lean: p.bodyfat ? Math.round(p.weight * (1 - p.bodyfat / 100) * 10) / 10 : null });
    if (!S.program || act === 'pregen') {
      if (act === 'pregen' && !(await confirmBox('Remplacer ton programme par un nouveau généré depuis ce profil ?', 'Régénérer'))) return;
      S.program = generateProgram(p); await kv.set('program', S.program);
      toast('Programme hybride créé 💪'); location.hash = '#/entrainement'; return;
    }
    if (S.program && act === 'psave' && oldMin !== p.sessionMinutes && await confirmBox(`Adapter les séances de ton programme actuel à ${p.sessionMinutes} min max ?`, 'Adapter')) {
      fitProgramToTime(S.program, p.sessionMinutes, p.goal); await kv.set('program', S.program);
      toast(`Séances ajustées à ${p.sessionMinutes} min max ✓`); return;
    }
    toast('Profil enregistré');
  }
  if (act === 'reboot') return hardReload();
  if (act === 'testwatch') { location.href = 'shortcuts://run-shortcut?name=' + encodeURIComponent('FORGE Repos') + '&input=text&text=30'; return; }
  if (act === 'hcopytpl') {
    try { await navigator.clipboard.writeText(SHORTCUT_TEMPLATE); toast('Modèle copié : colle-le dans l’action Texte'); }
    catch (e) { toast(SHORTCUT_TEMPLATE, 6000); }
    return;
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

function costBlock() {
  const m = new Date().toISOString().slice(0, 7), u = S.usage?.[m];
  const row = (id, label) => { const p = PRICES[id]; return `<div class="tr"><span>${label}</span><b>${p[0]} $ / ${p[1]} $</b><small>${id === 'claude-haiku-5-5' ? '< 0,01 $' : id === 'claude-sonnet-5-5' ? '~0,01–0,02 $' : '~0,02–0,04 $'}</small></div>`; };
  return `<h3 class="sec">Combien ça coûte ?</h3>
    <div class="table"><div class="tr"><span><small>Modèle</small></span><b><small>entrée / sortie par million de tokens</small></b><small>par photo ou message</small></div>
    ${row('claude-opus-5-5', 'Opus 5.5')}${row('claude-sonnet-5-5', 'Sonnet 5.5')}${row('claude-haiku-5-5', 'Haiku 5.5')}</div>
    <p class="muted small">Une adaptation complète du programme coûte environ 0,10 à 0,25 $ avec Opus. Usage typique (2 photos par jour + quelques questions) : ~3 à 5 $/mois avec Opus, ~1,5 à 3 $ avec Sonnet, quelques centimes avec Haiku. Crédits prépayés sur console.anthropic.com, avec une limite de dépense que tu fixes toi-même.</p>
    <p class="small"><b>Ce mois-ci :</b> ${u ? `${u.n} requête${u.n > 1 ? 's' : ''} · ~${u.cost.toFixed(2).replace('.', ',')} $` : 'aucune requête'}</p>`;
}

async function onProfileChange(act, el) {
  if (act?.startsWith('set-')) { S.settings[act.slice(4)] = el.checked; await kv.set('settings', S.settings); toast('Réglage enregistré'); return; }
  if (el.id === 'usewatch') { if (!S.profile) return; S.profile.useWatch = el.checked; await kv.set('profile', S.profile); toast(el.checked ? 'Calories calées sur ta montre (une fois synchronisée)' : 'Calories calculées depuis ton profil'); return; }
  if (act === 'import' && el.files[0]) {
    try { await importAll(JSON.parse(await el.files[0].text())); await loadState(); toast('Sauvegarde restaurée ✓'); render(); }
    catch (e) { toast('Restauration impossible : ' + e.message, 5000); }
  }
  if (act === 'import-activity') return onTrainChange(act, el, () => { location.hash = '#/entrainement'; });
}

// ————— Rechargement forcé (garde les données) —————
const APP_VERSION = 'v12';
export async function hardReload() {
  if (!navigator.onLine) return toast('Il faut du réseau pour télécharger la nouvelle version');
  toast('Mise à jour de FORGE…');
  try { for (const r of (await navigator.serviceWorker?.getRegistrations()) || []) if (r.scope.includes('/forge/')) await r.unregister(); } catch (e) { }
  try { for (const k of await caches.keys()) if (k.startsWith('forge')) await caches.delete(k); } catch (e) { }
  setTimeout(() => location.replace(location.pathname + '?v=' + Date.now() + '#/'), 400);
}

// ————— Synchro Apple Santé —————
function healthSync() {
  const w = sheet(`<h3>⌚ Synchroniser Apple Santé</h3>
    <p class="small">1. Lance le raccourci : il lit ta montre dans Santé et copie les valeurs.<br>2. Reviens dans FORGE et colle.</p>
    <button class="btn block" id="hrun">1 · Lancer « ${SC_IN} »</button>
    <button class="btn block" id="hpaste">2 · Coller les données</button>
    <a class="btn ghost block" href="#/profil" data-close>Raccourci pas encore créé ? Le guide</a>
    <details class="manual"${S.health?.[today()] ? '' : ''}><summary>✍️ Saisir à la main (sans raccourci)</summary>
      <p class="small muted">Ouvre l’app <b>Forme</b> (anneaux) ou <b>Santé</b> de ton iPhone et recopie les chiffres du jour.</p>
      <div class="grid2">
        <label class="mini">Calories actives (Bouger)<input type="number" inputmode="numeric" id="hm-active" placeholder="ex : 550"></label>
        <label class="mini">Pas<input type="number" inputmode="numeric" id="hm-steps" placeholder="ex : 8500"></label>
        <label class="mini">FC au repos<input type="number" inputmode="numeric" id="hm-rhr" placeholder="ex : 58"></label>
        <label class="mini">Poids kg<input type="number" inputmode="decimal" step="0.1" id="hm-weight" placeholder="opt."></label>
      </div>
      <button class="btn block" id="hmsave">Enregistrer</button>
    </details>`, { onClose: render });
  $('#hmsave', w).onclick = async () => {
    const v = (id) => { const x = $('#' + id, w).value; return x === '' ? undefined : +x; };
    const h = { date: today(), active: v('hm-active'), steps: v('hm-steps'), rhr: v('hm-rhr'), weight: v('hm-weight') };
    Object.keys(h).forEach(k => h[k] === undefined && delete h[k]);
    if (Object.keys(h).length < 2) return toast('Renseigne au moins un chiffre');
    await saveHealth(h); toast('Données de la montre enregistrées ✓'); w.close();
  };
  $('#hrun', w).onclick = () => runShortcut(SC_IN);
  $('#hpaste', w).onclick = async () => {
    try { const h = await importFromClipboard(); if (h) { toast(`Santé importée : ${h.steps ?? '–'} pas, ${h.active ?? '–'} kcal actives${h.weight ? ', ' + h.weight + ' kg' : ''}`, 4000); w.close(); } }
    catch (e) { toast(e.message, 4000); }
  };
}

// ————— Démarrage —————
(async () => {
  await loadState();
  $('#chronoBtn').onclick = () => chronoSheet();
  if (/[?&]reboot\b/.test(location.search) && navigator.onLine) { history.replaceState(null, '', location.pathname + location.hash); hardReload(); return; }
  let lp; const t = $('#title');
  t.addEventListener('pointerdown', () => { lp = setTimeout(async () => { if (await confirmBox('Recharger FORGE (dernière version) ? Tes données sont conservées.', 'Recharger')) hardReload(); }, 900); });
  ['pointerup', 'pointerleave', 'pointercancel'].forEach(ev => t.addEventListener(ev, () => clearTimeout(lp)));
  window.addEventListener('forge:refresh', () => { if (!document.querySelector('.sheet-wrap')) render(); });
  if (location.hash.startsWith('#/seance') && !S.active) location.hash = '#/';
  await render();
  $('#splash')?.remove();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => { });
  if (navigator.storage?.persist) navigator.storage.persist().catch(() => { });
  initOffline();
})();

// l'accueil réutilise l'action « démarrer » de l'entraînement
ROUTES[''].action = ROUTES.accueil.action = async (act, el, rr) => { if (act === 'start') return onTrainAction(act, el, rr); return onFeatureAction(act, el, rr); };
