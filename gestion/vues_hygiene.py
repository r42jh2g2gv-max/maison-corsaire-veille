"""Cahier d'hygiène : plan de nettoyage, contrôles et non-conformités (plan de maîtrise sanitaire)."""
from datetime import date, datetime, timedelta
from io import BytesIO

from flask import Response, flash, redirect, render_template, request, url_for
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from noyau import app, get_db, get_or_404, parse_date, settings, to_int, today
from pdfs import GRIS, NUIT, OR, _date, _decouper

TYPES_HYGIENE = {"nettoyage": "Nettoyage", "controle": "Contrôle", "reception": "Réception marchandise",
                 "nuisibles": "Nuisibles", "non_conformite": "Incident", "formation": "Formation",
                 "autre": "Autre"}
CATEGORIES_TACHES = {"nettoyage": "Nettoyage", "controle": "Contrôle", "nuisibles": "Nuisibles",
                     "autre": "Autre"}
app.jinja_env.globals["TYPES_HYGIENE"] = TYPES_HYGIENE
app.jinja_env.globals["CATEGORIES_TACHES"] = CATEGORIES_TACHES


def plan(conn):
    """Chaque tâche avec son dernier passage et sa prochaine échéance."""
    ajd = date.today()
    taches = []
    for t in conn.execute("SELECT * FROM hygiene_taches WHERE actif = 1 ORDER BY "
                          "frequence_jours IS NULL, frequence_jours, nom"):
        dernier = conn.execute("SELECT MAX(date_releve) FROM hygiene_releves WHERE tache_id = ?",
                               (t["id"],)).fetchone()[0]
        prochaine, etat = None, "ok"
        if t["frequence_jours"]:
            prochaine = (date.fromisoformat(dernier) + timedelta(days=t["frequence_jours"])
                         if dernier else ajd)
            if prochaine < ajd:
                etat = "retard"
            elif prochaine == ajd or not dernier:
                etat = "urgent"
        taches.append({"t": t, "dernier": dernier, "prochaine": prochaine.isoformat()
                       if prochaine else None, "etat": etat})
    return taches


def rappels_hygiene(conn):
    return [x for x in plan(conn) if x["etat"] in ("retard", "urgent")]


@app.route("/hygiene", methods=["GET", "POST"])
def hygiene():
    conn = get_db()
    if request.method == "POST":
        f = request.form
        tache = conn.execute("SELECT * FROM hygiene_taches WHERE id = ?",
                             (to_int(f.get("tache_id")),)).fetchone()
        objet = f.get("objet", "").strip() or (tache["nom"] if tache else "")
        resultat = "non_conforme" if f.get("resultat") == "non_conforme" else "conforme"
        action = f.get("action_corrective", "").strip() or None
        type_ = f.get("type") if f.get("type") in TYPES_HYGIENE else (
            tache["categorie"] if tache and tache["categorie"] in TYPES_HYGIENE else "autre")
        if not objet:
            flash("Indiquez ce qui a été fait ou contrôlé.", "erreur")
            return redirect(url_for("hygiene") + "#nouveau")
        if resultat == "non_conforme" and not action:
            flash("Non conforme : notez l'action corrective (ce que vous avez fait).", "erreur")
            return redirect(url_for("hygiene") + "#nouveau")
        from vues_degustations import enregistrer_photo
        photo = enregistrer_photo(request.files.get("photo"), "hygiene")
        conn.execute(
            "INSERT INTO hygiene_releves (date_releve, tache_id, type, objet, resultat,"
            " action_corrective, lot_id, fait_par, photo, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (parse_date(f.get("date")) or today(), tache["id"] if tache else None, type_, objet,
             resultat, action, to_int(f.get("lot_id")) or None,
             f.get("fait_par", "").strip() or None, photo,
             datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        flash("Enregistré dans le cahier d'hygiène.", "succes")
        return redirect(url_for("hygiene"))
    type_filtre = request.args.get("type")
    sql = """SELECT h.*, l.numero AS lot_numero FROM hygiene_releves h
             LEFT JOIN lots l ON l.id = h.lot_id"""
    params = []
    if type_filtre in TYPES_HYGIENE:
        sql += " WHERE h.type = ?"
        params.append(type_filtre)
    elif type_filtre == "nc":
        sql += " WHERE h.resultat = 'non_conforme'"
    journal = conn.execute(sql + " ORDER BY h.date_releve DESC, h.id DESC LIMIT 100",
                           params).fetchall()
    return render_template(
        "hygiene.html", plan=plan(conn), journal=journal, type_filtre=type_filtre,
        taches=conn.execute("SELECT * FROM hygiene_taches ORDER BY actif DESC, nom").fetchall(),
        lots=conn.execute("SELECT id, numero, recette_nom FROM lots WHERE statut IN"
                          " ('maceration', 'pret', 'embouteille') ORDER BY numero DESC").fetchall(),
        debut=(date.today() - timedelta(days=365)).isoformat())


@app.route("/hygiene/fait/<int:tache_id>", methods=["POST"])
def hygiene_fait(tache_id):
    """Un geste : la tâche du plan est faite aujourd'hui, conforme."""
    conn = get_db()
    t = get_or_404("hygiene_taches", tache_id)
    conn.execute(
        "INSERT INTO hygiene_releves (date_releve, tache_id, type, objet, resultat, created_at)"
        " VALUES (?, ?, ?, ?, 'conforme', ?)",
        (today(), tache_id, t["categorie"] if t["categorie"] in TYPES_HYGIENE else "autre",
         t["nom"], datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    flash(f"« {t['nom']} » noté comme fait aujourd'hui.", "succes")
    return redirect(url_for("hygiene"))


@app.route("/hygiene/releve/<int:rid>/supprimer", methods=["POST"])
def hygiene_supprimer(rid):
    conn = get_db()
    r = get_or_404("hygiene_releves", rid)
    if r["photo"]:
        from vues_degustations import PHOTOS
        (PHOTOS / r["photo"]).unlink(missing_ok=True)
    conn.execute("DELETE FROM hygiene_releves WHERE id = ?", (rid,))
    conn.commit()
    flash("Enregistrement supprimé.", "succes")
    return redirect(url_for("hygiene"))


@app.route("/hygiene/taches", methods=["POST"])
def hygiene_taches():
    """Ajout / modification / suppression des tâches du plan."""
    conn = get_db()
    f = request.form
    tid = to_int(f.get("id"))
    if f.get("action") == "supprimer" and tid:
        conn.execute("DELETE FROM hygiene_taches WHERE id = ?", (tid,))
        flash("Tâche retirée du plan (l'historique est conservé).", "succes")
    else:
        nom = f.get("nom", "").strip()
        if not nom:
            flash("Donnez un nom à la tâche.", "erreur")
            return redirect(url_for("hygiene") + "#plan-gerer")
        valeurs = (nom, f.get("categorie") if f.get("categorie") in CATEGORIES_TACHES else "autre",
                   to_int(f.get("frequence_jours")) or None, 1 if f.get("actif", "1") else 0)
        if tid:
            conn.execute("UPDATE hygiene_taches SET nom = ?, categorie = ?, frequence_jours = ?,"
                         " actif = ? WHERE id = ?", (*valeurs, tid))
        else:
            conn.execute("INSERT INTO hygiene_taches (nom, categorie, frequence_jours, actif)"
                         " VALUES (?, ?, ?, ?)", valeurs)
        flash("Plan d'hygiène mis à jour.", "succes")
    conn.commit()
    return redirect(url_for("hygiene") + "#plan-gerer")


@app.route("/hygiene/registre.pdf")
def hygiene_registre():
    """Registre à présenter lors d'un contrôle : plan + enregistrements de la période."""
    conn = get_db()
    conf = settings()
    debut = parse_date(request.args.get("debut")) or (date.today() - timedelta(days=365)).isoformat()
    fin = parse_date(request.args.get("fin")) or today()
    releves = conn.execute(
        """SELECT h.*, l.numero AS lot_numero FROM hygiene_releves h LEFT JOIN lots l ON l.id = h.lot_id
           WHERE h.date_releve BETWEEN ? AND ? ORDER BY h.date_releve, h.id""", (debut, fin)).fetchall()
    taches = plan(conn)
    buf = BytesIO()
    taille = landscape(A4)
    L, H = taille
    m = 12 * mm
    c = canvas.Canvas(buf, pagesize=taille)
    c.setTitle("Registre d'hygiène")

    def entete():
        c.setFillColor(OR)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(m, H - m, "REGISTRE D'HYGIÈNE · PLAN DE MAÎTRISE SANITAIRE")
        c.setFillColor(NUIT)
        c.setFont("Times-Bold", 16)
        c.drawString(m, H - m - 7 * mm, conf.get("producteur_nom") or "Maison Corsaire")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(GRIS)
        c.drawRightString(L - m, H - m - 7 * mm, f"Période du {_date(debut)} au {_date(fin)}"
                          + (f" · SIRET {conf['siret']}" if conf.get("siret") else ""))
        return H - m - 15 * mm

    y = entete()
    c.setFillColor(OR)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(m, y, "PLAN DE NETTOYAGE ET DE CONTRÔLE")
    y -= 6 * mm
    c.setFont("Helvetica", 8.5)
    for x in taches:
        t = x["t"]
        c.setFillColor(NUIT)
        c.drawString(m, y, f"• {t['nom']}"[:110])
        freq = (f"tous les {t['frequence_jours']} jours" if t["frequence_jours"]
                else "à chaque production / marché")
        c.setFillColor(GRIS)
        c.drawString(m + 175 * mm, y, freq)
        c.drawString(m + 225 * mm, y, f"dernier : {_date(x['dernier'])}" if x["dernier"] else "—")
        y -= 4.6 * mm
    y -= 4 * mm

    colonnes = [("Date", 20), ("Type", 30), ("Opération / contrôle", 92), ("Lot", 24),
                ("Résultat", 22), ("Action corrective", 70), ("Par", 15)]

    def tete_tableau(y):
        c.setFillColor(NUIT)
        c.rect(m, y - 2.2 * mm, L - 2 * m, 7 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0.92, 0.79, 0.51)
        c.setFont("Helvetica-Bold", 8)
        x = m
        for t, w in colonnes:
            c.drawString(x + 1.5 * mm, y, t)
            x += w * mm
        return y - 7.5 * mm

    y = tete_tableau(y)
    for r in releves:
        cellules = [_date(r["date_releve"]), TYPES_HYGIENE.get(r["type"], r["type"]), r["objet"],
                    r["lot_numero"] or "", "Conforme" if r["resultat"] == "conforme" else "NON CONFORME",
                    r["action_corrective"] or "", r["fait_par"] or ""]
        lignes = [_decouper(c, str(v), "Helvetica", 8, w * mm - 3 * mm) or [""]
                  for v, (_, w) in zip(cellules, colonnes)]
        hauteur = max(len(l) for l in lignes) * 3.8 * mm
        if y - hauteur < 14 * mm:
            c.showPage()
            y = tete_tableau(entete())
        x = m
        for (texte, (_, w)), contenu in zip(zip(cellules, colonnes), lignes):
            non_conf = texte == "NON CONFORME"
            c.setFont("Helvetica-Bold" if non_conf else "Helvetica", 8)
            c.setFillColorRGB(0.75, 0.15, 0.1) if non_conf else c.setFillColor(NUIT)
            yy = y
            for ligne in contenu:
                c.drawString(x + 1.5 * mm, yy, ligne)
                yy -= 3.8 * mm
            x += w * mm
        y -= hauteur
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.line(m, y + 1.5 * mm, L - m, y + 1.5 * mm)
        y -= 2.5 * mm
    if not releves:
        c.setFont("Helvetica", 9)
        c.setFillColor(GRIS)
        c.drawString(m, y, "Aucun enregistrement sur la période.")
    c.showPage()
    c.save()
    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="Registre-hygiene.pdf"'})
