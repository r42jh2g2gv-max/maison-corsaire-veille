"""Test de bout en bout sur une base d'exemple neuve. Lancer depuis gestion/ : python tests/test_ventes_clients.py"""
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="corsaire-test-")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import io, json, re, sqlite3
import app as appmod
from noyau import app
app.config['TESTING'] = False
c = app.test_client()
def csrf():
    with c.session_transaction() as s: return s.get('csrf')
c.get('/connexion')
r = c.post('/connexion', data={'email':'contact@maisoncorsaire.fr','password':'corsaire2026','csrf':csrf()}); assert r.status_code == 302, r.status_code
db = sqlite3.connect(app.config['DATABASE']); db.row_factory = sqlite3.Row
pages = ['/', '/caisse', '/caisse?lot_id=2&client_id=3', '/lots', '/lots/1', '/lots/2', '/lots/4', '/lots/5', '/lots/nouveau?recette_id=1',
 '/lots/2/modifier', '/lots/2/fiche', '/recettes', '/recettes/nouvelle', '/recettes/1/modifier', '/recettes/1/fiche?litres=12',
 '/stock', '/ventes', '/ventes?mois=tout&q=Galion', '/clients', '/clients?type=revendeur', '/clients/1', '/clients/3', '/clients/nouveau', '/clients/3/modifier',
 '/clients/message', '/bons', '/agenda', '/agenda/4/modifier', '/chiffres', '/calculateur', '/calculateur?lot_id=3', '/parametres',
 '/tickets/1', '/tickets/2', '/tickets/12', '/tickets/1/ticket.pdf', '/tickets/2/facture.pdf', '/bons/1.pdf', '/api/bon?code=XXX']
for u in pages:
    r = c.get(u)
    assert r.status_code == 200, (u, r.status_code, r.get_data(as_text=True)[:3000])
for nom in ['livre-recettes','ventes','lots','stock','clients','recettes','complet']:
    r = c.get(f'/exports/{nom}.xlsx?debut=2026-01-01&fin=2026-12-31'); assert r.status_code == 200 and r.data[:2] == b'PK', nom
print('pages OK')
html = c.get('/').get_data(as_text=True)
print('KPI', re.findall(r'class="valeur">([^<]*)<', html))
print('rappels', [re.sub(r'\s+',' ',t) for t in re.findall(r'<span class="titre">([^<]*)<', html)])
# caisse : vente multi-lignes avec bon + consigne
bon = db.execute("select * from bons where ticket_id is null and beneficiaire='Sophie Martin'").fetchone()
r = c.get('/api/bon?code='+bon['code']+'&client_id=4'); print('bon autre client', r.json)
r = c.get('/api/bon?code='+bon['code'].lower()+'&client_id='+str(bon['client_id'])); print('bon ok', r.json)
stock_avant = db.execute("select nb_bouteilles - (select sum(quantite) from ventes where lot_id=2) from lots where id=2").fetchone()[0]
panier = json.dumps([{'lot_id':2,'quantite':2,'prix':36},{'lot_id':3,'quantite':1,'prix':38}])
r = c.post('/caisse', data={'csrf':csrf(),'panier':panier,'client_id':bon['client_id'],'client_nom':'Sophie Martin','canal':'direct','mode_paiement':'carte','bon_code':bon['code'],'consigne_btl':'3','consigne_retour':'1','date_vente':'2026-10-30'})
assert r.status_code == 302, r.get_data(as_text=True)[:3000]
tid = int(r.headers['Location'].split('/tickets/')[1].split('?')[0])
t = db.execute('select * from tickets where id=?',(tid,)).fetchone()
print('ticket', dict(t)['numero'], t['sous_total'], t['remise'], t['consigne'], t['total'])
assert t['sous_total']==110 and t['remise']==10 and t['consigne']==2 and t['total']==102
assert db.execute('select ticket_id from bons where id=?',(bon['id'],)).fetchone()[0]==tid
# réutiliser le bon -> refus
r = c.post('/caisse', data={'csrf':csrf(),'panier':panier,'client_id':bon['client_id'],'bon_code':bon['code'],'mode_paiement':'carte'}, follow_redirects=True)
assert 'déjà été utilisé' in r.get_data(as_text=True)
# stock insuffisant
r = c.post('/caisse', data={'csrf':csrf(),'panier':json.dumps([{'lot_id':2,'quantite':99,'prix':36}]),'mode_paiement':'especes'}, follow_redirects=True)
assert 'Stock insuffisant' in r.get_data(as_text=True)
# consigne sans client -> refus
r = c.post('/caisse', data={'csrf':csrf(),'panier':json.dumps([{'lot_id':2,'quantite':1,'prix':36}]),'consigne_btl':'1','mode_paiement':'especes'}, follow_redirects=True)
assert 'Pour une consigne' in r.get_data(as_text=True)
# vente épuisant le lot 2
reste = db.execute("select nb_bouteilles - (select sum(quantite) from ventes where lot_id=2) from lots where id=2").fetchone()[0]
r = c.post('/caisse', data={'csrf':csrf(),'panier':json.dumps([{'lot_id':2,'quantite':reste,'prix':36}]),'mode_paiement':'especes','client_nom':'Marché'})
tid2 = int(r.headers['Location'].split('/tickets/')[1].split('?')[0])
assert db.execute('select statut from lots where id=2').fetchone()[0]=='epuise'
# facture
r = c.post(f'/tickets/{tid}/facture', data={'csrf':csrf(),'client_nom':'Sophie Martin','client_adresse':'1 rue X, 17000 La Rochelle','memoriser':'1'})
f = db.execute('select facture_numero from tickets where id=?',(tid,)).fetchone()[0]; print('facture', f)
assert c.get(f'/tickets/{tid}/facture.pdf').data[:4]==b'%PDF'
r = c.post(f'/tickets/{tid}/supprimer', data={'csrf':csrf()}, follow_redirects=True); assert 'ne peut pas être supprimé' in r.get_data(as_text=True)
# suppression ticket -> lot réouvert
c.post(f'/tickets/{tid2}/supprimer', data={'csrf':csrf()})
assert db.execute('select statut from lots where id=2').fetchone()[0]=='embouteille'
# clients
r = c.post('/clients/nouveau', data={'csrf':csrf(),'nom':'Test Client','type':'particulier','email':'t@ex.fr','accepte_infos':'1'}); cid = int(r.headers['Location'].rstrip('/').split('/')[-1])
c.post(f'/clients/{cid}/consigne', data={'csrf':csrf(),'quantite':'2','sens':'sortie'})
mat0 = db.execute("select stock from materiaux where type='bouteille'").fetchone()[0]
c.post(f'/clients/{cid}/consigne', data={'csrf':csrf(),'quantite':'1','sens':'retour','remettre_en_stock':'1'})
assert db.execute("select stock from materiaux where type='bouteille'").fetchone()[0]==mat0+1
assert db.execute('select sum(quantite) from consignes where client_id=?',(cid,)).fetchone()[0]==1
c.post('/bons', data={'csrf':csrf(),'client_id':cid,'montant':'7.5','motif':'Test','date_expiration':'2027-01-01'})
assert db.execute('select count(*) from bons where client_id=?',(cid,)).fetchone()[0]==1
r = c.post('/clients/message', data={'csrf':csrf(),'sujet':'Nouveau','corps':'Coucou','destinataires':[str(cid),'1'],'mode':'messagerie'})
assert 'mailto:?bcc=' in r.get_data(as_text=True)
c.post(f'/clients/{cid}/supprimer', data={'csrf':csrf()})
assert db.execute('select count(*) from clients where id=?',(cid,)).fetchone()[0]==0
# recettes
r = c.post('/recettes/nouvelle', data={'csrf':csrf(),'nom':'Banane flambée','duree_maceration_jours':'50','degre':'31','ing_categorie':['rhum','fruit',''],'ing_nom':['Rhum ambré','Banane',''],'ing_qte':['0.7','0.3',''],'ing_unite':['L','kg',''],'ing_cout':['17','3','']})
rid = db.execute("select id from recettes where nom='Banane flambée'").fetchone()[0]
assert db.execute('select count(*) from recette_ingredients where recette_id=?',(rid,)).fetchone()[0]==2
r = c.post('/lots/nouveau', data={'csrf':csrf(),'recette_id':rid,'recette_nom':'','date_maceration':'2026-10-30','nb_bouteilles':'20','volume_cl':'50','statut':'maceration','litres':'10'})
lid = int(r.headers['Location'].split('/')[-1])
print('lot depuis recette', [tuple(x) for x in db.execute('select nom, quantite, cout from lot_ingredients where lot_id=?',(lid,))])
# agenda
c.post('/agenda/nouveau', data={'csrf':csrf(),'nom':'Test marché','type':'marche','date_debut':'2026-11-05','btl_prevues':'40'})
eid = db.execute("select id from evenements where nom='Test marché'").fetchone()[0]
c.post(f'/agenda/{eid}/basculer', data={'csrf':csrf(),'champ':'inscrit'})
assert db.execute('select inscrit from evenements where id=?',(eid,)).fetchone()[0]==1
# chiffres
r = c.post('/chiffres/declarer', data={'csrf':csrf(),'periode':'2026-09','montant':'100'}); assert r.status_code==302
assert 'Déclarer le CA URSSAF : septembre' not in c.get('/').get_data(as_text=True)
# thème
r = c.get('/theme/clair?next=/stock'); assert r.headers['Location'].endswith('/stock') and 'theme=clair' in r.headers['Set-Cookie']
r = c.get('/theme/clair?next=//evil.com'); assert 'evil' not in r.headers['Location']
print('OK')
# Changement de mot de passe : confirmation obligatoire, ancien refusé, nouveau accepté
c2 = app.test_client()
c2.get('/connexion')
with c2.session_transaction() as s: t = s['csrf']
c2.post('/connexion', data={'email':'contact@maisoncorsaire.fr','password':'corsaire2026','csrf':t})
with c2.session_transaction() as s: t = s['csrf']
r = c2.post('/parametres/compte', data={'csrf':t,'email':'contact@maisoncorsaire.fr','actuel':'corsaire2026','nouveau':'Rhum2026!','confirmation':'Rhum2026?'}, follow_redirects=True)
assert 'pas identiques' in r.get_data(as_text=True)
r = c2.post('/parametres/compte', data={'csrf':t,'email':'contact@maisoncorsaire.fr','actuel':'faux','nouveau':'Rhum2026!','confirmation':'Rhum2026!'}, follow_redirects=True)
assert 'actuel incorrect' in r.get_data(as_text=True)
r = c2.post('/parametres/compte', data={'csrf':t,'email':'contact@maisoncorsaire.fr','actuel':'corsaire2026','nouveau':'Rhum2026!','confirmation':'Rhum2026!'}, follow_redirects=True)
assert 'mot de passe changé' in r.get_data(as_text=True)
c2.get('/deconnexion'); c2.get('/connexion')
with c2.session_transaction() as s: t = s['csrf']
assert c2.post('/connexion', data={'email':'contact@maisoncorsaire.fr','password':'corsaire2026','csrf':t}).status_code == 200
assert c2.post('/connexion', data={'email':'contact@maisoncorsaire.fr','password':'Rhum2026!','csrf':t}).status_code == 302
print('mot de passe OK')
