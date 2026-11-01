"""Avis clients : un QR code invite à noter un rhum et à donner ses idées."""
import os
import time
from datetime import datetime

from flask import Response, flash, redirect, render_template, request, session, url_for

from noyau import app, get_db, get_or_404, settings, to_int

MAX_TEXTE = 1000


def SCHEMA():
    return "https" if os.environ.get("HTTPS") == "1" else None


def resume_avis(conn, recette_id=None, publies=False):
    """Moyenne et nombre d'avis notés (tous, ou seulement les publiés)."""
    sql = "SELECT COUNT(note), AVG(note) FROM avis WHERE note IS NOT NULL"
    params = []
    if recette_id:
        sql += " AND recette_id = ?"
        params.append(recette_id)
    if publies:
        sql += " AND publie = 1"
    nb, moyenne = conn.execute(sql, params).fetchone()
    return {"nb": nb, "moyenne": round(moyenne, 1) if moyenne else None}


@app.route("/avis", methods=["GET", "POST"])
def avis_public():
    """Page publique (sans connexion), ouverte par le QR code du stand ou de la fiche produit."""
    conn = get_db()
    recettes = conn.execute("SELECT id, nom FROM recettes ORDER BY nom").fetchall()
    choisie = to_int(request.values.get("recette"))
    lot = (request.values.get("lot") or "").strip()[:30] or None
    if request.method == "POST":
        f = request.form
        # Anti-robots : champ piège invisible + 5 avis maximum par heure et par téléphone
        envois = [t for t in session.get("avis_envois", []) if t > time.time() - 3600]
        note = to_int(f.get("note"))
        note = note if 1 <= note <= 5 else None
        commentaire = f.get("commentaire", "").strip()[:MAX_TEXTE] or None
        conseil = f.get("conseil", "").strip()[:MAX_TEXTE] or None
        if f.get("site_web"):
            return render_template("avis_public.html", merci=True, conf=settings())
        if len(envois) >= 5:
            flash("Merci ! Vous avez déjà envoyé plusieurs avis, réessayez un peu plus tard.", "erreur")
        elif not (note or commentaire or conseil):
            flash("Donnez une note, un avis ou un conseil.", "erreur")
        else:
            recette_id = choisie if any(r["id"] == choisie for r in recettes) else None
            email = f.get("email", "").strip()[:120] or None
            if email and "@" not in email:
                email = None
            prenom = f.get("prenom", "").strip()[:60] or None
            conn.execute(
                "INSERT INTO avis (recette_id, lot_numero, note, commentaire, conseil, prenom, email,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (recette_id, lot, note, commentaire, conseil, prenom, email,
                 datetime.now().isoformat(timespec="seconds")))
            if email and f.get("nouveautes"):  # inscription aux nouveautés (consentement explicite)
                client = conn.execute("SELECT id FROM clients WHERE lower(email) = lower(?)",
                                      (email,)).fetchone()
                if client:
                    conn.execute("UPDATE clients SET accepte_infos = 1 WHERE id = ?", (client["id"],))
                else:
                    conn.execute(
                        "INSERT INTO clients (nom, type, email, notes, accepte_infos, created_at)"
                        " VALUES (?, 'particulier', ?, 'Inscrit via un avis client', 1, ?)",
                        (prenom or email.split("@")[0], email,
                         datetime.now().isoformat(timespec="seconds")))
            conn.commit()
            session["avis_envois"] = envois + [time.time()]
            return render_template("avis_public.html", merci=True, conf=settings())
    return render_template("avis_public.html", recettes=recettes, choisie=choisie, lot=lot,
                           conf=settings(), form=request.form)


@app.route("/avis-clients")
def avis_clients():
    conn = get_db()
    filtre = request.args.get("filtre", "tous")
    recette = to_int(request.args.get("recette"))
    sql = """SELECT a.*, r.nom AS recette_nom FROM avis a LEFT JOIN recettes r ON r.id = a.recette_id
             WHERE 1 = 1"""
    params = []
    if filtre == "nouveaux":
        sql += " AND a.lu = 0"
    elif filtre == "conseils":
        sql += " AND a.conseil IS NOT NULL"
    elif filtre == "publies":
        sql += " AND a.publie = 1"
    if recette:
        sql += " AND a.recette_id = ?"
        params.append(recette)
    liste = conn.execute(sql + " ORDER BY a.created_at DESC", params).fetchall()
    par_recette = conn.execute(
        """SELECT r.id, r.nom, COUNT(a.id) AS nb, AVG(a.note) AS moyenne,
                  SUM(CASE WHEN a.conseil IS NOT NULL THEN 1 ELSE 0 END) AS conseils
           FROM recettes r JOIN avis a ON a.recette_id = r.id GROUP BY r.id ORDER BY moyenne DESC"""
    ).fetchall()
    nouveaux = conn.execute("SELECT COUNT(*) FROM avis WHERE lu = 0").fetchone()[0]
    lien = url_for("avis_public", _external=True, _scheme=SCHEMA())
    return render_template("avis_clients.html", liste=liste, par_recette=par_recette,
                           global_=resume_avis(conn), nouveaux=nouveaux, filtre=filtre,
                           recette=recette, lien=lien,
                           recettes=conn.execute("SELECT id, nom FROM recettes ORDER BY nom").fetchall())


@app.route("/avis-clients/<int:avis_id>", methods=["POST"])
def avis_action(avis_id):
    conn = get_db()
    get_or_404("avis", avis_id)
    action = request.form.get("action")
    if action == "supprimer":
        conn.execute("DELETE FROM avis WHERE id = ?", (avis_id,))
        flash("Avis supprimé.", "succes")
    elif action == "publier":
        conn.execute("UPDATE avis SET publie = 1, lu = 1 WHERE id = ?", (avis_id,))
        flash("Avis publié sur la fiche produit (prénom seulement, jamais l'email).", "succes")
    elif action == "masquer":
        conn.execute("UPDATE avis SET publie = 0 WHERE id = ?", (avis_id,))
    elif action == "lu":
        conn.execute("UPDATE avis SET lu = 1 WHERE id = ?", (avis_id,))
    conn.commit()
    return redirect(request.form.get("retour") or url_for("avis_clients"))


@app.route("/avis-clients/tout-lu", methods=["POST"])
def avis_tout_lu():
    get_db().execute("UPDATE avis SET lu = 1")
    get_db().commit()
    return redirect(url_for("avis_clients"))


@app.route("/avis-clients/affiche.pdf")
def avis_affiche():
    from pdfs import affiche_avis_pdf
    recette = to_int(request.args.get("recette"))
    nom = None
    if recette:
        nom = get_or_404("recettes", recette)["nom"]
    lien = url_for("avis_public", recette=recette or None, _external=True, _scheme=SCHEMA())
    format_ = "A6" if request.args.get("format") == "A6" else "A5"
    pdf = affiche_avis_pdf(lien, settings(), nom, format_)
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="Affiche-avis.pdf"'})


def avis_publies(conn, recette_id, limite=5):
    return conn.execute(
        """SELECT prenom, note, commentaire, created_at FROM avis
           WHERE recette_id = ? AND publie = 1 AND commentaire IS NOT NULL
           ORDER BY created_at DESC LIMIT ?""", (recette_id, limite)).fetchall()
