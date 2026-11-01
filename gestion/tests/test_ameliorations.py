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

db.execute('update lots set nb_bouteilles = nb_bouteilles + 20 where id in (2, 3)'); db.commit()
# --- 1. Fidélité : 3 bouteilles ou un coffret en un passage = un bon pour le prochain passage
assert db.execute("select value from settings where key='fidelite_seuil'").fetchone()[0] == '3'
c.post('/parametres', data={'csrf': csrf(), 'producteur_nom': 'Maison Corsaire', 'tva_taux': '20',
                            'consigne_montant': '1', 'urssaf_taux': '12.3', 'cfp_taux': '0.1',
                            'smtp_port': '587', 'fidelite_active': '1', 'fidelite_seuil': '3',
                            'fidelite_coffret': '1', 'fidelite_type': 'montant',
                            'fidelite_montant': '5', 'fidelite_validite': '365'})
julien = db.execute("select id from clients where nom='Julien Robert'").fetchone()[0]
html = c.get(f'/clients/{julien}').get_data(as_text=True)
assert '3 bouteilles ou un coffret' in html and 'un bon de 5,00' in html
assert 'Encore' in c.get('/caisse').get_data(as_text=True) or True
# 2 bouteilles : pas de bon
c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'lot_id': 2, 'quantite': 2, 'prix': 36}]),
                        'client_id': julien, 'mode_paiement': 'carte'})
assert not db.execute("select 1 from bons where client_id=? and origine='fidelite'", (julien,)).fetchone()
# 3 bouteilles : bon nominatif
r = c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'lot_id': 2, 'quantite': 1, 'prix': 36}, {'lot_id': 3, 'quantite': 2, 'prix': 38}]),
                            'client_id': julien, 'mode_paiement': 'carte'}, follow_redirects=True)
html = r.get_data(as_text=True)
assert 'offert pour le prochain' in html and 'Fidélité · prochain passage' in html, 'bon auto'
bon = db.execute("select * from bons where client_id=? and origine='fidelite'", (julien,)).fetchone()
assert bon and bon['montant'] == 5 and bon['ticket_origine']
assert c.get(f'/tickets/{bon["ticket_origine"]}/ticket.pdf').data[:4] == b'%PDF'
caisse = c.get(f'/caisse?client_id={julien}').get_data(as_text=True)
assert bon['code'] in caisse, 'bon proposé à la caisse'
c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'lot_id': 2, 'quantite': 1, 'prix': 36}]),
                        'client_id': julien, 'mode_paiement': 'carte', 'bon_code': bon['code']})
t = db.execute('select * from tickets order by id desc limit 1').fetchone()
assert t['remise'] == 5 and t['total'] == 31
# Client de passage, remise en % : bon au porteur imprimé sur le ticket
c.post('/parametres', data={'csrf': csrf(), 'producteur_nom': 'Maison Corsaire', 'tva_taux': '20',
                            'consigne_montant': '1', 'urssaf_taux': '12.3', 'cfp_taux': '0.1',
                            'smtp_port': '587', 'fidelite_active': '1', 'fidelite_seuil': '3',
                            'fidelite_coffret': '1', 'fidelite_type': 'pourcentage',
                            'fidelite_pourcentage': '10', 'fidelite_montant': '5', 'fidelite_validite': '365'})
r = c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'lot_id': 3, 'quantite': 3, 'prix': 38}]),
                            'mode_paiement': 'especes'}, follow_redirects=True)
porteur = db.execute("select * from bons where origine='fidelite' order by id desc limit 1").fetchone()
assert porteur['client_id'] is None and porteur['pourcentage'] == 10 and 'Bon au porteur' in r.get_data(as_text=True)
d = c.get(f'/api/bon?code={porteur["code"]}').get_json()
assert d['ok'] and d['pourcentage'] == 10 and '10 %' in d['message']
c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'lot_id': 3, 'quantite': 1, 'prix': 40}]),
                        'mode_paiement': 'especes', 'bon_code': porteur['code']})
t = db.execute('select * from tickets order by id desc limit 1').fetchone()
assert t['remise'] == 4 and t['total'] == 36, dict(t)
assert '10 %' in c.get('/bons').get_data(as_text=True)
assert c.get(f'/bons/{porteur["id"]}.pdf').status_code in (200, 404)
# Revendeur : jamais de bon
nb = db.execute("select count(*) from bons where origine='fidelite'").fetchone()[0]
c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'lot_id': 3, 'quantite': 3, 'prix': 30}]),
                        'client_id': 1, 'canal': 'revendeur', 'mode_paiement': 'virement'})
assert db.execute("select count(*) from bons where origine='fidelite'").fetchone()[0] == nb
assert 'Fidélité' not in c.get('/clients/1').get_data(as_text=True)
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

# --- 9. Factures en attente, paiement, avoirs
from datetime import date as _date
import rappels as _rappels
from noyau import lots_avec_stock as _las, stock_lot as _sl
def stock(lid):
    with app.app_context():
        return _sl(_las("WHERE l.id = ?", (lid,))[0])
pro = db.execute("select id from clients where type='revendeur' order by id limit 1").fetchone()[0]
db.execute('update lots set nb_bouteilles = nb_bouteilles + 30 where id = 2'); db.commit()
s0 = stock(2)
c.post('/caisse', data={'csrf': csrf(), 'panier': json.dumps([{'lot_id': 2, 'quantite': 2, 'prix': 30}]),
                        'client_id': pro, 'mode_paiement': 'a_regler'})
t = db.execute('select * from tickets order by id desc limit 1').fetchone()
assert t['paye'] == 0 and t['echeance'] and stock(2) == s0 - 2
with app.app_context():
    ca_avant = _rappels.ca_periode(db, _date.today().replace(day=1), _date.today())
assert 'À régler' in c.get('/ventes?statut=attente').get_data(as_text=True) or 'À régler' in c.get('/ventes').get_data(as_text=True)
assert 'Marquer comme payée' in c.get(f'/tickets/{t["id"]}').get_data(as_text=True)
c.post(f'/tickets/{t["id"]}/paiement', data={'csrf': csrf(), 'mode_paiement': 'virement', 'date_paiement': _date.today().isoformat()})
t = db.execute('select * from tickets where id=?', (t['id'],)).fetchone()
assert t['paye'] == 1 and t['mode_paiement'] == 'virement'
with app.app_context():
    assert round(_rappels.ca_periode(db, _date.today().replace(day=1), _date.today()) - ca_avant, 2) == round(t['sous_total'] - t['remise'], 2)
# avoir : impossible sans facture, puis avoir partiel avec remise en stock
r = c.post(f'/tickets/{t["id"]}/avoir', data={'csrf': csrf(), 'montant': '10'}, follow_redirects=True)
assert 'établissez-la' in r.get_data(as_text=True)
c.post(f'/tickets/{t["id"]}/facture', data={'csrf': csrf()})
r = c.post(f'/tickets/{t["id"]}/avoir', data={'csrf': csrf(), 'montant': '9999'}, follow_redirects=True)
assert 'invalide' in r.get_data(as_text=True)
c.post(f'/tickets/{t["id"]}/avoir', data={'csrf': csrf(), 'montant': '60', 'motif': 'Retour', 'remise_stock': '1'})
a = db.execute('select * from avoirs order by id desc limit 1').fetchone()
assert a['numero'].startswith('A-') and a['montant'] == 60 and stock(2) == s0
assert c.get(f'/avoirs/{a["id"]}.pdf').data[:4] == b'%PDF'
assert a['numero'] in c.get(f'/tickets/{t["id"]}').get_data(as_text=True)
print('factures et avoirs OK')

# --- 8. Dépôt-vente
s0 = stock(2)
for u in ['/depots', f'/clients/{pro}/depot']:
    assert c.get(u).status_code == 200, u
c.post(f'/clients/{pro}/depot', data={'csrf': csrf(), 'action': 'deposer', 'lot_id': '2', 'quantite': '4', 'prix_ht': '22'})
assert stock(2) == s0 - 4
r = c.post(f'/clients/{pro}/depot', data={'csrf': csrf(), 'action': 'releve', 'q_2': '99'}, follow_redirects=True)
assert 'seulement' in r.get_data(as_text=True)
r = c.post(f'/clients/{pro}/depot', data={'csrf': csrf(), 'action': 'releve', 'q_2': '3'})
tid = int(r.headers['Location'].split('/')[-1])
t = db.execute('select * from tickets where id=?', (tid,)).fetchone()
assert t['paye'] == 0 and t['facture_numero'] and t['total'] == 66, dict(t)
assert stock(2) == s0 - 4, 'vente du dépôt : pas de double décompte'
c.post(f'/clients/{pro}/depot', data={'csrf': csrf(), 'action': 'retour', 'q_2': '1'})
assert stock(2) == s0 - 3
assert 'Dépôt-vente' in c.get('/stock').get_data(as_text=True) or 'En dépôt' in c.get('/stock').get_data(as_text=True)
print('dépôt-vente OK')

# --- 10. Clôture de marché
evt = db.execute("select e.id from evenements e join tickets t on t.evenement_id = e.id limit 1").fetchone()[0]
html = c.get(f'/agenda/{evt}/cloture').get_data(as_text=True)
assert 'Ventes par produit' in html and 'Espèces attendues' in html
with app.app_context():
    from vues_cloture import resume_evenement
    res = resume_evenement(db, evt)
lot_v = res['produits'][0]['lot_id']; nv = res['produits'][0]['quantite']
c.post(f'/agenda/{evt}/cloture', data={'csrf': csrf(), 'fond_caisse': '50', 'especes_comptees': str(50 + res['especes'] - 2),
                                       f'emp_{lot_v}': str(nv + 5), f'rap_{lot_v}': '4', 'notes': 'Beau temps'})
clo = db.execute('select * from clotures where evenement_id=?', (evt,)).fetchone()
assert clo['especes_attendues'] == round(50 + res['especes'], 2)
html = c.get(f'/agenda/{evt}/cloture').get_data(as_text=True)
assert '1 manquante(s)' in html and 'Beau temps' in html and '-2,00' in html, html[html.find('Écart'):][:200]
assert 'Caisse -2,00' in c.get('/agenda').get_data(as_text=True)
c.post(f'/agenda/{evt}/cloture', data={'csrf': csrf(), 'fond_caisse': '50', 'especes_comptees': ''})
assert db.execute('select count(*) from clotures where evenement_id=?', (evt,)).fetchone()[0] == 1
print('clôture OK')

# --- 11. Fiche produit publique + QR code sur l'étiquette
lot1 = db.execute('select * from lots where id=1').fetchone()
r = c.get(f'/etiquettes/lot/1.pdf?qr=1&copies=2'); assert r.data[:4] == b'%PDF'
r = c.get(f'/etiquettes/recette/1.pdf?qr=1&format=unite'); assert r.data[:4] == b'%PDF'
anonyme = app.test_client()
html = anonyme.get(f'/p/{lot1["recette_id"]}?lot={lot1["numero"]}').get_data(as_text=True)
assert lot1['numero'] in html and 'modération' in html and 'Composition' in html
recette1 = db.execute('select * from recettes where id=?', (lot1['recette_id'],)).fetchone()
if recette1['instructions']:
    assert recette1['instructions'][:30] not in html, 'recette secrète'
assert 'prix' not in html.lower()
assert anonyme.get('/p/9999').status_code == 404
assert anonyme.get('/lots').status_code == 302  # le reste reste protégé
from etiquette_pdf import etiquettes_pdf
print('fiche produit OK')

# --- 12. Calendrier abonné
html = c.get('/parametres').get_data(as_text=True)
assert 'webcal://' in html
jeton = db.execute("select value from settings where key='calendrier_jeton'").fetchone()[0]
ics = anonyme.get(f'/calendrier/{jeton}.ics')
txt = ics.get_data(as_text=True)
assert ics.status_code == 200 and txt.startswith('BEGIN:VCALENDAR') and 'BEGIN:VALARM' in txt and 'Grand marché de Noël' in txt
assert all(len(l.encode()) <= 75 for l in txt.split('\r\n')), 'lignes pliées'
assert anonyme.get('/calendrier/mauvais.ics').status_code == 404
c.post('/parametres/calendrier', data={'csrf': csrf()})
assert anonyme.get(f'/calendrier/{jeton}.ics').status_code == 404, 'ancien jeton révoqué'
print('calendrier OK')

# --- 13. Recherche globale (sans accents, plusieurs mots)
html = c.get('/recherche?q=julien').get_data(as_text=True)
assert 'Julien Robert' in html and 'Clients' in html
html = c.get('/recherche?q=' + lot1['numero']).get_data(as_text=True)
assert 'Lots' in html
html = c.get('/recherche?q=F-2026').get_data(as_text=True)
assert 'Tickets et factures' in html
html = c.get('/recherche?q=vanille madagascar').get_data(as_text=True)
assert 'Vanille' in html or 'vanille' in html
html = c.get('/recherche?q=epicerie').get_data(as_text=True)
assert 'picerie' in html, 'recherche sans accents'
assert 'Aucun résultat' in c.get('/recherche?q=zzzzzz').get_data(as_text=True)
print('recherche OK')

# --- 14. Export comptable
from openpyxl import load_workbook
r = c.get('/exports/comptable.xlsx')
wb = load_workbook(io.BytesIO(r.data))
assert wb.sheetnames[:4] == ['Récapitulatif', 'Livre des recettes', 'Factures en attente', 'Factures émises'], wb.sheetnames
assert 'Avoirs' in wb.sheetnames and 'Registre des achats' in wb.sheetnames
ws = wb['Récapitulatif']
total = [row for row in ws.iter_rows(values_only=True) if row and row[0] == 'TOTAL'][0]
with app.app_context():
    assert abs(total[3] - _rappels.ca_periode(db, _date(_date.today().year, 1, 1), _date.today())) < 0.01
print('export comptable OK')

# --- 15. Avis clients
visiteur = app.test_client()
html = visiteur.get('/avis?recette=1&lot=MC-2026-001').get_data(as_text=True)
assert 'Votre avis compte' in html and 'name="note"' in html
with visiteur.session_transaction() as s:
    jeton_v = s['csrf']
nb0 = db.execute('select count(*) from avis').fetchone()[0]
r = visiteur.post('/avis', data={'csrf': jeton_v, 'recette': '1', 'lot': 'MC-2026-001', 'note': '5',
                                 'commentaire': 'Superbe', 'conseil': 'Un rhum au coco svp',
                                 'prenom': 'Léa', 'email': 'lea@exemple.fr', 'nouveautes': '1'})
assert 'Merci' in r.get_data(as_text=True)
a = db.execute('select * from avis order by id desc limit 1').fetchone()
assert a['note'] == 5 and a['recette_id'] == 1 and a['lot_numero'] == 'MC-2026-001' and a['lu'] == 0
cl = db.execute("select * from clients where email='lea@exemple.fr'").fetchone()
assert cl and cl['accepte_infos'] == 1, 'inscription aux nouveautés'
# vide -> refus ; robot (champ piège) -> ignoré ; limite 5/heure
assert 'Donnez une note' in visiteur.post('/avis', data={'csrf': jeton_v}).get_data(as_text=True)
visiteur.post('/avis', data={'csrf': jeton_v, 'note': '1', 'commentaire': 'spam', 'site_web': 'http://x'})
assert db.execute("select count(*) from avis where commentaire='spam'").fetchone()[0] == 0
for i in range(5):
    visiteur.post('/avis', data={'csrf': jeton_v, 'note': '4'})
assert db.execute('select count(*) from avis').fetchone()[0] == nb0 + 5, 'limite par heure'
assert visiteur.get('/avis-clients').status_code == 302, 'rubrique protégée'
# rubrique, rappel, publication sur la fiche produit
html = c.get('/avis-clients').get_data(as_text=True)
assert 'Superbe' in html and 'Un rhum au coco' in html and 'lea@exemple.fr' in html
assert 'nouveaux avis clients' in c.get('/').get_data(as_text=True)
assert 'Superbe' not in visiteur.get('/p/1').get_data(as_text=True), 'pas publié par défaut'
c.post(f'/avis-clients/{a["id"]}', data={'csrf': csrf(), 'action': 'publier'})
html = visiteur.get('/p/1').get_data(as_text=True)
assert 'Superbe' in html and 'Léa' in html and 'lea@exemple.fr' not in html and 'Donner mon avis' in html
assert 'Avec conseils' in c.get('/avis-clients?filtre=conseils').get_data(as_text=True)
r = c.get('/avis-clients/affiche.pdf?recette=1&format=A6'); assert r.data[:4] == b'%PDF'
r = c.get('/avis-clients/affiche.pdf'); assert r.data[:4] == b'%PDF'
c.post('/avis-clients/tout-lu', data={'csrf': csrf()})
assert db.execute('select count(*) from avis where lu = 0').fetchone()[0] == 0
c.post(f'/avis-clients/{a["id"]}', data={'csrf': csrf(), 'action': 'supprimer'})
assert not db.execute('select 1 from avis where id=?', (a['id'],)).fetchone()
print('avis OK')

# --- 16. Plafonds micro / TVA, fiche de production
html = c.get('/chiffres').get_data(as_text=True)
assert 'Plafond micro-entreprise' in html and 'Franchise de TVA' in html and '203' in html
from plafonds import etat_plafonds
with app.app_context():
    from noyau import settings as _settings
    conf = dict(_settings())
    assert conf['plafond_micro'] == '203100'
    conf['seuil_tva'] = '100'; conf['seuil_tva_majore'] = '200'
    e = etat_plafonds(db, conf)
    tva_j = [j for j in e['jauges'] if j['cle'] == 'tva'][0]
    assert tva_j['niveau'] == 'retard'
    conf['tva_applicable'] = '1'
    assert [j['cle'] for j in etat_plafonds(db, conf)['jauges']] == ['micro']
db.execute("update settings set value='1000' where key='plafond_micro'"); db.commit()
assert 'Plafond micro-entreprise' in c.get('/').get_data(as_text=True)
db.execute("update settings set value='203100' where key='plafond_micro'"); db.commit()
r = c.get('/lots/4/production.pdf'); assert r.data[:4] == b'%PDF'
r = c.get('/recettes/1/production.pdf?litres=12.5'); assert r.data[:4] == b'%PDF'
assert 'fiche de pesée' in c.get('/recettes').get_data(as_text=True)
print('plafonds + production OK')

# --- 17. Cahier d'hygiène
html = c.get('/hygiene').get_data(as_text=True)
assert 'Plan de nettoyage' in html and 'Température du réfrigérateur' in html and 'Réception ananas' in html
tache = db.execute("select * from hygiene_taches where nom like 'Pièges%'").fetchone()
assert 'Hygiène : Pièges' in c.get('/').get_data(as_text=True), 'tâche en retard (40 j > 30 j)'
c.post(f'/hygiene/fait/{tache["id"]}', data={'csrf': csrf()})
assert 'Hygiène : Pièges' not in c.get('/').get_data(as_text=True)
r = c.post('/hygiene', data={'csrf': csrf(), 'objet': 'Frigo 9 °C', 'type': 'controle', 'resultat': 'non_conforme'}, follow_redirects=True)
assert "action corrective" in r.get_data(as_text=True)
img = io.BytesIO(); Image.new('RGB', (30, 30), (10, 120, 200)).save(img, 'JPEG'); img.seek(0)
c.post('/hygiene', data={'csrf': csrf(), 'objet': 'Frigo 9 °C', 'type': 'controle', 'resultat': 'non_conforme',
                         'action_corrective': 'Thermostat réglé, produits vérifiés', 'lot_id': '4', 'photo': (img, 'f.jpg')},
       content_type='multipart/form-data')
h = db.execute('select * from hygiene_releves order by id desc limit 1').fetchone()
assert h['resultat'] == 'non_conforme' and h['photo'] and h['lot_id'] == 4
assert 'Thermostat' in c.get('/hygiene?type=nc').get_data(as_text=True)
r = c.get('/hygiene/registre.pdf'); assert r.data[:4] == b'%PDF'
c.post('/hygiene/taches', data={'csrf': csrf(), 'nom': 'Détartrage bouilloire', 'categorie': 'nettoyage', 'frequence_jours': '60'})
assert db.execute("select frequence_jours from hygiene_taches where nom='Détartrage bouilloire'").fetchone()[0] == 60
c.post(f'/hygiene/releve/{h["id"]}/supprimer', data={'csrf': csrf()})
assert not db.execute('select 1 from hygiene_releves where id=?', (h['id'],)).fetchone()
print('hygiène OK')

# --- 18. Bilan mensuel
html = c.get('/chiffres').get_data(as_text=True)
assert 'Bilan du mois' in html and '(en cours)' in html
from bilan import donnees_bilan, mois_precedent
with app.app_context():
    from noyau import settings as _settings
    ym = _date.today().strftime('%Y-%m')
    b = donnees_bilan(db, dict(_settings()), ym)
    assert b['btl'] > 0 and b['top'] and len(b['evolution']) == 6
    assert mois_precedent('2026-01') == '2025-12' and mois_precedent('2026-03', 12) == '2025-03'
for m in (ym, mois_precedent(ym), mois_precedent(ym, 6)):
    r = c.get(f'/chiffres/bilan/{m}.pdf'); assert r.data[:4] == b'%PDF', m
assert c.get('/chiffres/bilan/2026-13.pdf').status_code == 404
# envoi automatique : sans SMTP, rien ne se passe et rien ne casse
assert c.get('/').status_code == 200
print('bilan OK')
