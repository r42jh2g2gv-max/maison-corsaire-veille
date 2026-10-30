#!/bin/bash
# Installation de Maison Corsaire sur PythonAnywhere, en une commande depuis une console Bash :
#   git clone -b claude/app-gestion-maison-corsaire https://github.com/r42jh2g2gv-max/maison-corsaire-veille.git && bash maison-corsaire-veille/gestion/installer_pythonanywhere.sh
# Mise à jour plus tard :
#   bash ~/maison-corsaire-veille/gestion/installer_pythonanywhere.sh
set -e

DEPOT="$HOME/maison-corsaire-veille"
APP="$DEPOT/gestion"
VENV="$HOME/venv-corsaire"
DONNEES="$HOME/donnees-corsaire"
CONFIG="$DONNEES/config.json"
BRANCHE="claude/app-gestion-maison-corsaire"
WSGI_DIR="${WSGI_DIR:-/var/www}"

echo "=== Maison Corsaire : installation ==="

# 1. Le fichier WSGI n'existe que si l'application web a été créée (onglet Web)
WSGI=$(ls "$WSGI_DIR"/*_wsgi.py 2>/dev/null | head -n 1 || true)
if [ -z "$WSGI" ]; then
  echo
  echo "!! Créez d'abord l'application web : onglet Web > Add a new web app >"
  echo "   Manual configuration > Python 3.12. Puis relancez :"
  echo "   bash ~/maison-corsaire-veille/gestion/installer_pythonanywhere.sh"
  exit 1
fi

# 2. Code à jour, sur la bonne branche
cd "$DEPOT"
git fetch -q origin "$BRANCHE"
git checkout -q "$BRANCHE" 2>/dev/null || git checkout -q -b "$BRANCHE" "origin/$BRANCHE"
git pull -q --ff-only origin "$BRANCHE"

# 3. Environnement Python (même version que l'application web : 3.12 de préférence)
PY=""
for v in python3.12 python3.13 python3.11 python3.10; do
  if command -v "$v" >/dev/null 2>&1; then PY="$v"; break; fi
done
if [ -z "$PY" ]; then echo "!! Aucun Python 3.10 ou plus récent trouvé."; exit 1; fi
echo "-> Python ${PY#python} (choisissez la même version dans l'onglet Web)"
[ -d "$VENV" ] || "$PY" -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$APP/requirements.txt"

# 4. Compte administrateur (demandé seulement à la première installation)
mkdir -p "$DONNEES"
if [ ! -f "$CONFIG" ]; then
  echo
  read -r -p "Votre email (pour vous connecter) : " EMAIL
  while true; do
    read -r -s -p "Choisissez un mot de passe (8 caractères minimum) : " MDP; echo
    if [ ${#MDP} -ge 8 ]; then break; fi
    echo "Trop court, recommencez."
  done
  ( umask 077
    EMAIL="$EMAIL" MDP="$MDP" "$VENV/bin/python" "$APP/outils_installation.py" config "$CONFIG" )
fi

# 5. Fichier WSGI de l'application web
"$VENV/bin/python" "$APP/outils_installation.py" wsgi "$CONFIG" "$WSGI" "$APP" "$DONNEES"

echo
echo "=== Installation terminée ==="
echo "Dernière étape, dans l'onglet Web :"
echo "  1. Virtualenv : $VENV"
echo "  2. Security > Force HTTPS : activé"
echo "  3. Bouton vert Reload"
echo "Puis ouvrez votre adresse https://...pythonanywhere.com"
