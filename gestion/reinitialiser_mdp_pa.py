# =====================================================================
#  Maison Corsaire — changer le mot de passe de connexion (PythonAnywhere)
#
#  1. Écrivez votre nouveau mot de passe ci-dessous (garder les guillemets)
#  2. Touchez « Save », puis « >>> Run »
#  3. Supprimez ce fichier ensuite (il contient votre mot de passe)
# =====================================================================

NOUVEAU_MOT_DE_PASSE = "ecrivez-ici-votre-nouveau-mot-de-passe"

# ---------------------------------------------------------------------
# Rien à modifier en dessous
# ---------------------------------------------------------------------
import json  # noqa: E402
import os  # noqa: E402
import sqlite3  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

HOME = os.path.expanduser("~")
DONNEES = os.environ.get("DATA_DIR") or os.path.join(HOME, "donnees-corsaire")
BASE = os.path.join(DONNEES, "corsaire.db")
VENV_PYTHON = os.path.join(HOME, "venv-corsaire", "bin", "python")

try:
    from werkzeug.security import generate_password_hash
except ImportError:  # le bouton Run n'utilise pas forcément l'environnement de l'appli
    if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON:
        sys.exit(subprocess.call([VENV_PYTHON] + sys.argv))
    raise

if NOUVEAU_MOT_DE_PASSE == "ecrivez-ici-votre-nouveau-mot-de-passe" or len(NOUVEAU_MOT_DE_PASSE) < 8:
    sys.exit("!! Écrivez un mot de passe d'au moins 8 caractères (ligne NOUVEAU_MOT_DE_PASSE), "
             "puis Save et Run.")
if not os.path.exists(BASE):
    sys.exit(f"!! Base introuvable : {BASE}")

conn = sqlite3.connect(BASE)
email = conn.execute("SELECT email FROM users ORDER BY id LIMIT 1").fetchone()[0]
conn.execute("UPDATE users SET password_hash = ?", (generate_password_hash(NOUVEAU_MOT_DE_PASSE),))
conn.commit()
conn.close()

# Garde la configuration d'installation cohérente (utilisée lors des mises à jour)
config = os.path.join(DONNEES, "config.json")
if os.path.exists(config):
    with open(config) as f:
        c = json.load(f)
    c["mdp"] = NOUVEAU_MOT_DE_PASSE
    with open(config, "w") as f:
        json.dump(c, f)

print("Mot de passe changé.")
print(f"Connectez-vous avec : {email}")
print("et le nouveau mot de passe. Pensez à supprimer ce fichier.")
