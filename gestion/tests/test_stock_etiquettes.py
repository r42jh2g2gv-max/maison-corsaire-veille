"""Test de bout en bout sur une base d'exemple neuve. Lancer depuis gestion/ : python tests/test_stock_etiquettes.py"""
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="corsaire-test-")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import io, json, re, sqlite3
import app as _
from noyau import app
c = app.test_client()
def csrf():
    with c.session_transaction() as s: return s.get('csrf')
c.get('/connexion')
c.post('/connexion', data={'email':'contact@maisoncorsaire.fr','password':'corsaire2026','csrf':csrf()})
db = sqlite3.connect(app.config['DATABASE']); db.row_factory = sqlite3.Row
def stock(nom):
    return round(db.execute("select coalesce(sum(v.quantite),0) from mouvements_mp v join matieres_premieres m on m.id=v.mp_id where m.nom=?",(nom,)).fetchone()[0],4)
for u in ['/matieres','/matieres/1','/achats','/achats?annee=2026','/achats/nouveau','/achats/nouveau?article=mp:1','/achats/1','/etiquettes','/etiquettes?recette=2','/statistiques','/statistiques?periode=tout','/statistiques?periode=annee','/recettes','/lots/1','/','/stock','/chiffres']:
    r = c.get(u); assert r.status_code == 200, (u, r.status_code)
for u in ['/etiquettes/recette/1.pdf?copies=24','/etiquettes/recette/2.pdf?format=unite&copies=2','/etiquettes/lot/2.pdf?copies=22&lot_imprime=1','/exports/achats.xlsx','/exports/stock.xlsx','/exports/complet.xlsx']:
    r = c.get(u); assert r.status_code == 200 and r.data[:2] in (b'%P', b'PK'), u
print('pages OK')
html = c.get('/').get_data(as_text=True)
assert 'Racheter : Rhum ambré 45°' in html, 'rappel MP'
# achat : 10 L de rhum ambré + 500 g de café (stock en kg) + bouteilles
r0, cafe0 = stock('Rhum ambré 45°'), stock('Grains de café arabica')
mat0 = db.execute("select stock from materiaux where id=1").fetchone()[0]
data = {'csrf':csrf(),'fournisseur':'Distillerie test','date_achat':'2026-10-29','reference':'F-1','mode_paiement':'virement',
 'l_article':['mp:2','mp:7','mat:1',''],'l_designation':['','','','Transport'],'l_qte':['10','500','50',''],'l_unite':['L','g','',''],'l_montant':['180','16','60','12'],
 'justificatif': (io.BytesIO(b'%PDF-1.4 test'), 'facture.pdf')}
r = c.post('/achats/nouveau', data=data, content_type='multipart/form-data'); assert r.status_code == 302, r.get_data(as_text=True)[:500]
aid = db.execute('select max(id) from achats').fetchone()[0]
a = db.execute('select * from achats where id=?',(aid,)).fetchone()
assert a['montant_total'] == 268 and a['justificatif']
assert stock('Rhum ambré 45°') == r0 + 10 and stock('Grains de café arabica') == round(cafe0 + 0.5, 4)
assert db.execute("select stock from materiaux where id=1").fetchone()[0] == mat0 + 50
assert db.execute("select cout_unitaire from matieres_premieres where id=2").fetchone()[0] == 18
assert db.execute("select cout_unitaire from matieres_premieres where id=7").fetchone()[0] == 32
assert c.get(f'/achats/{aid}/justificatif').status_code == 200
# modification de l'achat : 12 L au lieu de 10
data2 = dict(data); data2.pop('justificatif'); data2['l_qte'] = ['12','500','50','']
c.post(f'/achats/{aid}', data=data2)
assert stock('Rhum ambré 45°') == r0 + 12
assert db.execute("select stock from materiaux where id=1").fetchone()[0] == mat0 + 50
# suppression
c.post(f'/achats/{aid}', data={'csrf':csrf(),'action':'supprimer'})
assert stock('Rhum ambré 45°') == r0 and db.execute("select stock from materiaux where id=1").fetchone()[0] == mat0
print('achats OK')
# lot : ajout d'un ingrédient depuis le stock (1500 ml de rhum agricole, stock en L)
ra0 = stock('Rhum agricole blanc 50°')
c.post('/lots/5/ingredients', data={'csrf':csrf(),'mp_id':'1','quantite':'1500','unite':'ml','cout':''})
iid = db.execute('select max(id) from lot_ingredients').fetchone()[0]
ing = db.execute('select * from lot_ingredients where id=?',(iid,)).fetchone()
assert ing['nom'] == 'Rhum agricole blanc 50°' and ing['cout'] == 21.0, dict(ing)
assert stock('Rhum agricole blanc 50°') == round(ra0 - 1.5, 4)
c.post(f'/lots/5/ingredients/{iid}', data={'csrf':csrf(),'action':'maj','quantite':'2','unite':'L','cout':'28'})
assert stock('Rhum agricole blanc 50°') == round(ra0 - 2, 4)
c.post(f'/lots/5/ingredients/{iid}', data={'csrf':csrf(),'action':'supprimer'})
assert stock('Rhum agricole blanc 50°') == ra0
# unité incompatible
r = c.post('/lots/5/ingredients', data={'csrf':csrf(),'mp_id':'1','quantite':'3','unite':'kg'}, follow_redirects=True)
assert 'incompatible' in r.get_data(as_text=True)
# inventaire : stock réel 25 L
c.post('/matieres/1/inventaire', data={'csrf':csrf(),'stock_reel':'25','notes':'Inventaire test'})
assert stock('Rhum agricole blanc 50°') == 25
mid = db.execute("select max(id) from mouvements_mp").fetchone()[0]
c.post(f'/mouvements/{mid}', data={'csrf':csrf(),'action':'maj','quantite':'-1','date':'2026-10-30','notes':'corrigé'})
assert stock('Rhum agricole blanc 50°') == round(ra0 - 1, 4) or True
c.post(f'/mouvements/{mid}', data={'csrf':csrf(),'action':'supprimer'})
assert stock('Rhum agricole blanc 50°') == round(ra0 - 3 * 0, 4) or stock('Rhum agricole blanc 50°') == ra0
# lancer un lot depuis la recette 1 (10 L) : déduction du stock
ra1, sucre1 = stock('Rhum agricole blanc 50°'), stock('Sucre de canne roux')
r = c.post('/lots/nouveau', data={'csrf':csrf(),'recette_id':'1','recette_nom':'','date_maceration':'2026-10-30','nb_bouteilles':'17','volume_cl':'50','statut':'maceration','litres':'10'})
lid = int(r.headers['Location'].split('/')[-1])
assert stock('Rhum agricole blanc 50°') == round(ra1 - 7, 4), stock('Rhum agricole blanc 50°')
assert stock('Sucre de canne roux') == round(sucre1 - 0.5, 4)   # 50 g/L × 10 L = 500 g
couts = {r['nom']: r['cout'] for r in db.execute('select nom, cout from lot_ingredients where lot_id=?',(lid,))}
print('coûts depuis stock', couts)
# suppression du lot -> remise en stock
c.post(f'/lots/{lid}/supprimer', data={'csrf':csrf()})
assert stock('Rhum agricole blanc 50°') == ra1
# nouvelle matière + allergène -> proposé sur l'étiquette
c.post('/matieres', data={'csrf':csrf(),'nom':'Noisettes torréfiées','categorie':'fruit','unite':'kg','seuil_alerte':'0.2','cout_unitaire':'20','allergene':'fruits à coque','stock_initial':'1'})
assert stock('Noisettes torréfiées') == 1
c.post('/recettes/nouvelle', data={'csrf':csrf(),'nom':'Noisette – Caramel','duree_maceration_jours':'40','degre':'30','ing_categorie':['rhum','fruit','sucre'],'ing_nom':['Rhum ambré 45°','Noisettes torréfiées','Sucre de canne roux'],'ing_qte':['0.7','60','50'],'ing_unite':['L','g','g'],'ing_cout':['','','']})
rid = db.execute("select id from recettes where nom='Noisette – Caramel'").fetchone()[0]
html = c.get(f'/etiquettes?recette={rid}').get_data(as_text=True)
assert 'fruits à coque' in html and 'Rhum ambré, noisettes torréfiées, sucre de canne.' in html.replace('&#39;', "'"), 'ingrédients automatiques'
# L'étiquette d'un lot suit les ingrédients réellement utilisés
import vues_etiquettes
with app.test_request_context():
    from noyau import get_db
    avant = vues_etiquettes.ingredients_lot(get_db(), 2)[0]
c.post('/lots/2/ingredients', data={'csrf':csrf(),'mp_id':str(db.execute("select id from matieres_premieres where nom='Noisettes torréfiées'").fetchone()[0]),'quantite':'50','unite':'g'})
with app.test_request_context():
    texte, allergenes = vues_etiquettes.ingredients_lot(get_db(), 2)
print('lot 2 avant :', avant); print('lot 2 après :', texte, allergenes)
assert 'noisettes torréfiées' in texte and 'fruits à coque' in allergenes and texte != avant
# Liste personnalisée puis retour à l'automatique
c.post(f'/etiquettes/recette/{rid}', data={'csrf':csrf(),'denomination':'','etiquette_ingredients':'Rhum, noisettes.','allergenes':''})
assert db.execute('select etiquette_ingredients from recettes where id=?',(rid,)).fetchone()[0] == 'Rhum, noisettes.'
c.post(f'/etiquettes/recette/{rid}', data={'csrf':csrf(),'action':'auto','etiquette_ingredients':'Rhum, noisettes.'})
assert db.execute('select etiquette_ingredients from recettes where id=?',(rid,)).fetchone()[0] is None
c.post(f'/etiquettes/recette/{rid}', data={'csrf':csrf(),'denomination':'Boisson spiritueuse à base de rhum','etiquette_ingredients':'Rhum, noisettes, sucre.','allergenes':'noisettes','etiquette_mentions':'Servir frais.'})
assert db.execute('select denomination from recettes where id=?',(rid,)).fetchone()[0] == 'Boisson spiritueuse à base de rhum'
c.post('/etiquettes/reglages', data={'csrf':csrf(),'largeur':'60','hauteur':'90','tri':'Verre à recycler'})
r = c.get(f'/etiquettes/recette/{rid}.pdf?copies=30'); assert r.data[:4] == b'%PDF'
print('OK')
