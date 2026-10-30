/* Ventes enregistrées sur le téléphone sans réseau, puis envoyées au serveur. */
(function () {
  var CLE = 'mc_ventes_attente';
  function lire() { try { return JSON.parse(localStorage.getItem(CLE) || '[]'); } catch (e) { return []; } }
  function ecrire(l) { localStorage.setItem(CLE, JSON.stringify(l)); majIndicateur(); }
  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'v-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  }
  var envoiEnCours = false;

  function majIndicateur() {
    var el = document.getElementById('indicateur-reseau');
    if (!el) return;
    var n = lire().length, horsLigne = navigator.onLine === false;
    el.hidden = !n && !horsLigne;
    var court = window.innerWidth < 480;
    el.textContent = horsLigne ? (n ? 'Hors ligne · ' + n + (court ? '' : ' en attente') : 'Hors ligne')
                               : n + (court ? ' à envoyer' : ' vente' + (n > 1 ? 's' : '') + ' à envoyer');
    el.className = 'badge ' + (horsLigne ? 'badge-retard' : 'badge-urgent');
    document.dispatchEvent(new CustomEvent('mc-attente', { detail: { n: n, horsLigne: horsLigne } }));
  }

  function synchroniser() {
    var ventes = lire();
    if (!ventes.length || envoiEnCours || navigator.onLine === false) return Promise.resolve(null);
    envoiEnCours = true;
    return fetch('/api/synchro', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF': window.CSRF || '' },
      body: JSON.stringify({ ventes: ventes })
    }).then(function (r) {
      return r.json().then(function (d) { return { statut: r.status, d: d }; });
    }).then(function (res) {
      if (res.statut !== 200) throw new Error(res.d && res.d.message || 'Envoi refusé');
      var recus = {}, rapport = [];
      (res.d.resultats || []).forEach(function (x) {
        if (x.ok) recus[x.uuid] = true;
        rapport.push(x);
      });
      ecrire(lire().filter(function (v) { return !recus[v.uuid]; }));
      localStorage.setItem('mc_dernier_envoi', JSON.stringify({ quand: new Date().toISOString(), rapport: rapport }));
      document.dispatchEvent(new CustomEvent('mc-synchro', { detail: { rapport: rapport } }));
      return rapport;
    }).catch(function (err) {
      document.dispatchEvent(new CustomEvent('mc-synchro-erreur', { detail: { message: err.message } }));
      return null;
    }).finally(function () { envoiEnCours = false; });
  }

  window.MC = {
    attente: lire,
    ajouter: function (vente) { vente.uuid = vente.uuid || uuid(); vente.cree_le = new Date().toISOString(); var l = lire(); l.push(vente); ecrire(l); return vente; },
    retirer: function (id) { ecrire(lire().filter(function (v) { return v.uuid !== id; })); },
    synchroniser: synchroniser,
    majIndicateur: majIndicateur
  };

  window.addEventListener('online', function () { majIndicateur(); synchroniser(); });
  window.addEventListener('offline', majIndicateur);
  document.addEventListener('DOMContentLoaded', function () { majIndicateur(); synchroniser(); });
  setInterval(function () { if (lire().length) synchroniser(); }, 30000);

  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
  }
})();
