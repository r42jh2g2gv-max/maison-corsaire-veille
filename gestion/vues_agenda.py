"""Agenda : marchés, salons, dégustations et leur bilan."""
from flask import flash, redirect, render_template, request, url_for

from calculs import to_float
from noyau import (TYPES_EVENEMENTS, app, couts_par_lot, get_db, get_or_404, parse_date,
                   redirection_sure, settings, to_int, today)
from rappels import calculer_rappels


def lire_evenement(form):
    return {
        "nom": form.get("nom", "").strip(),
        "type": form.get("type") if form.get("type") in TYPES_EVENEMENTS else "autre",
        "date_debut": parse_date(form.get("date_debut")),
        "date_fin": parse_date(form.get("date_fin")),
        "lieu": form.get("lieu", "").strip(),
        "cout_place": max(to_float(form.get("cout_place")), 0),
        "btl_prevues": max(to_int(form.get("btl_prevues")), 0),
        "date_limite_inscription": parse_date(form.get("date_limite_inscription")),
        "inscrit": 1 if form.get("inscrit") else 0,
        "stock_pret": 1 if form.get("stock_pret") else 0,
        "notes": form.get("notes", "").strip(),
    }


@app.route("/agenda")
def agenda():
    conn = get_db()
    a_venir = conn.execute(
        "SELECT * FROM evenements WHERE COALESCE(date_fin, date_debut) >= ? ORDER BY date_debut",
        (today(),)).fetchall()
    passes = conn.execute(
        "SELECT * FROM evenements WHERE COALESCE(date_fin, date_debut) < ?"
        " ORDER BY date_debut DESC", (today(),)).fetchall()
    couts = couts_par_lot(conn, settings())
    bilans = []
    for e in passes:
        lignes = conn.execute(
            """SELECT v.lot_id, v.quantite FROM ventes v JOIN tickets t ON t.id = v.ticket_id
               WHERE t.evenement_id = ?""", (e["id"],)).fetchall()
        ca = conn.execute(
            "SELECT COALESCE(SUM(sous_total - remise), 0) FROM tickets WHERE evenement_id = ?",
            (e["id"],)).fetchone()[0]
        btl = sum(l["quantite"] for l in lignes)
        cout = sum(l["quantite"] * couts.get(l["lot_id"], 0) for l in lignes)
        bilans.append({"e": e, "btl": btl, "ca": ca, "cout": cout,
                       "benefice": ca - cout - e["cout_place"]})
    rappels = [r for r in calculer_rappels(conn, settings())
               if r["icone"] in ("calendrier", "caisse")]
    return render_template("agenda.html", a_venir=a_venir, bilans=bilans, rappels=rappels,
                           evenement={"type": "marche"})


@app.route("/agenda/nouveau", methods=["POST"])
def evenement_nouveau():
    data = lire_evenement(request.form)
    if not data["nom"] or not data["date_debut"]:
        flash("Le nom et la date de l'événement sont obligatoires.", "erreur")
        return redirect(url_for("agenda") + "#nouveau")
    get_db().execute(
        """INSERT INTO evenements (nom, type, date_debut, date_fin, lieu, cout_place, btl_prevues,
           date_limite_inscription, inscrit, stock_pret, notes) VALUES (:nom, :type, :date_debut,
           :date_fin, :lieu, :cout_place, :btl_prevues, :date_limite_inscription, :inscrit,
           :stock_pret, :notes)""", data)
    get_db().commit()
    flash(f"« {data['nom']} » ajouté à l'agenda.", "succes")
    return redirect(url_for("agenda"))


@app.route("/agenda/<int:evt_id>/modifier", methods=["GET", "POST"])
def evenement_modifier(evt_id):
    evt = get_or_404("evenements", evt_id)
    if request.method == "POST":
        data = lire_evenement(request.form)
        if not data["nom"] or not data["date_debut"]:
            flash("Le nom et la date de l'événement sont obligatoires.", "erreur")
        else:
            get_db().execute(
                """UPDATE evenements SET nom = :nom, type = :type, date_debut = :date_debut,
                   date_fin = :date_fin, lieu = :lieu, cout_place = :cout_place,
                   btl_prevues = :btl_prevues, date_limite_inscription = :date_limite_inscription,
                   inscrit = :inscrit, stock_pret = :stock_pret, notes = :notes WHERE id = :id""",
                {**data, "id": evt_id})
            get_db().commit()
            flash("Événement mis à jour.", "succes")
            return redirect(url_for("agenda") + f"#evt-{evt_id}")
    return render_template("evenement_form.html", evenement=evt)


@app.route("/agenda/<int:evt_id>/basculer", methods=["POST"])
def evenement_basculer(evt_id):
    get_or_404("evenements", evt_id)
    champ = request.form.get("champ")
    if champ in ("inscrit", "stock_pret"):
        get_db().execute(f"UPDATE evenements SET {champ} = 1 - {champ} WHERE id = ?", (evt_id,))
        get_db().commit()
    return redirection_sure(request.form.get("retour"), url_for("agenda") + f"#evt-{evt_id}")


@app.route("/agenda/<int:evt_id>/supprimer", methods=["POST"])
def evenement_supprimer(evt_id):
    evt = get_or_404("evenements", evt_id)
    get_db().execute("DELETE FROM evenements WHERE id = ?", (evt_id,))
    get_db().commit()
    flash(f"« {evt['nom']} » supprimé de l'agenda (les ventes sont conservées).", "succes")
    return redirect(url_for("agenda"))
