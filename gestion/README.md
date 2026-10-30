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
| Stock | Bouteilles par lot, matières avec seuils d'alerte (déduites à l'embouteillage) |
| Clients | Fichier clients avec consentement RGPD, historique d'achats, bons d'achat, consignes, suppression |
| Bons d'achat | Création, PDF, partage ou email, utilisation unique en caisse avec code |
| Nouveautés | Message aux clients qui l'ont accepté (copie cachée ou envoi individuel) |
| Agenda | Marchés et salons : inscription, stock à préparer, bilan (CA, coûts, place, bénéfice) |
| Chiffres | CA URSSAF à déclarer par mois ou trimestre, cotisations estimées, volumes d'alcool pur (douanes) |
| Tableurs | Excel : livre des recettes, ventes détaillées, lots, stock, clients, recettes, classeur complet |
| Calculateur | Coût de revient par bouteille, prix direct et revendeur selon la marge |

## Rappels automatiques (« À faire »)

Déclaration URSSAF à faire ou en retard · inscription à un marché avant la date limite ·
stock à préparer avant un événement (et alerte si insuffisant) · lot prêt à embouteiller ou
à goûter · matière sous le seuil · DLC proche · bon d'achat qui expire · revendeur sans
commande depuis 45 jours.

## Envoi d'emails (facultatif)

Sans configuration, « Partager le PDF » ouvre la messagerie du téléphone avec le document
joint. Pour envoyer directement depuis l'application, renseignez un serveur SMTP dans
*Paramètres → Envoi d'emails* (Gmail : `smtp.gmail.com`, port 587, mot de passe d'application).

## Configuration (variables d'environnement)

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `PORT`, `HOST` | Adresse d'écoute | `5000`, `127.0.0.1` |
| `DATABASE` | Chemin de la base SQLite | `instance/corsaire.db` |
| `SECRET_KEY` | Clé de session | générée dans `instance/secret_key` |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Compte créé au premier lancement | compte de démonstration |

Sauvegarde : copiez le fichier `instance/corsaire.db`, ou téléchargez le classeur Excel complet.
Une base créée avec une version précédente est mise à jour automatiquement au démarrage.

## Organisation du code

`app.py` (démarrage) · `noyau.py` (application, outils, sécurité) · `db.py` (schéma,
migrations, données d'exemple) · `calculs.py` · `rappels.py` · `pdfs.py` · `emails.py` ·
`vues_*.py` (une page ou un groupe de pages par fichier) · `templates/` · `static/`.
