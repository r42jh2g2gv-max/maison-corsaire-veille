# Maison Corsaire — Gestion

Application web pour gérer la production de rhum arrangé : registre des lots,
coût de revient et prix, stock et ventes. Fonctionne sur téléphone et ordinateur.

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
d'exemple (5 lots, 4 recettes, matières, ventes). Pour démarrer votre vrai
registre : *Paramètres → Données → Tout effacer et démarrer*.

Pour l'utiliser depuis votre téléphone sur le même Wi-Fi : `HOST=0.0.0.0 python app.py`,
puis ouvrez `http://<adresse-IP-de-l-ordinateur>:5000`.

## Modules

| Module | Contenu |
| --- | --- |
| Tableau de bord | CA du mois, bouteilles en stock, marge moyenne, prochains lots prêts, alertes de stock, CA sur 6 mois |
| Registre des lots | Numéro automatique `MC-AAAA-NNN`, dates, DLC/DDM, statut, ingrédients avec quantités et coûts, fiche de traçabilité imprimable en PDF |
| Calculateur | Coût de revient par bouteille (ingrédients + bouteille, bouchon, étiquette, emballage + droits), prix HT/TTC selon la marge, comparaison vente directe / revendeur |
| Stock & ventes | Stock par lot, matières avec seuil d'alerte, enregistrement des ventes avec mise à jour automatique du stock |

Règles automatiques :
- passer un lot à **Embouteillé** déduit 1 unité de chaque matière « par bouteille » ; revenir en arrière ou corriger le nombre de bouteilles réajuste le stock ;
- une vente est refusée si le stock du lot est insuffisant ; le lot passe à **Épuisé** quand tout est vendu ;
- supprimer une vente remet les bouteilles en stock.

## Configuration (variables d'environnement)

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `PORT`, `HOST` | Adresse d'écoute | `5000`, `127.0.0.1` |
| `DATABASE` | Chemin de la base SQLite | `instance/corsaire.db` |
| `SECRET_KEY` | Clé de session | générée dans `instance/secret_key` |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Compte créé au premier lancement | compte de démonstration |

Sauvegarde : copiez simplement le fichier `instance/corsaire.db`.
