"""Améliorations : fidélité, sauvegardes, formats, coffrets... Lancer depuis gestion/ : python tests/test_ameliorations.py"""
import json
import os
import sqlite3
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="corsaire-test-")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as _  # noqa: E402,F401
from noyau import app  # noqa: E402

c = app.test_client()
c.get('/connexion')
def csrf():
    with c.session_transaction() as s:
        return s['csrf']
c.post('/connexion', data={'email': 'contact@maisoncorsaire.fr', 'password': 'corsaire2026', 'csrf': csrf()})
db = sqlite3.connect(app.config['DATABASE'])
db.row_factory = sqlite3.Row

# --- 1. Fidélité : seuil 3 tampons pour tester, client Julien (1 bouteille déjà achetée)
c.post('/parametres', data={'csrf': csrf(), 'producteur_nom': 'Maison Corsaire', 'tva_taux': '20',
                            'consigne_montant': '1', 'urssaf_taux': '12.3', 'cfp_taux': '0.1',
                            'smtp_port': '587', 'fidelite_active': '1', 'fidelite_seuil': '3',
                            'fidelite_montant': '5', 'fidelite_validite': '365',
                            'fidelite_bonus_consigne': '1'})
julien = db.execute("select id from clients where nom='Julien Robert'").fetchone()[0]
html = c.get(f'/clients/{julien}').get_data(as_text=True)
assert 'Carte de fidélité' in html and '1/3' in html, ('carte', db.execute("select value from settings where key='fidelite_seuil'").fetchone()[0], html[html.find('<strong>', html.find('Carte de fid')):][:40])
r = c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'lot_id': 2, 'quantite': 2, 'prix': 36}]),
                            'client_id': julien, 'mode_paiement': 'carte'}, follow_redirects=True)
assert 'Carte de fidélité complète' in r.get_data(as_text=True), 'bon auto'
bon = db.execute("select * from bons where client_id=? and origine='fidelite'", (julien,)).fetchone()
assert bon and bon['montant'] == 5
caisse = c.get(f'/caisse?client_id={julien}').get_data(as_text=True)
assert bon['code'] in caisse, 'bon proposé à la caisse'
assert '0/3' in c.get(f'/clients/{julien}').get_data(as_text=True)
r = c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'lot_id': 2, 'quantite': 1, 'prix': 36}]),
                            'client_id': julien, 'mode_paiement': 'carte', 'bon_code': bon['code']})
t = db.execute('select * from tickets order by id desc limit 1').fetchone()
assert t['remise'] == 5 and t['total'] == 31
# Revendeur : pas de carte
assert 'Carte de fidélité' not in c.get('/clients/1').get_data(as_text=True)
print('fidélité OK')

# --- 2. Sauvegardes : copie du jour automatique, manuelle, restauration
from pathlib import Path
from datetime import date
dossier = Path(os.environ["DATA_DIR"]) / "sauvegardes"
assert (dossier / f"corsaire-{date.today().isoformat()}.db").exists(), 'sauvegarde du jour'
nb_clients = db.execute('select count(*) from clients').fetchone()[0]
c.post('/parametres/sauvegardes/maintenant', data={'csrf': csrf()})
manuelle = sorted(dossier.glob('corsaire-manuelle-*.db'))[-1].name
c.post('/clients/nouveau', data={'csrf': csrf(), 'nom': 'Client à effacer', 'type': 'particulier'})
assert db.execute('select count(*) from clients').fetchone()[0] == nb_clients + 1
r = c.post('/parametres/sauvegardes/restaurer', data={'csrf': csrf(), 'nom': manuelle, 'confirmation': 'non'}, follow_redirects=True)
assert 'Tapez CONFIRMER' in r.get_data(as_text=True)
c.post('/parametres/sauvegardes/restaurer', data={'csrf': csrf(), 'nom': manuelle, 'confirmation': 'CONFIRMER'})
assert db.execute('select count(*) from clients').fetchone()[0] == nb_clients, 'restauration'
assert list(dossier.glob('corsaire-avant-restauration-*.db')), 'filet de sécurité'
assert c.get(f'/parametres/sauvegardes/{manuelle}').status_code == 200
assert c.get('/parametres/sauvegardes/..%2Fcorsaire.db').status_code == 404
z = c.get('/parametres/sauvegarde-complete.zip'); assert z.data[:2] == b'PK'
assert 'Sauvegardes' in c.get('/parametres').get_data(as_text=True)
print('sauvegardes OK')
