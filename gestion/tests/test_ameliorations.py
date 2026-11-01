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

# --- 3a. Plusieurs formats : le lot 4 (prêt) embouteillé en 50 cl et en 20 cl
cur = db.execute("INSERT INTO materiaux (nom, type, stock, seuil_alerte, cout_unitaire, par_bouteille, format_cl) VALUES ('Flasque 20 cl','bouteille',50,10,0.8,1,20)")
db.commit()
flasque20 = cur.lastrowid
stock50 = db.execute("select stock from materiaux where nom='Bouteille flasque 50 cl'").fetchone()[0]
bouchons = db.execute("select stock from materiaux where nom='Bouchon liège tête bois'").fetchone()[0]
r = c.post('/lots/4/statut', data={'csrf': csrf(), 'statut': 'embouteille', 'volume_obtenu_l': '12',
                                  'nb_bouteilles': '16', 'format_cl': ['20', ''], 'format_nb': ['20', '']},
           follow_redirects=True)
assert 'Format supplémentaire créé' in r.get_data(as_text=True)
enfant = db.execute("select * from lots where parent_id=4").fetchone()
assert enfant['volume_cl'] == 20 and enfant['nb_bouteilles'] == 20 and enfant['statut'] == 'embouteille'
assert enfant['numero'].endswith('-004-20'), enfant['numero']
assert db.execute("select stock from materiaux where id=?", (flasque20,)).fetchone()[0] == 30
assert db.execute("select stock from materiaux where nom='Bouteille flasque 50 cl'").fetchone()[0] == stock50 - 16
assert db.execute("select stock from materiaux where nom='Bouchon liège tête bois'").fetchone()[0] == bouchons - 36
from calculs import cout_revient
from noyau import settings as _settings
with app.test_request_context():
    from noyau import get_db, get_lot
    parent, fils = get_lot(4), get_lot(enfant['id'])
    total_ing = get_db().execute('select sum(cout) from lot_ingredients where lot_id=4').fetchone()[0]
    c50 = cout_revient(get_db(), parent, _settings())['ingredients_bouteille']
    c20 = cout_revient(get_db(), fils, _settings())['ingredients_bouteille']
assert abs(c50 * 16 + c20 * 20 - total_ing) < 0.01 and abs(c20 / c50 - 0.4) < 0.001, (c50, c20)
for u in ['/lots/4', f'/lots/{enfant["id"]}', f'/lots/{enfant["id"]}/fiche', f'/etiquettes/lot/{enfant["id"]}.pdf']:
    assert c.get(u).status_code == 200, u
assert "Lot d'origine" in c.get(f'/lots/{enfant["id"]}').get_data(as_text=True)
print('formats OK')

# --- 3b. Coffret : 1 × Ananas 20 cl + 1 × Café 50 cl, vendu 45 €
c.post('/coffrets', data={'csrf': csrf(), 'nom': 'Coffret découverte', 'prix_ttc': '45',
                          'materiau_id': str(db.execute("select id from materiaux where nom='Étui kraft + calage'").fetchone()[0]),
                          'el_recette': ['1', '3', ''], 'el_cl': ['20', '50', '20'], 'el_qte': ['1', '1', '1']})
cof = db.execute("select * from coffrets where nom='Coffret découverte'").fetchone()
assert db.execute('select count(*) from coffret_elements where coffret_id=?', (cof['id'],)).fetchone()[0] == 2
assert 'Coffret découverte' in c.get('/caisse').get_data(as_text=True)
etuis = db.execute("select stock from materiaux where nom='Étui kraft + calage'").fetchone()[0]
r = c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'coffret_id': cof['id'], 'quantite': 1, 'prix': 45}]),
                            'mode_paiement': 'especes'})
assert r.status_code == 302, r.get_data(as_text=True)[:400]
t = db.execute('select * from tickets order by id desc limit 1').fetchone()
lignes = db.execute('select v.*, l.volume_cl, l.recette_id from ventes v join lots l on l.id=v.lot_id where ticket_id=?', (t['id'],)).fetchall()
assert t['sous_total'] == 45 and abs(sum(l['quantite'] * l['prix_unitaire_ttc'] for l in lignes) - 45) < 0.001
assert sorted((l['recette_id'], l['volume_cl']) for l in lignes) == [(1, 20), (3, 50)]
assert all(l['notes'] == 'Coffret Coffret découverte' for l in lignes)
assert db.execute("select stock from materiaux where nom='Étui kraft + calage'").fetchone()[0] == etuis - 1
# Coffret offert pour un concours (sortie hors vente)
r = c.post('/sorties', data={'csrf': csrf(), 'coffret_id': str(cof['id']), 'quantite': '1', 'motif': 'concours', 'beneficiaire': 'Gagnant'}, follow_redirects=True)
assert 'sorti du stock' in r.get_data(as_text=True)
assert db.execute("select count(*) from sorties where beneficiaire='Gagnant'").fetchone()[0] == 2
assert c.get('/coffrets').status_code == 200
print('coffrets OK')

# --- 4. Prévision de production
html = c.get('/prevision').get_data(as_text=True)
assert 'Prévision de production' in html and 'Marché de producteurs de Surgères' in html
c.post('/agenda/nouveau', data={'csrf': csrf(), 'nom': 'Grand marché de Noël', 'type': 'marche', 'date_debut': '2026-12-20', 'btl_prevues': '150'})
html = c.get('/prevision').get_data(as_text=True)
assert 'Il manquera' in html and 'Lancer ce lot' in html, 'manque détecté'
assert 'Lancer ' in c.get('/').get_data(as_text=True)
r = c.get('/lots/nouveau?recette_id=1&litres=12.5'); assert 'value="12.5"' in r.get_data(as_text=True)
print('prévision OK')

# --- 5. Lot d'essai et carnet de dégustation (avec photo)
import io
from PIL import Image
r = c.post('/lots/nouveau', data={'csrf': csrf(), 'recette_id': '2', 'recette_nom': '', 'date_maceration': '2026-10-01', 'litres': '1', 'perte_pct': '15', 'volume_cl': '50', 'nb_bouteilles': '1', 'statut': 'maceration', 'essai': '1'})
essai = int(r.headers['Location'].split('/')[-1])
assert db.execute('select essai from lots where id=?', (essai,)).fetchone()[0] == 1
img = io.BytesIO(); Image.new('RGB', (40, 30), (200, 120, 40)).save(img, 'JPEG'); img.seek(0)
c.post(f'/lots/{essai}/degustations', data={'csrf': csrf(), 'date': '2026-10-31', 'note': '4', 'commentaire': 'Très fruité', 'photo': (img, 'photo.jpg')}, content_type='multipart/form-data')
d = db.execute('select * from degustations where lot_id=?', (essai,)).fetchone()
assert d['note'] == 4 and d['photo'] and c.get(f'/photos/{d["photo"]}').status_code == 200
html = c.get(f'/lots/{essai}').get_data(as_text=True)
assert 'J+30' in html and 'Lot d&#39;essai' in html or "Lot d'essai" in html
assert 'Très fruité' in c.get('/degustations').get_data(as_text=True)
assert 'dégustation(s)' in c.get('/recettes').get_data(as_text=True)
print('dégustations OK')

# --- 6. Historique des prix et alerte de hausse (rhum ambré : 17 € puis 19,50 €/L)
c.post('/achats/nouveau', data={'csrf': csrf(), 'fournisseur': 'Distillerie des Alizés', 'date_achat': '2026-10-30', 'mode_paiement': 'virement',
                                'l_article': ['mp:2'], 'l_designation': [''], 'l_qte': ['10'], 'l_unite': ['L'], 'l_montant': ['195']})
html = c.get('/matieres/2').get_data(as_text=True)
assert 'Historique des prix' in html and '+15 %' in html, 'variation'
assert 'Hausse du prix : Rhum ambré 45° +15 %' in c.get('/').get_data(as_text=True)
print('prix OK')
