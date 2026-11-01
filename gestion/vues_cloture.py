"""Clôture de marché : ventes de la journée, caisse espèces comptée et bouteilles rapportées."""
import json

from flask import flash, redirect, render_template, request, url_for

from calculs import to_float
from noyau import MODES_PAIEMENT, app, get_db, get_or_404, to_int, today


def resume_evenement(conn, evt_id):
    produits = conn.execute(
        """SELECT v.lot_id, l.numero, COALESCE(l.recette_nom, '') AS recette_nom, l.volume_cl,
                  SUM(v.quantite) AS quantite, SUM(v.quantite * v.prix_unitaire_ttc) AS montant
           FROM ventes v JOIN tickets t ON t.id = v.ticket_id LEFT JOIN lots l ON l.id = v.lot_id
           WHERE t.evenement_id = ? GROUP BY v.lot_id ORDER BY quantite DESC""",
        (evt_id,)).fetchall()
    modes = conn.execute(
        """SELECT mode_paiement, COUNT(*) AS nb, SUM(total) AS total FROM tickets
           WHERE evenement_id = ? GROUP BY mode_paiement ORDER BY total DESC""",
        (evt_id,)).fetchall()
    tickets = conn.execute(
        "SELECT COUNT(*) AS nb, COALESCE(SUM(sous_total - remise), 0) AS ca,"
        " COALESCE(SUM(total), 0) AS encaisse FROM tickets WHERE evenement_id = ?",
        (evt_id,)).fetchone()
    especes = sum(m["total"] for m in modes if m["mode_paiement"] == "especes")
    return {"produits": produits, "modes": modes, "nb": tickets["nb"], "ca": tickets["ca"],
            "encaisse": tickets["encaisse"], "especes": especes,
            "panier": tickets["ca"] / tickets["nb"] if tickets["nb"] else 0}


@app.route("/agenda/<int:evt_id>/cloture", methods=["GET", "POST"])
def cloture(evt_id):
    conn = get_db()
    evt = get_or_404("evenements", evt_id)
    r = resume_evenement(conn, evt_id)
    existante = conn.execute("SELECT * FROM clotures WHERE evenement_id = ? ORDER BY id DESC",
                             (evt_id,)).fetchone()
    # Lots proposés pour le comptage : ceux vendus ce jour-là + ceux en stock
    lots = conn.execute(
        """SELECT id, numero, recette_nom, volume_cl FROM lots
           WHERE statut = 'embouteille' OR id IN (SELECT v.lot_id FROM ventes v
             JOIN tickets t ON t.id = v.ticket_id WHERE t.evenement_id = ?)
           ORDER BY recette_nom, volume_cl""", (evt_id,)).fetchall()
    vendues = {p["lot_id"]: p["quantite"] for p in r["produits"]}

    if request.method == "POST":
        fond = max(to_float(request.form.get("fond_caisse")), 0)
        comptees = request.form.get("especes_comptees", "").strip()
        bouteilles = {}
        for l in lots:
            emp = request.form.get(f"emp_{l['id']}", "").strip()
            rap = request.form.get(f"rap_{l['id']}", "").strip()
            if emp or rap:
                bouteilles[str(l["id"])] = {"emportees": to_int(emp), "rapportees": to_int(rap)}
        if existante:
            conn.execute("DELETE FROM clotures WHERE evenement_id = ?", (evt_id,))
        conn.execute(
            "INSERT INTO clotures (evenement_id, date_cloture, fond_caisse, especes_comptees,"
            " especes_attendues, notes, bouteilles) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (evt_id, today(), fond, to_float(comptees) if comptees else None,
             round(fond + r["especes"], 2), request.form.get("notes", "").strip() or None,
             json.dumps(bouteilles)))
        conn.commit()
        flash("Clôture enregistrée.", "succes")
        return redirect(url_for("cloture", evt_id=evt_id))

    saisie = json.loads(existante["bouteilles"] or "{}") if existante else {}
    comptage = []
    for l in lots:
        s = saisie.get(str(l["id"]), {})
        v = vendues.get(l["id"], 0)
        ecart = None
        if s:
            ecart = s.get("emportees", 0) - v - s.get("rapportees", 0)
        comptage.append({"l": l, "vendues": v, "emportees": s.get("emportees"),
                         "rapportees": s.get("rapportees"), "ecart": ecart})
    fond = existante["fond_caisse"] if existante else 0
    ecart_caisse = None
    if existante and existante["especes_comptees"] is not None:
        ecart_caisse = round(existante["especes_comptees"] - (fond + r["especes"]), 2)
    return render_template("cloture.html", e=evt, r=r, c=existante, fond=fond,
                           attendu=round(fond + r["especes"], 2), ecart_caisse=ecart_caisse,
                           comptage=comptage, MODES=MODES_PAIEMENT)
