// FORGE — appareils connectés.
// • Ceinture / montre cardio Bluetooth (service standard Heart Rate 0x180D) via Web Bluetooth.
//   Fonctionne sur Chrome Android, Chrome/Edge ordinateur. Sur iPhone : navigateur « Bluefy ».
// • Import de fichiers GPX / TCX exportés depuis Strava, Garmin Connect, Apple Santé (via apps tierces), Polar, Coros…

export const hr = {
  device: null, bpm: null, samples: [], listeners: new Set(),
  supported: () => 'bluetooth' in navigator,
  async connect() {
    if (!this.supported()) throw new Error('Bluetooth non disponible dans ce navigateur. Sur iPhone, ouvre FORGE dans l’app « Bluefy » ; sur Android, utilise Chrome.');
    const device = await navigator.bluetooth.requestDevice({ filters: [{ services: ['heart_rate'] }] });
    const server = await device.gatt.connect();
    const service = await server.getPrimaryService('heart_rate');
    const ch = await service.getCharacteristic('heart_rate_measurement');
    await ch.startNotifications();
    ch.addEventListener('characteristicvaluechanged', (e) => {
      const v = e.target.value, flags = v.getUint8(0);
      const bpm = flags & 1 ? v.getUint16(1, true) : v.getUint8(1);
      this.bpm = bpm; this.samples.push([Date.now(), bpm]);
      if (this.samples.length > 20000) this.samples.shift();
      this.listeners.forEach(fn => fn(bpm));
    });
    device.addEventListener('gattserverdisconnected', () => { this.device = null; this.bpm = null; this.listeners.forEach(fn => fn(null)); });
    this.device = device;
    return device.name || 'Capteur cardio';
  },
  disconnect() { if (this.device?.gatt?.connected) this.device.gatt.disconnect(); this.device = null; this.bpm = null; },
  stats(since) {
    const s = this.samples.filter(([t]) => t >= since).map(([, b]) => b);
    if (!s.length) return null;
    return { avg: Math.round(s.reduce((a, b) => a + b, 0) / s.length), max: Math.max(...s) };
  },
};

function haversine(a, b) {
  const R = 6371, toR = (d) => d * Math.PI / 180;
  const dLat = toR(b.lat - a.lat), dLon = toR(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toR(a.lat)) * Math.cos(toR(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

// Retourne { name, type, start, minutes, km, avgHr, maxHr, kcal }
export function parseActivity(text, filename = '') {
  const doc = new DOMParser().parseFromString(text, 'application/xml');
  if (doc.querySelector('parsererror')) throw new Error('Fichier illisible');
  const q = (el, tag) => el.getElementsByTagNameNS('*', tag);
  const isTcx = q(doc, 'TrainingCenterDatabase').length > 0;
  let points = [];
  if (isTcx) {
    for (const tp of q(doc, 'Trackpoint')) {
      const t = q(tp, 'Time')[0]?.textContent;
      const lat = q(tp, 'LatitudeDegrees')[0]?.textContent, lon = q(tp, 'LongitudeDegrees')[0]?.textContent;
      const hrv = q(tp, 'HeartRateBpm')[0] ? q(q(tp, 'HeartRateBpm')[0], 'Value')[0]?.textContent : null;
      points.push({ t: t ? Date.parse(t) : null, lat: lat ? +lat : null, lon: lon ? +lon : null, hr: hrv ? +hrv : null });
    }
  } else {
    for (const tp of q(doc, 'trkpt')) {
      const t = q(tp, 'time')[0]?.textContent;
      const hrEl = q(tp, 'hr')[0];
      points.push({ t: t ? Date.parse(t) : null, lat: +tp.getAttribute('lat'), lon: +tp.getAttribute('lon'), hr: hrEl ? +hrEl.textContent : null });
    }
  }
  points = points.filter(p => p.t);
  if (!points.length) throw new Error('Aucun point d’activité trouvé');
  let km = 0;
  for (let i = 1; i < points.length; i++) if (points[i].lat != null && points[i - 1].lat != null) km += haversine(points[i - 1], points[i]);
  if (isTcx) {
    const dist = [...q(doc, 'Lap')].reduce((s, l) => s + (+q(l, 'DistanceMeters')[0]?.textContent || 0), 0);
    if (dist) km = dist / 1000;
  }
  const kcalTcx = isTcx ? [...q(doc, 'Lap')].reduce((s, l) => s + (+q(l, 'Calories')[0]?.textContent || 0), 0) : 0;
  const hrs = points.map(p => p.hr).filter(Boolean);
  const sport = isTcx ? (q(doc, 'Activity')[0]?.getAttribute('Sport') || '') : (q(doc, 'type')[0]?.textContent || '');
  const name = (q(doc, 'name')[0]?.textContent || filename.replace(/\.(gpx|tcx)$/i, '') || 'Activité importée').trim();
  const s = sport.toLowerCase();
  const type = /bik|cycl|vélo|ride/.test(s + name.toLowerCase()) ? 'bike' : /walk|marche|hik/.test(s + name.toLowerCase()) ? 'brisk_walk' : /row/.test(s) ? 'rower' : 'run';
  return {
    name, type,
    start: new Date(points[0].t).toISOString(),
    minutes: Math.round((points[points.length - 1].t - points[0].t) / 60000),
    km: Math.round(km * 100) / 100,
    avgHr: hrs.length ? Math.round(hrs.reduce((a, b) => a + b, 0) / hrs.length) : null,
    maxHr: hrs.length ? Math.max(...hrs) : null,
    kcal: kcalTcx || null,
  };
}
