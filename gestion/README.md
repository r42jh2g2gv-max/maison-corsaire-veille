# Maison Corsaire — Gestion

Application web de gestion pour une production artisanale de rhum arrangé :
lots, recettes, caisse, clients, stock, agenda, chiffres et tableurs.
Thème sombre bleu nuit, bois et or (thème clair « plein soleil » en option),
pensée d'abord pour le téléphone.

## Démarrer

```bash
cd gestion
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Ouvrez ensuite http://127.0.0.1:5000

**Compte de démonstration** : `contact@maisoncorsaire.fr` / `corsaire2026`.
Changez-le dans *Paramètres → Mon compte*.

Au premier lancement, la base `instance/corsaire.db` est créée avec des données
d'exemple. Pour démarrer votre vrai registre : *Paramètres → Données → Tout effacer et démarrer*.

Sur le téléphone (même Wi-Fi) : `HOST=0.0.0.0 python app.py`, puis ouvrez
`http://<adresse-IP-de-l-ordinateur>:5000`. Dans Safari, « Partager → Sur l'écran
d'accueil » l'installe comme une application.

## Pages

| Page | Contenu |
| --- | --- |
| Accueil | CA du mois, stock, marge, lots en cours, **À faire** (rappels), CA sur 6 mois |
| Caisse | Encaissement au doigt : produits, quantités, client, bon d'achat, consigne, espèces/carte/virement/chèque, rendu de monnaie, rattachement à un marché |
| Tickets & factures | Ticket PDF (80 mm) et facture PDF (A4, numérotation continue, mentions micro-entreprise), à imprimer, partager (Mail, SMS, WhatsApp) ou envoyer par email |
| Lots | Registre de traçabilité, ingrédients et coûts, statuts, fiche lot imprimable |
| Recettes | Bibliothèque (quantités pour 1 L, prix des ingrédients, étapes, dégustation), fiche imprimable recalculée pour N litres, bouton « Lancer un lot » |
| Stock | Bouteilles par lot, conditionnement avec seuils d'alerte (déduit à l'embouteillage) |
| Matières premières | Rhum, fruits, épices, sucre : stock calculé à partir des achats et des lots (déduction automatique), inventaire pour corriger un écart, chaque mouvement modifiable ou supprimable |
| Registre des achats | Fournisseur, n° de facture, lignes d'articles (conversion g/kg, cl/L automatique), mode de règlement, photo du justificatif ; met le stock et les prix à jour |
| Étiquettes | Contre-étiquette PDF : dénomination, ingrédients (allergènes en gras), volume, degré, case LOT à tamponner (ou n° imprimé), producteur, pictogramme femme enceinte, consigne de tri ; planche A4 ou une par page |
| Statistiques | Par recette : bouteilles vendues, CA, part du CA, marge, prix moyen, ventes mois par mois, canaux, meilleurs clients, autonomie du stock |
| Clients | Fichier clients avec consentement RGPD, historique d'achats, bons d'achat, consignes, suppression |
| Bons d'achat | Création, PDF, partage ou email, utilisation unique en caisse avec code |
| Nouveautés | Message aux clients qui l'ont accepté (copie cachée ou envoi individuel) |
| Agenda | Marchés et salons : inscription, stock à préparer, bilan (CA, coûts, place, bénéfice) |
| Chiffres | CA URSSAF à déclarer par mois ou trimestre, cotisations estimées, volumes d'alcool pur (douanes) |
| Tableurs | Excel : livre des recettes, registre des achats, ventes détaillées, lots, stock (dont matières premières), clients, recettes, classeur complet |
| Calculateur | Coût de revient par bouteille, prix direct et revendeur selon la marge |

## Caisse sans réseau

Une fois l'application **en ligne (https)** et la caisse ouverte une fois avec du réseau,
elle fonctionne sans connexion : les ventes sont gardées dans le téléphone puis envoyées
automatiquement au retour du réseau, sans doublon. Voir [DEPLOIEMENT.md](DEPLOIEMENT.md).

## Mise en ligne

Guide pas à pas pour un test gratuit sur PythonAnywhere, et `Dockerfile` pour un autre
hébergeur : [DEPLOIEMENT.md](DEPLOIEMENT.md).

## Tests

```bash
python tests/test_ventes_clients.py
python tests/test_stock_etiquettes.py
```

Chaque test crée une base d'exemple neuve dans un dossier temporaire et parcourt l'application.

## Rappels automatiques (« À faire »)

Déclaration URSSAF à faire ou en retard · inscription à un marché avant la date limite ·
stock à préparer avant un événement (et alerte si insuffisant) · lot prêt à embouteiller ou
à goûter · conditionnement ou matière première sous le seuil · DLC proche · bon d'achat qui expire · revendeur sans
commande depuis 45 jours.

## Envoi d'emails (facultatif)

Sans configuration, « Partager le PDF » ouvre la messagerie du téléphone avec le document
joint. Pour envoyer directement depuis l'application, renseignez un serveur SMTP dans
*Paramètres → Envoi d'emails* (Gmail : `smtp.gmail.com`, port 587, mot de passe d'application).

## Configuration (variables d'environnement)

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `PORT`, `HOST` | Adresse d'écoute | `5000`, `127.0.0.1` |
| `DATA_DIR` | Dossier des données (base, justificatifs, clé) | `instance/` |
| `DATABASE` | Chemin de la base SQLite | `DATA_DIR/corsaire.db` |
| `HTTPS` | `1` en ligne : cookies sécurisés, identifiants de démo masqués | — |
| `SECRET_KEY` | Clé de session | générée dans `instance/secret_key` |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Compte créé au premier lancement | compte de démonstration |

Sauvegarde : copiez le fichier `instance/corsaire.db`, ou téléchargez le classeur Excel complet.
Une base créée avec une version précédente est mise à jour automatiquement au démarrage.

## Organisation du code

`app.py` (démarrage) · `wsgi.py` (hébergeur) · `noyau.py` (application, outils, sécurité) · `db.py` (schéma,
migrations, données d'exemple) · `calculs.py` · `rappels.py` · `pdfs.py` · `emails.py` ·
`etiquette_pdf.py` · `vues_*.py` (une page ou un groupe de pages par fichier) · `tests/` · `templates/` · `static/`.
