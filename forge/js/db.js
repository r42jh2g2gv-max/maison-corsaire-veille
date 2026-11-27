// FORGE — stockage local (IndexedDB). Tout reste sur l'appareil.
const DB_NAME = 'forge';
const STORES = ['kv', 'sessions', 'body', 'photos', 'food', 'recipes'];
let dbp;

function open() {
  if (dbp) return dbp;
  dbp = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      for (const s of STORES) if (!db.objectStoreNames.contains(s)) db.createObjectStore(s, s === 'kv' ? undefined : { keyPath: 'id' });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbp;
}

function tx(store, mode, fn) {
  return open().then(db => new Promise((resolve, reject) => {
    const t = db.transaction(store, mode);
    const s = t.objectStore(store);
    const r = fn(s);
    t.oncomplete = () => resolve(r && 'result' in r ? r.result : undefined);
    t.onerror = () => reject(t.error);
  }));
}

export const kv = {
  get: (k) => tx('kv', 'readonly', s => s.get(k)),
  set: (k, v) => tx('kv', 'readwrite', s => s.put(v, k)),
  del: (k) => tx('kv', 'readwrite', s => s.delete(k)),
};

export const col = (name) => ({
  all: () => tx(name, 'readonly', s => s.getAll()),
  get: (id) => tx(name, 'readonly', s => s.get(id)),
  put: (obj) => tx(name, 'readwrite', s => s.put(obj)),
  del: (id) => tx(name, 'readwrite', s => s.delete(id)),
  clear: () => tx(name, 'readwrite', s => s.clear()),
});

export const sessions = col('sessions');
export const body = col('body');
export const photos = col('photos');
export const food = col('food');
export const recipes = col('recipes');

export const uid = (p = '') => p + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

function blobToDataURL(blob) {
  return new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(blob); });
}
async function dataURLToBlob(url) { return (await fetch(url)).blob(); }

export async function exportAll(includePhotos = true) {
  const out = { app: 'forge', version: 1, exported: new Date().toISOString(), kv: {} };
  for (const k of ['profile', 'program', 'customExercises', 'settings', 'water']) out.kv[k] = await kv.get(k);
  for (const s of ['sessions', 'body', 'food', 'recipes']) out[s] = await col(s).all();
  if (includePhotos) {
    const ph = await photos.all();
    out.photos = await Promise.all(ph.map(async p => ({ ...p, blob: await blobToDataURL(p.blob) })));
  }
  return out;
}

export async function importAll(data) {
  if (!data || data.app !== 'forge') throw new Error('Fichier de sauvegarde FORGE invalide');
  for (const [k, v] of Object.entries(data.kv || {})) if (v !== undefined && v !== null) await kv.set(k, v);
  for (const s of ['sessions', 'body', 'food', 'recipes']) for (const o of data[s] || []) await col(s).put(o);
  for (const p of data.photos || []) await photos.put({ ...p, blob: await dataURLToBlob(p.blob) });
}

export async function wipe() {
  for (const s of STORES) await col(s).clear();
}
