// FORGE — hors connexion (salle sans réseau) : file d'attente traitée automatiquement au retour du réseau.
// Tout le reste (séances, chronos, journal, menu, mesures, photos) fonctionne sans réseau : les données sont sur le téléphone.
import { S, $, toast } from './ui.js';
import { kv, food, uid } from './db.js';

export async function fetchT(url, ms = 8000, opts = {}) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), ms);
  try { return await fetch(url, { ...opts, signal: ac.signal }); }
  finally { clearTimeout(t); }
}
export const isNetErr = (e) => !navigator.onLine || e?.name === 'AbortError' || e?.name === 'TypeError' || /fetch|network|connection/i.test(e?.message || '');

export async function enqueue(task) {
  S.queue.push({ id: uid('q'), at: Date.now(), ...task });
  await kv.set('queue', S.queue);
  netBadge();
}

// Ajoute une ligne « en attente » dans le journal et met la tâche en file.
export async function pendingFood({ date, meal, name, grams = null, task }) {
  const id = uid('f');
  const d = new Date(), time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  task = { ...task, time };
  await food.put({ id, date, meal, time, name, grams, kcal: 0, p: 0, c: 0, f: 0, pending: true, src: 'attente' });
  await enqueue({ ...task, foodId: id, date, meal, grams });
  toast('Pas de réseau : enregistré, calculé dès que tu retrouves du réseau', 4500);
  return id;
}

const handlers = {};
export const registerHandler = (type, fn) => { handlers[type] = fn; };

let busy = false;
export async function processQueue() {
  if (busy || !navigator.onLine || !S.queue.length) { netBadge(); return; }
  busy = true;
  let done = 0;
  try {
    for (const task of [...S.queue]) {
      const h = handlers[task.type]; if (!h) continue;
      try {
        await h(task);
        S.queue = S.queue.filter(x => x.id !== task.id); done++;
      } catch (e) {
        if (isNetErr(e)) break; // toujours pas de vrai réseau : on réessaiera
        task.tries = (task.tries || 0) + 1; task.error = e.message;
        if (task.tries >= 3) { S.queue = S.queue.filter(x => x.id !== task.id); const f = task.foodId && await food.get(task.foodId); if (f) { f.name = f.name.replace(' (en attente)', '') + ' (à compléter)'; f.pending = false; await food.put(f); } }
      }
      await kv.set('queue', S.queue);
    }
  } finally { busy = false; netBadge(); }
  if (done) { toast(`Réseau retrouvé : ${done} élément${done > 1 ? 's' : ''} mis à jour ✓`); window.dispatchEvent(new Event('forge:refresh')); }
}

export function netBadge() {
  const b = $('#netbadge'); if (!b) return;
  const n = S.queue?.length || 0;
  if (!navigator.onLine) { b.hidden = false; b.textContent = n ? `Hors ligne · ${n} en attente` : 'Hors ligne'; b.className = 'netbadge off'; }
  else if (n) { b.hidden = false; b.textContent = `↻ ${n} en attente`; b.className = 'netbadge wait'; }
  else b.hidden = true;
}

export function initOffline() {
  window.addEventListener('online', () => { netBadge(); processQueue(); navigator.serviceWorker?.getRegistration().then(r => r?.update()).catch(() => { }); });
  window.addEventListener('offline', netBadge);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') processQueue(); });
  setInterval(processQueue, 60000); // réseau faible : on retente chaque minute
  netBadge();
  processQueue();
  // mise à jour de l'app : le nouveau code est téléchargé en arrière-plan, on propose de recharger
  if ('serviceWorker' in navigator) {
    const had = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!had) return;
      const bar = document.createElement('div');
      bar.className = 'updbar';
      bar.innerHTML = '<span>Nouvelle version de FORGE installée</span><button class="btn sm">Recharger</button>';
      bar.querySelector('button').onclick = () => location.reload();
      document.body.appendChild(bar);
    });
  }
}
