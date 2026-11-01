"""Carnet de dégustation : notes et photos de chaque lot, pour comparer essais et variantes."""
from datetime import date, datetime

from flask import abort, flash, redirect, render_template, request, send_file, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename

from noyau import INSTANCE, app, get_db, get_lot, get_or_404, parse_date, to_int, today

PHOTOS = INSTANCE / "photos"


def degustations_du_lot(conn, lot_id):
    return conn.execute(
        "SELECT * FROM degustations WHERE lot_id = ? ORDER BY date_degustation DESC, id DESC",
        (lot_id,)).fetchall()


app.jinja_env.globals["degustations_du_lot"] = lambda lot_id: degustations_du_lot(get_db(), lot_id)


def jour_maceration(lot, jour):
    if not lot["date_maceration"] or not jour:
        return None
    return (date.fromisoformat(jour) - date.fromisoformat(lot["date_maceration"])).days


app.jinja_env.globals["jour_maceration"] = jour_maceration


def enregistrer_photo(fichier, lot_id):
    if not fichier or not fichier.filename:
        return None
    try:
        image = ImageOps.exif_transpose(Image.open(fichier.stream)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        flash("Photo illisible : elle n'a pas été enregistrée.", "erreur")
        return None
    image.thumbnail((1600, 1600))  # photos iPhone allégées
    PHOTOS.mkdir(parents=True, exist_ok=True)
    nom = f"lot{lot_id}-{datetime.now():%Y%m%d%H%M%S}.jpg"
    image.save(PHOTOS / secure_filename(nom), quality=82, optimize=True)
    return nom


@app.route("/lots/<int:lot_id>/degustations", methods=["POST"])
def degustation_ajouter(lot_id):
    conn = get_db()
    get_lot(lot_id)
    note = to_int(request.form.get("note")) or None
    commentaire = request.form.get("commentaire", "").strip() or None
    photo = enregistrer_photo(request.files.get("photo"), lot_id)
    if not (note or commentaire or photo):
        flash("Indiquez une note, un commentaire ou une photo.", "erreur")
    else:
        conn.execute(
            "INSERT INTO degustations (lot_id, date_degustation, note, commentaire, photo)"
            " VALUES (?, ?, ?, ?, ?)",
            (lot_id, parse_date(request.form.get("date")) or today(),
             min(max(note, 1), 5) if note else None, commentaire, photo))
        conn.commit()
        flash("Dégustation notée dans le carnet.", "succes")
    return redirect(url_for("lot_detail", lot_id=lot_id) + "#carnet")


@app.route("/degustations/<int:deg_id>/supprimer", methods=["POST"])
def degustation_supprimer(deg_id):
    conn = get_db()
    d = get_or_404("degustations", deg_id)
    if d["photo"]:
        (PHOTOS / d["photo"]).unlink(missing_ok=True)
    conn.execute("DELETE FROM degustations WHERE id = ?", (deg_id,))
    conn.commit()
    flash("Dégustation supprimée.", "succes")
    return redirect(url_for("lot_detail", lot_id=d["lot_id"]) + "#carnet")


@app.route("/photos/<nom>")
def photo(nom):
    chemin = PHOTOS / secure_filename(nom)
    if not chemin.exists():
        abort(404)
    return send_file(chemin, max_age=86400)


@app.route("/degustations")
def carnet():
    """Toutes les dégustations, par recette : pour comparer essais et variantes."""
    conn = get_db()
    rows = conn.execute(
        """SELECT d.*, l.numero, l.recette_nom, l.recette_id, l.essai, l.date_maceration
           FROM degustations d JOIN lots l ON l.id = d.lot_id
           ORDER BY l.recette_nom, d.date_degustation DESC""").fetchall()
    groupes = {}
    for d in rows:
        g = groupes.setdefault(d["recette_nom"], {"lignes": [], "notes": []})
        g["lignes"].append(d)
        if d["note"]:
            g["notes"].append(d["note"])
    return render_template("degustations.html", groupes=groupes)


def resume_recette(conn, recette_id):
    r = conn.execute(
        """SELECT COUNT(*) n, AVG(d.note) moyenne,
                  SUM(CASE WHEN l.essai = 1 THEN 1 ELSE 0 END) essais
           FROM degustations d JOIN lots l ON l.id = d.lot_id WHERE l.recette_id = ?""",
        (recette_id,)).fetchone()
    return r if r["n"] else None


app.jinja_env.globals["resume_degustations"] = lambda rid: resume_recette(get_db(), rid)
