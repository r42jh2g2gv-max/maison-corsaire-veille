/* Service worker Maison Corsaire — généré par l'application (version {{ version }}). */
const CACHE = 'corsaire-{{ version }}';
const PAGES = {{ pages|safe }};
const STATIQUES = {{ statiques|safe }};

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.all([...STATIQUES, ...PAGES].map(async (url) => {
      try {
        const rep = await fetch(url, { credentials: 'same-origin' });
        if (rep.ok && !rep.redirected) await cache.put(url, rep);
      } catch (e) { /* hors ligne pendant l'installation : on réessaiera */ }
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const cle of await caches.keys()) {
      if (cle.startsWith('corsaire-') && cle !== CACHE) await caches.delete(cle);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Polices Google : servies depuis le cache, rafraîchies en arrière-plan
  if (url.hostname.endsWith('googleapis.com') || url.hostname.endsWith('gstatic.com')) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const enCache = await cache.match(req);
      const reseau = fetch(req).then((r) => { if (r.ok || r.type === 'opaque') cache.put(req, r.clone()); return r; }).catch(() => enCache);
      return enCache || reseau;
    })());
    return;
  }
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;

  // Pages : réseau d'abord ; sans réseau, la copie enregistrée (la caisse en priorité)
  if (req.mode === 'navigate') {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      try {
        const rep = await fetch(req);
        if (rep.ok && !rep.redirected && PAGES.includes(url.pathname)) cache.put(url.pathname, rep.clone());
        return rep;
      } catch (e) {
        return (await cache.match(url.pathname)) || (await cache.match('{{ url_for("caisse") }}'))
          || (await cache.match('{{ url_for("hors_ligne") }}')) || Response.error();
      }
    })());
    return;
  }

  // Fichiers statiques : cache d'abord
  if (url.pathname.startsWith('/static/')) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const enCache = await cache.match(req, { ignoreSearch: true });
      if (enCache) return enCache;
      const rep = await fetch(req);
      if (rep.ok) cache.put(req, rep.clone());
      return rep;
    })());
  }
});
