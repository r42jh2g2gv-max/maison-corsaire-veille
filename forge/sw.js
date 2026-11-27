// FORGE — service worker : l'app s'ouvre instantanément et fonctionne sans réseau (salle de sport).
// Stratégie : on sert la version en cache tout de suite, et on télécharge la nouvelle en arrière-plan
// dès qu'il y a du réseau. Changer CACHE à chaque mise à jour déclenche l'installation de la nouvelle version.
const CACHE = 'forge-v6';
const CDN = 'forge-cdn-v1';
const FILES = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png',
  'js/app.js', 'js/ui.js', 'js/db.js', 'js/data.js', 'js/charts.js', 'js/train.js', 'js/progress.js', 'js/nutrition.js',
  'js/coach.js', 'js/claude.js', 'js/devices.js', 'js/plan.js', 'js/health.js', 'js/ecart.js', 'js/offline.js'];
// bibliothèques externes gardées en cache (coach Claude, scanner iPhone)
const CDN_FILES = ['https://cdn.jsdelivr.net/npm/@anthropic-ai/sdk@1.7.0/+esm', 'https://cdn.jsdelivr.net/npm/@zxing/library@0.21.3/umd/index.min.js'];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await c.addAll(FILES.map(f => new Request(f, { cache: 'reload' })));
    const cdn = await caches.open(CDN);
    await Promise.all(CDN_FILES.map(u => cdn.match(u).then(hit => hit || cdn.add(u)).catch(() => { })));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE && k !== CDN) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    // cache d'abord (instantané, marche sans réseau), mise à jour en arrière-plan
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const hit = await cache.match(req, { ignoreSearch: true });
      const net = fetch(req).then(r => { if (r.ok) cache.put(req, r.clone()); return r; }).catch(() => null);
      if (hit) { e.waitUntil(net); return hit; }
      return (await net) || (req.mode === 'navigate' ? cache.match('index.html') : Response.error());
    })());
    return;
  }
  if (url.hostname === 'cdn.jsdelivr.net') {
    e.respondWith(caches.open(CDN).then(async c => (await c.match(req)) || fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; })));
  }
  // API Claude, Open Food Facts… : réseau direct (gérés par la file d'attente de l'app)
});
