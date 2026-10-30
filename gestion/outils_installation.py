"""Aide à l'installation sur PythonAnywhere (appelé par installer_pythonanywhere.sh)."""
import json
import os
import secrets
import sys

MODELE_WSGI = '''# Généré par installer_pythonanywhere.sh — ne pas modifier à la main
import os, sys
sys.path.insert(0, {app!r})
os.chdir({app!r})
os.environ["HTTPS"] = "1"
os.environ["DATA_DIR"] = {donnees!r}
os.environ["SECRET_KEY"] = {secret!r}
os.environ["ADMIN_EMAIL"] = {email!r}
os.environ["ADMIN_PASSWORD"] = {mdp!r}
from app import app as application  # noqa: E402
'''


def main(args):
    if args[0] == "config":
        # Identifiants lus dans l'environnement : ils n'apparaissent pas dans l'historique.
        with open(args[1], "w") as f:
            json.dump({"email": os.environ["EMAIL"].strip(), "mdp": os.environ["MDP"],
                       "secret": secrets.token_hex(32)}, f)
    elif args[0] == "wsgi":
        config, wsgi, app, donnees = args[1:]
        with open(config) as f:
            c = json.load(f)
        with open(wsgi, "w") as f:
            f.write(MODELE_WSGI.format(app=app, donnees=donnees, secret=c["secret"],
                                       email=c["email"], mdp=c["mdp"]))


if __name__ == "__main__":
    main(sys.argv[1:])
