// FORGE — Apple Watch / Apple Santé via l'app « Raccourcis » d'iPhone.
// Apple ne donne accès à Santé qu'aux apps natives : une app web passe donc par un raccourci
// qui lit Santé, copie les valeurs, puis FORGE les colle. Dans l'autre sens, FORGE copie le
// journal du jour et un second raccourci l'enregistre dans Santé.
import { S, esc, $, toast, sheet, today, num, targets } from './ui.js';
import { kv, body, food, uid } from './db.js';

export const SC_IN = 'FORGE Sync';
export const SC_OUT = 'FORGE vers Santé';

const KEYS = { date: 'date', pas: 'steps', steps: 'steps', actif: 'active', active: 'active', fcrepos: 'rhr', rhr: 'rhr', vfc: 'hrv', hrv: 'hrv', poids: 'weight', weight: 'weight', sommeil: 'sleep', sleep: 'sleep', exercice: 'exmin', mg: 'bf', vo2: 'vo2' };
const numOf = (v) => { const m = String(v).replace(/\s/g, '').replace(',', '.').match(/-?\d+(\.\d+)?/); return m ? +m[0] : null; };

export function parseHealthText(txt) {
  // version express : le raccourci copie seulement la somme des calories actives (ex. « 612 » ou « 612,4 kcal »)
  const bare = String(txt).replace(/\s/g, '').replace(',', '.');
  if (/^\d+(\.\d+)?(kcal|cal)?$/i.test(bare)) return { date: today(), active: Math.round(parseFloat(bare)) };
  if (!/forge/i.test(txt) && !/pas=|actif=/i.test(txt)) throw new Error('Ce texte ne vient pas du raccourci FORGE');
  const out = {};
  for (const part of txt.split(/[;\n&]/)) {
    const [k, ...rest] = part.split('=');
    const key = KEYS[k?.trim().toLowerCase()];
    if (!key || !rest.length) continue;
    const v = rest.join('=').trim();
    if (key === 'date') { const m = v.match(/(\d{4})-(\d{2})-(\d{2})/) || v.match(/(\d{2})\/(\d{2})\/(\d{4})/); out.date = m ? (m[1].length === 4 ? `${m[1]}-${m[2]}-${m[3]}` : `${m[3]}-${m[2]}-${m[1]}`) : today(); continue; }
    const n = numOf(v); if (n != null) out[key] = n;
  }
  if (!out.date) out.date = today();
  if (out.sleep > 24) out.sleep = Math.round(out.sleep / 60 * 10) / 10; // minutes → heures
  if (out.steps != null) out.steps = Math.round(out.steps);
  if (out.active != null) out.active = Math.round(out.active);
  if (Object.keys(out).length < 2) throw new Error('Aucune valeur trouvée');
  return out;
}

export async function saveHealth(h) {
  const { date, ...vals } = h;
  S.health[date] = { ...(S.health[date] || {}), ...vals, synced: new Date().toISOString() };
  await kv.set('health', S.health);
  if (h.weight) {
    const all = await body.all();
    const same = all.find(x => x.date === date);
    const e = { ...(same || { id: uid('b'), date }), weight: h.weight, src: 'sante' };
    if (h.bf) { e.bf = h.bf; e.lean = Math.round(h.weight * (1 - h.bf / 100) * 10) / 10; }
    await body.put(e);
    const last = all.filter(x => x.date > date).length === 0;
    if (last && S.profile) { S.profile.weight = h.weight; await kv.set('profile', S.profile); }
  }
}

export async function importFromClipboard() {
  let txt;
  try { txt = await navigator.clipboard.readText(); } catch (e) { return pasteSheet(); }
  const h = parseHealthText(txt);
  await saveHealth(h);
  return h;
}

function pasteSheet() {
  return new Promise((res) => {
    const w = sheet(`<h3>Coller les données Santé</h3><p class="muted small">Colle ici le texte copié par le raccourci « ${SC_IN} ».</p><textarea id="htxt" rows="4"></textarea><button class="btn block" id="hgo">Importer</button>`, { onClose: () => res(null) });
    $('#hgo', w).onclick = async () => {
      try { const h = parseHealthText($('#htxt', w).value); await saveHealth(h); res(h); w.close(); } catch (e) { toast(e.message); }
    };
  });
}

export function runShortcut(name) {
  location.href = 'shortcuts://run-shortcut?name=' + encodeURIComponent(name);
}

// Journal du jour → texte pour le raccourci d'export vers Santé
export async function exportDayText(date = today()) {
  const es = (await food.all()).filter(f => f.date === date);
  const s = es.reduce((a, e) => ({ k: a.k + (+e.kcal || 0), p: a.p + (+e.p || 0), c: a.c + (+e.c || 0), f: a.f + (+e.f || 0) }), { k: 0, p: 0, c: 0, f: 0 });
  // simples nombres séparés par « ; » : kcal ; protéines ; glucides ; lipides ; eau (L)
  return `${Math.round(s.k)};${Math.round(s.p)};${Math.round(s.c)};${Math.round(s.f)};${((S.water[date] || 0) * 0.25).toFixed(2)}`;
}

export function healthCard(date = today()) {
  const h = S.health[date];
  const t = targets(S.profile, date);
  if (!h) return `<section class="card health"><div class="row between"><b>⌚ Apple Watch</b><button class="btn sm" data-act="hsync">Synchroniser</button></div><p class="muted small">Importe tes pas, calories actives, FC au repos et ton poids depuis Apple Santé.</p></section>`;
  return `<section class="card health"><div class="row between"><b>⌚ Apple Watch · ${date === today() ? 'aujourd’hui' : date}</b><button class="btn sm ghost" data-act="hsync">↻</button></div>
    <div class="stats4 inner">
      <div class="stat"><b>${h.steps != null ? h.steps.toLocaleString('fr-FR') : '—'}</b><small>pas</small></div>
      <div class="stat"><b>${h.active ?? '—'}</b><small>kcal actives</small></div>
      <div class="stat"><b>${h.rhr ?? '—'}</b><small>FC repos</small></div>
      <div class="stat"><b>${h.sleep ? num(h.sleep) + ' h' : h.hrv ? h.hrv + ' ms' : '—'}</b><small>${h.sleep ? 'sommeil' : 'VFC'}</small></div>
    </div>${t.watch ? '<p class="muted small">Tes calories du jour suivent ta dépense réelle mesurée par la montre.</p>' : ''}</section>`;
}

export const SHORTCUT_TEMPLATE = 'FORGE;pas=;actif=;fcrepos=;poids=;vfc=';

export const SHORTCUT_GUIDE_V2 = `
<div class="express">
<h3>⚡ Version express (3 actions, 2 min)</h3>
<p class="small">Récupère les calories brûlées mesurées par ta montre.</p>
<ol class="small guide">
<li>Raccourcis → <b>+</b> → touche le nom en haut → <b>Renommer</b> → <code>${SC_IN}</code>.</li>
<li>Touche <b>Ajouter une action</b>, tape <i>santé</i> dans la recherche → <b>Rechercher des échantillons de santé</b>. Touche le mot bleu du type → choisis <b>Énergie active</b>. Touche <i>Ajouter un filtre</i> → règle-le sur <b>Date de début</b> · <b>est aujourd’hui</b>.</li>
<li>Recherche <i>statistiques</i> → <b>Calculer les statistiques</b> → touche le mot bleu → <b>Somme</b>.</li>
<li>Recherche <i>presse-papiers</i> → <b>Copier dans le presse-papiers</b>. Touche <b>OK</b>.</li>
<li>Touche ▶︎ une fois et <b>autorise l’accès à Santé</b>.</li>
</ol>
<p class="small">Pas envie de raccourci ? Utilise « ✍️ Saisir à la main » dans ⌚ Synchroniser avec les chiffres de l’app <b>Forme</b> de ton iPhone.</p>
</div>
<h3>Version complète (pas, calories, FC, poids)</h3>
<p class="small">Apple réserve Santé aux apps de l’App Store : l’app <b>Raccourcis</b> (déjà sur ton iPhone) sert de pont entre ta montre et FORGE.</p>
<ol class="small guide">
<li>Ouvre <b>Raccourcis</b> → <b>+</b> en haut à droite. Touche le nom en haut → <b>Renommer</b> → tape exactement <code>${SC_IN}</code>.</li>
<li><b>Pas</b> : ajoute l’action <b>Rechercher des échantillons de santé</b>. Type : <i>Pas</i> (ou <i>Nombre de pas</i>). Touche <i>Ajouter un filtre</i> → <i>Date de début</i> <i>est aujourd’hui</i>.<br>Ajoute <b>Calculer les statistiques</b> → <i>Somme</i>.</li>
<li><b>Calories</b> : refais exactement la même chose avec le type <i>Énergie active</i> (+ <b>Calculer les statistiques</b> → <i>Somme</i>).</li>
<li><b>FC au repos</b> : <b>Rechercher des échantillons de santé</b>, type <i>Fréquence cardiaque au repos</i>, <i>Trier par</i> Date de début, <i>Ordre</i> Plus récent d’abord, <i>Limite</i> activée → 1.</li>
<li><b>Poids</b> : pareil avec le type <i>Poids</i> (trier, plus récent, limite 1). Si tu veux : idem avec <i>Variabilité de la fréquence cardiaque</i>.</li>
<li>Ajoute l’action <b>Texte</b>. Colle le modèle (bouton « Copier le modèle » ci-dessous), puis place le curseur <b>juste après chaque « = »</b> et touche <i>Sélectionner une variable</i> → touche le résultat de l’action correspondante (Somme des pas, Somme des calories, FC repos, Poids, VFC).</li>
<li>Ajoute <b>Copier dans le presse-papiers</b>. Termine.</li>
<li>Lance-le une première fois : iPhone demande l’accès à Santé → <b>Autoriser</b> tout.</li>
</ol>
<p class="small"><b>Ensuite, à chaque fois</b> : dans FORGE, ⌚ <b>Synchroniser</b> → « 1 · Lancer » (le raccourci s’exécute) → reviens dans FORGE → « 2 · Coller ».</p>
<details><summary><b>Automatique chaque soir</b> (optionnel)</summary>
<p class="small">Raccourcis → <b>Automatisation</b> → <b>+</b> → <i>Heure de la journée</i> → 21:00, Quotidien → <i>Exécuter immédiatement</i> → choisis « ${SC_IN} ». Le soir, ouvre FORGE et touche simplement « Coller ».</p></details>
<details><summary><b>Raccourci « ${SC_OUT} »</b> (FORGE → Santé, optionnel)</summary>
<ol class="small guide">
<li>Nouveau raccourci nommé exactement <code>${SC_OUT}</code>.</li>
<li><b>Obtenir le presse-papiers</b>, puis <b>Diviser le texte</b> → séparateur <i>Personnalisé</i> : <code>;</code></li>
<li><b>Obtenir l’élément de la liste</b> → <i>Premier élément</i>, puis <b>Enregistrer un échantillon de santé</b> → <i>Énergie alimentaire</i>, valeur = l’élément, unité kcal.</li>
<li>Recommence avec <i>Élément à l’index</i> 2 → <i>Protéines</i> (g), 3 → <i>Glucides</i> (g), 4 → <i>Lipides totaux</i> (g), 5 → <i>Eau</i> (L).</li>
</ol>
<p class="small">Dans FORGE : Profil → « Journal → Santé » envoie ton journal du jour dans Santé.</p></details>
<details><summary><b>Pendant tes séances</b></summary>
<p class="small">Lance l’exercice <b>Renforcement musculaire traditionnel</b> sur ta montre en même temps que la séance FORGE : FC et calories sont enregistrées dans Santé et récupérées à la synchro.</p></details>`;

export const SHORTCUT_GUIDE = `
<h3>Relier ton Apple Watch (une seule fois, ~5 min)</h3>
<p class="small">Apple réserve Santé aux apps de l’App Store. FORGE utilise donc l’app <b>Raccourcis</b> (déjà sur ton iPhone) comme pont. Ta montre enregistre tout dans Santé ; le raccourci lit Santé et transmet à FORGE.</p>
<details open><summary><b>1. Raccourci « ${SC_IN} » (Santé → FORGE)</b></summary>
<ol class="small guide">
<li>Raccourcis → <b>+</b> → nomme-le exactement <b>${SC_IN}</b>.</li>
<li>Ajoute <b>Rechercher des échantillons de santé</b> : type <i>Nombre de pas</i>, <i>Date de début</i> est <i>aujourd’hui</i>. Puis <b>Calculer des statistiques</b> → <i>Somme</i>.</li>
<li>Même chose pour <i>Énergie active</i> → <i>Somme</i>.</li>
<li><b>Rechercher des échantillons de santé</b> : <i>Fréquence cardiaque au repos</i>, trier par <i>Date de début</i> (plus récent), limite <i>1</i>.</li>
<li>Pareil pour <i>Poids</i> (limite 1) et, si tu veux, <i>Variabilité de la fréquence cardiaque</i>.</li>
<li>Ajoute un bloc <b>Texte</b> et écris, en insérant les résultats (variables) :<br><code>FORGE;date=</code><i>Date actuelle (format AAAA-MM-JJ)</i><code>;pas=</code><i>Somme 1</i><code>;actif=</code><i>Somme 2</i><code>;fcrepos=</code><i>FC repos</i><code>;poids=</code><i>Poids</i><code>;vfc=</code><i>VFC</i></li>
<li>Termine par <b>Copier dans le presse-papiers</b>.</li>
</ol></details>
<details><summary><b>2. Raccourci « ${SC_OUT} » (FORGE → Santé, optionnel)</b></summary>
<ol class="small guide">
<li>Nouveau raccourci nommé <b>${SC_OUT}</b>.</li>
<li><b>Obtenir le presse-papiers</b>, puis <b>Diviser le texte</b> par <i>;</i>.</li>
<li>Pour chaque valeur (kcal, protéines, glucides, lipides) : <b>Obtenir l’élément de la liste</b> (1, 2, 3, 4), <b>Remplacer le texte</b> <code>kcal=</code> par rien, puis <b>Enregistrer un échantillon de santé</b> : <i>Énergie alimentaire</i>, <i>Protéines</i>, <i>Glucides</i>, <i>Lipides totaux</i>.</li>
</ol></details>
<details><summary><b>3. Pendant tes séances</b></summary>
<p class="small">Lance l’exercice <b>Renforcement musculaire traditionnel</b> (ou Course, Vélo, HIIT…) sur ta montre en même temps que la séance FORGE : la montre mesure FC et calories, que la synchro récupère. Pour voir ta FC en direct dans FORGE, il faut une app montre qui diffuse la FC en Bluetooth + le navigateur Bluefy, ou une ceinture cardio.</p>
<p class="small">Pour récupérer le détail d’un entraînement (distance, tracé, FC), exporte-le en GPX/TCX avec une app comme HealthFit et importe-le dans Entraînement.</p></details>
<details><summary><b>4. Automatique chaque soir (optionnel)</b></summary>
<p class="small">Raccourcis → Automatisation → <i>Heure de la journée</i> 21:00 → exécuter « ${SC_IN} ». Les valeurs restent dans le presse-papiers : ouvre FORGE et touche « Coller les données ».</p></details>`;
