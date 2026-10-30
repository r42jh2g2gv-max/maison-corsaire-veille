# Mettre l'application en ligne (test)

Pour un test, **PythonAnywhere** est le plus simple : offre gratuite, sans carte bancaire,
adresse en `https://votre-nom.pythonanywhere.com` (le https est indispensable pour que la
caisse fonctionne sans réseau et que l'application s'installe sur le téléphone), et les
données sont conservées sur leur disque.

Limites de l'offre gratuite à connaître : il faut cliquer une fois tous les 3 mois sur
« Run until 3 months from today » dans l'onglet *Web*, et l'accès à internet depuis le
serveur est restreint (l'envoi d'emails depuis l'application peut ne pas fonctionner :
le bouton « Partager le PDF » du téléphone, lui, fonctionne toujours).

## Version rapide (faisable entièrement depuis un téléphone)
1. Inscription gratuite sur pythonanywhere.com (offre *Beginner*).
2. Onglet **Web → Add a new web app → Next → Manual configuration → Python 3.12 → Next**.
3. Onglet **Consoles → Bash**, collez cette commande puis répondez aux 2 questions :
   ```bash
   git clone -b claude/app-gestion-maison-corsaire https://github.com/r42jh2g2gv-max/maison-corsaire-veille.git && bash maison-corsaire-veille/gestion/installer_pythonanywhere.sh
   ```
4. Onglet **Web** : *Virtualenv* → `/home/NOM/venv-corsaire`, *Force HTTPS* activé, bouton **Reload**.

La version détaillée ci-dessous fait la même chose à la main.

## 1. Créer le compte
1. Inscrivez-vous sur https://www.pythonanywhere.com (offre *Beginner*, gratuite).
2. Le nom d'utilisateur choisi donnera l'adresse : `https://NOM.pythonanywhere.com`.

## 2. Récupérer le code
Onglet **Consoles → Bash**, puis :

```bash
git clone https://github.com/r42jh2g2gv-max/maison-corsaire-veille.git
cd maison-corsaire-veille && git checkout claude/app-gestion-maison-corsaire
python3.12 -m venv ~/venv-corsaire
~/venv-corsaire/bin/pip install -r gestion/requirements.txt
```

Si le dépôt est privé, `git clone` demandera votre identifiant GitHub et, en guise de mot de
passe, un *token* GitHub (GitHub → Settings → Developer settings → Personal access tokens,
droit « Contents : read »). Autre solution : téléchargez le ZIP du dépôt depuis GitHub et
envoyez-le dans l'onglet *Files*, puis `unzip`.

## 3. Créer l'application web
1. Onglet **Web → Add a new web app → Manual configuration → Python 3.12** (ou la version la plus récente proposée, en adaptant `python3.12` ci-dessus).
2. **Virtualenv** : `/home/NOM/venv-corsaire`
3. **Source code** : `/home/NOM/maison-corsaire-veille/gestion`
4. Cliquez sur le lien du **WSGI configuration file** et remplacez tout son contenu par :

```python
import os, sys
CHEMIN = "/home/NOM/maison-corsaire-veille/gestion"
sys.path.insert(0, CHEMIN)
os.chdir(CHEMIN)
os.environ["HTTPS"] = "1"
os.environ["DATA_DIR"] = "/home/NOM/donnees-corsaire"
os.environ["SECRET_KEY"] = "remplacez-par-une-longue-phrase-secrete-et-unique"
os.environ["ADMIN_EMAIL"] = "votre@email.fr"
os.environ["ADMIN_PASSWORD"] = "un-mot-de-passe-solide"
from app import app as application
```

5. Section **Static files** : URL `/static/` → dossier `/home/NOM/maison-corsaire-veille/gestion/static`
6. Section **Security** : activez **Force HTTPS**.
7. Bouton vert **Reload**, puis ouvrez `https://NOM.pythonanywhere.com`.

Au premier lancement, le compte est créé avec l'email et le mot de passe du fichier WSGI,
et les **données d'exemple** sont chargées pour tester. Quand vous démarrez pour de vrai :
*Paramètres → Données → Tout effacer et démarrer*.

## 4. Installer sur le téléphone
- **iPhone (Safari)** : ouvrez l'adresse, connectez-vous, *Partager → Sur l'écran d'accueil*.
- **Android (Chrome)** : menu ⋮ → *Installer l'application*.

Ouvrez ensuite **une fois la caisse avec du réseau** : elle est alors enregistrée dans le
téléphone et fonctionne sans réseau.

## 5. Au marché sans réseau
- La caisse s'ouvre et encaisse normalement ; l'en-tête affiche « Hors ligne ».
- Chaque vente est gardée dans le téléphone (encadré « Ventes enregistrées sur ce téléphone »).
- Dès que le réseau revient, elles sont envoyées automatiquement (ou bouton *Envoyer maintenant*).
  Chaque vente a un identifiant unique : un envoi répété ne crée jamais de doublon.
- Hors ligne, les bons d'achat ne peuvent pas être vérifiés, et tickets et factures sont
  disponibles après l'envoi (Historique des ventes).
- Ne videz pas les données de Safari/Chrome tant que des ventes sont en attente.

## Mettre à jour l'application
```bash
cd ~/maison-corsaire-veille && git pull
~/venv-corsaire/bin/pip install -r gestion/requirements.txt
```
puis **Reload** dans l'onglet *Web*. La base existante est mise à jour automatiquement.

## Sauvegarde
Téléchargez régulièrement *Chiffres → Tableurs → Classeur complet*, et/ou le fichier
`/home/NOM/donnees-corsaire/corsaire.db` depuis l'onglet *Files*.

## Autre hébergeur (plus tard)
Le `Dockerfile` fourni fonctionne sur tout hébergeur de conteneurs avec un **disque
persistant monté sur `/data`** (Fly.io, Railway, un VPS…). Variables à définir :
`SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
