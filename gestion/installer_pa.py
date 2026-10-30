# =====================================================================
#  Installation de Maison Corsaire sur PythonAnywhere — sans console
#
#  1. Remplacez l'email et le mot de passe ci-dessous (garder les guillemets)
#  2. Touchez « Save », puis le bouton « Run » (en haut à droite)
# =====================================================================

EMAIL = "votre@email.fr"
MOT_DE_PASSE = "choisissez-un-mot-de-passe"

# ---------------------------------------------------------------------
# Rien à modifier en dessous
# ---------------------------------------------------------------------
import json  # noqa: E402
import os  # noqa: E402
import secrets  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

DEPOT_GIT = "https://github.com/r42jh2g2gv-max/maison-corsaire-veille.git"
BRANCHE = "claude/app-gestion-maison-corsaire"
HOME = os.path.expanduser("~")
DEPOT = os.path.join(HOME, "maison-corsaire-veille")
DONNEES = os.path.join(HOME, "donnees-corsaire")
CONFIG = os.path.join(DONNEES, "config.json")


def main():
    if "@" not in EMAIL or EMAIL == "votre@email.fr":
        sys.exit("!! Remplacez d'abord votre@email.fr par votre email (ligne EMAIL), puis Save et Run.")
    if len(MOT_DE_PASSE) < 8 or MOT_DE_PASSE == "choisissez-un-mot-de-passe":
        sys.exit("!! Choisissez un mot de passe d'au moins 8 caractères (ligne MOT_DE_PASSE).")

    if not os.path.isdir(DEPOT):
        print("Téléchargement de l'application…")
        subprocess.run(["git", "clone", "-q", "-b", BRANCHE, DEPOT_GIT, DEPOT], check=True)

    os.makedirs(DONNEES, exist_ok=True)
    secret = secrets.token_hex(32)
    if os.path.exists(CONFIG):
        with open(CONFIG) as f:
            secret = json.load(f).get("secret", secret)
    ancien = os.umask(0o077)
    with open(CONFIG, "w") as f:
        json.dump({"email": EMAIL.strip(), "mdp": MOT_DE_PASSE, "secret": secret}, f)
    os.umask(ancien)

    print("Installation (1 à 2 minutes)…")
    resultat = subprocess.run(
        ["bash", os.path.join(DEPOT, "gestion", "installer_pythonanywhere.sh")])
    if resultat.returncode == 0:
        print("\nPensez à effacer votre mot de passe de ce fichier (ou à le supprimer).")


if __name__ == "__main__":
    main()
