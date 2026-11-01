"""Sauvegardes : une copie de la base chaque jour (30 jours), téléchargement et restauration."""
import io
import re
import sqlite3
import zipfile
from datetime import date, datetime

from flask import Response, abort, flash, g, redirect, request, send_file, url_for

from noyau import INSTANCE, app

DOSSIER = INSTANCE / "sauvegardes"
GARDER = 30
NOM_VALIDE = re.compile(r"^corsaire-[\w\-]+\.db$")


def copier_base(destination):
    """Copie cohérente de la base, même pendant son utilisation (API de sauvegarde SQLite)."""
    source = sqlite3.connect(app.config["DATABASE"])
    cible = sqlite3.connect(destination)
    with cible:
        source.backup(cible)
    cible.close()
    source.close()


def sauvegarder(suffixe=None):
    DOSSIER.mkdir(parents=True, exist_ok=True)
    nom = f"corsaire-{suffixe or date.today().isoformat()}.db"
    copier_base(DOSSIER / nom)
    # On garde les 30 sauvegardes quotidiennes les plus récentes
    quotidiennes = sorted(DOSSIER.glob("corsaire-????-??-??.db"))
    for ancienne in quotidiennes[:-GARDER]:
        ancienne.unlink()
    return nom


def liste_sauvegardes():
    if not DOSSIER.exists():
        return []
    return [{"nom": f.name, "taille": f.stat().st_size,
             "date": datetime.fromtimestamp(f.stat().st_mtime)}
            for f in sorted(DOSSIER.glob("corsaire-*.db"), key=lambda f: f.stat().st_mtime,
                            reverse=True)]


app.jinja_env.globals["liste_sauvegardes"] = liste_sauvegardes


@app.before_request
def sauvegarde_du_jour():
    """Au premier passage de la journée, une copie de la base est faite automatiquement."""
    if request.endpoint in (None, "static") or g.get("sauvegarde_verifiee"):
        return
    g.sauvegarde_verifiee = True
    if not (DOSSIER / f"corsaire-{date.today().isoformat()}.db").exists():
        try:
            sauvegarder()
        except (OSError, sqlite3.Error):
            pass  # une sauvegarde ratée ne doit jamais bloquer l'application


def _chemin(nom):
    if not NOM_VALIDE.match(nom or "") or not (DOSSIER / nom).exists():
        abort(404)
    return DOSSIER / nom


@app.route("/parametres/sauvegardes/<nom>")
def sauvegarde_telecharger(nom):
    return send_file(_chemin(nom), as_attachment=True, download_name=nom)


@app.route("/parametres/sauvegardes/maintenant", methods=["POST"])
def sauvegarde_maintenant():
    nom = sauvegarder(datetime.now().strftime("manuelle-%Y-%m-%d-%Hh%M"))
    flash(f"Sauvegarde créée : {nom}.", "succes")
    return redirect(url_for("parametres") + "#sauvegardes")


@app.route("/parametres/sauvegardes/restaurer", methods=["POST"])
def sauvegarde_restaurer():
    chemin = _chemin(request.form.get("nom"))
    if request.form.get("confirmation", "").strip().upper() != "CONFIRMER":
        flash("Tapez CONFIRMER pour restaurer une sauvegarde.", "erreur")
        return redirect(url_for("parametres") + "#sauvegardes")
    # Filet de sécurité : l'état actuel est sauvegardé avant d'être remplacé
    filet = sauvegarder(datetime.now().strftime("avant-restauration-%Y-%m-%d-%Hh%M"))
    source = sqlite3.connect(chemin)
    cible = sqlite3.connect(app.config["DATABASE"])
    with cible:
        source.backup(cible)
    cible.close()
    source.close()
    flash(f"Données restaurées depuis {chemin.name}. L'état précédent est gardé dans {filet}.",
          "succes")
    return redirect(url_for("parametres") + "#sauvegardes")


@app.route("/parametres/sauvegarde-complete.zip")
def sauvegarde_complete():
    """Base + justificatifs d'achat + logo, en un seul fichier."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        temporaire = DOSSIER / "export-temporaire.db"
        DOSSIER.mkdir(parents=True, exist_ok=True)
        copier_base(temporaire)
        z.write(temporaire, "corsaire.db")
        temporaire.unlink()
        for dossier in ("justificatifs", "logo", "photos"):
            for f in (INSTANCE / dossier).glob("*") if (INSTANCE / dossier).exists() else []:
                if f.is_file():
                    z.write(f, f"{dossier}/{f.name}")
    nom = f"MaisonCorsaire-sauvegarde-{date.today().isoformat()}.zip"
    return Response(tampon.getvalue(), mimetype="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})
