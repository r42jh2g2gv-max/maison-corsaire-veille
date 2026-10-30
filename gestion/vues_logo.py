"""Logo personnalisé : en-tête de l'appli, icône de l'écran d'accueil et documents PDF."""
from io import BytesIO

from flask import abort, flash, redirect, request, send_file, url_for
from PIL import Image, ImageOps, UnidentifiedImageError

from noyau import BASE, INSTANCE, app, get_db, set_setting, settings

DOSSIER = INSTANCE / "logo"
LOGO = DOSSIER / "logo.png"
# nom servi → (taille, marge relative) ; la marge « maskable » protège le logo des découpes Android
ICONES = {"icone-192": (192, 0.10), "icone-512": (512, 0.10),
          "icone-maskable-512": (512, 0.20), "apple-touch-icon": (180, 0.10)}


def logo_perso():
    return LOGO if LOGO.exists() else None


def version_logo():
    return str(int(LOGO.stat().st_mtime)) if LOGO.exists() else "0"


app.jinja_env.globals.update(logo_perso=logo_perso, version_logo=version_logo)


def _couleur(hexa, defaut=(10, 19, 34)):
    hexa = (hexa or "").lstrip("#")
    try:
        return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4)) if len(hexa) == 6 else defaut
    except ValueError:
        return defaut


def generer_icones(image, fond, plein_cadre):
    """Crée les icônes carrées à partir du logo, centré sur la couleur de fond."""
    for nom, (taille, marge) in ICONES.items():
        marge = 0 if plein_cadre and nom != "icone-maskable-512" else marge
        icone = Image.new("RGB", (taille, taille), fond)
        place = int(taille * (1 - 2 * marge))
        copie = image.copy()
        if plein_cadre:
            copie = ImageOps.fit(copie, (place, place), Image.LANCZOS)
        else:
            copie.thumbnail((place, place), Image.LANCZOS)
        position = ((taille - copie.width) // 2, (taille - copie.height) // 2)
        icone.paste(copie, position, copie if copie.mode == "RGBA" else None)
        icone.save(DOSSIER / f"{nom}.png", optimize=True)


@app.route("/parametres/logo", methods=["POST"])
def parametres_logo():
    fichier = request.files.get("logo")
    fond = request.form.get("fond", "#0a1322")
    plein_cadre = bool(request.form.get("plein_cadre"))
    set_setting("logo_fond", fond)
    set_setting("logo_plein_cadre", "1" if plein_cadre else "0")
    get_db().commit()
    if fichier and fichier.filename:
        try:
            image = Image.open(fichier.stream)
            image = ImageOps.exif_transpose(image).convert("RGBA")  # photo iPhone : bon sens
        except (UnidentifiedImageError, OSError):
            flash("Image illisible : envoyez une photo ou une image PNG ou JPEG.", "erreur")
            return redirect(url_for("parametres") + "#logo")
        if image.getbbox():
            image = image.crop(image.getbbox())  # retire les bords transparents
        image.thumbnail((1024, 1024), Image.LANCZOS)
        DOSSIER.mkdir(parents=True, exist_ok=True)
        image.save(LOGO, optimize=True)
    elif not LOGO.exists():
        flash("Choisissez d'abord une image.", "erreur")
        return redirect(url_for("parametres") + "#logo")
    generer_icones(Image.open(LOGO).convert("RGBA"), _couleur(fond), plein_cadre)
    flash("Logo enregistré. Pour changer l'icône de l'iPhone : supprimez l'icône de l'écran "
          "d'accueil puis ajoutez-la de nouveau depuis Safari.", "succes")
    return redirect(url_for("parametres") + "#logo")


@app.route("/parametres/logo/supprimer", methods=["POST"])
def parametres_logo_supprimer():
    if DOSSIER.exists():
        for f in DOSSIER.glob("*.png"):
            f.unlink()
    flash("Logo retiré : l'ancre Maison Corsaire est rétablie.", "succes")
    return redirect(url_for("parametres") + "#logo")


@app.route("/icone/<nom>.png")
def icone(nom):
    """Icône personnalisée si un logo a été envoyé, sinon l'icône d'origine."""
    if nom == "logo":
        if not LOGO.exists():
            abort(404)
        return send_file(LOGO, max_age=86400)
    if nom not in ICONES:
        abort(404)
    perso = DOSSIER / f"{nom}.png"
    chemin = perso if perso.exists() and LOGO.exists() else BASE / "static" / "icones" / f"{nom}.png"
    return send_file(chemin, max_age=86400)


def logo_pour_pdf():
    """Logo en mémoire pour reportlab (ou None)."""
    if not LOGO.exists():
        return None
    return BytesIO(LOGO.read_bytes())


app.jinja_env.globals["logo_fond"] = lambda: settings().get("logo_fond") or "#0a1322"
