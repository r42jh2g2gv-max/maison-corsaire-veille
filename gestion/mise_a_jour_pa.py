# Mise à jour de Maison Corsaire sur PythonAnywhere : touchez « Run », puis « Reload » dans l'onglet Web.
# (Après cette mise à jour, le bouton Paramètres → « Mettre à jour l'application » suffit.)
import os
import subprocess

script = os.path.expanduser("~/maison-corsaire-veille/gestion/installer_pythonanywhere.sh")
print("Mise à jour en cours (1 à 2 minutes)…")
subprocess.run(["bash", script], stdin=subprocess.DEVNULL)
