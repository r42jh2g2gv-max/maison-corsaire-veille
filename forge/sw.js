// FORGE — service worker : l'app fonctionne hors connexion.
const CACHE = 'forge-v3';
const FILES = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png',
  'js/app.js', 'js/ui.js', 'js/db.js', 'js/data.js', 'js/charts.js', 'js/train.js', 'js/progress.js', 'js/nutrition.js', 'js/coach.js', 'js/claude.js', 'js/devices.js', 'js/plan.js', 'js/health.js'];

self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return; // API, Open Food Facts : réseau direct
  // réseau d'abord (mises à jour), cache en secours
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; }).catch(() => caches.match(e.request, { ignoreSearch: true })));
});
