"""Dépôt-vente : bouteilles confiées à un revendeur, facturées quand elles sont vendues."""
from datetime import date, datetime, timedelta

from flask import flash, redirect, render_template, request, url_for

import db as database
from calculs import taux_tva, to_float
from noyau import (app, get_db, get_or_404, lots_avec_stock, maj_statut_epuise,
                   parse_date, settings, stock_lot, to_int, today)


def etat_depot(conn, client_id):
    """Par lot : déposé, vendu, retourné, encore en dépôt (et prix HT convenu)."""
    rows = conn.execute(
        """SELECT d.lot_id, l.numero, l.recette_nom, l.volume_cl,
                  SUM(CASE d.type WHEN 'depot' THEN d.quantite ELSE 0 END) AS depose,
                  SUM(CASE d.type WHEN 'vente' THEN d.quantite ELSE 0 END) AS vendu,
                  SUM(CASE d.type WHEN 'retour' THEN d.quantite ELSE 0 END) AS retourne,
                  MAX(CASE d.type WHEN 'depot' THEN d.prix_unitaire_ht END) AS prix_ht,
                  MAX(d.date_mouvement) AS dernier
           FROM depots d JOIN lots l ON l.id = d.lot_id WHERE d.client_id = ?
           GROUP BY d.lot_id ORDER BY l.numero""", (client_id,)).fetchall()
    return [{**dict(r), "reste": r["depose"] - r["vendu"] - r["retourne"]} for r in rows]


@app.route("/depots")
def depots():
    conn = get_db()
    resume = []
    for c in conn.execute("SELECT * FROM clients WHERE type = 'revendeur' ORDER BY nom"):
        etat = etat_depot(conn, c["id"])
        resume.append({"c": c, "reste": sum(e["reste"] for e in etat),
                       "valeur": sum(e["reste"] * (e["prix_ht"] or 0) for e in etat),
                       "dernier": max((e["dernier"] for e in etat), default=None)})
    return render_template("depots.html", resume=resume)


@app.route("/clients/<int:client_id>/depot", methods=["GET", "POST"])
def depot_client(client_id):
    conn = get_db()
    client = get_or_404("clients", client_id)
    if request.method == "POST":
        action = request.form.get("action")
        jour = parse_date(request.form.get("date")) or today()
        if action == "deposer":
            lot_id = to_int(request.form.get("lot_id"))
            qte = to_int(request.form.get("quantite"))
            lot = lots_avec_stock("WHERE l.id = ?", (lot_id,))
            if not lot or qte <= 0 or qte > stock_lot(lot[0]):
                flash("Quantité impossible : vérifiez le stock du lot.", "erreur")
            else:
                conn.execute(
                    "INSERT INTO depots (client_id, lot_id, date_mouvement, type, quantite,"
                    " prix_unitaire_ht) VALUES (?, ?, ?, 'depot', ?, ?)",
                    (client_id, lot_id, jour, qte, to_float(request.form.get("prix_ht"), None)))
                maj_statut_epuise(conn, lot_id)
                conn.commit()
                flash(f"{qte} bouteille(s) déposée(s) chez {client['nom']}.", "succes")
        elif action in ("releve", "retour"):
            etat = {e["lot_id"]: e for e in etat_depot(conn, client_id)}
            mouvements = []
            for lot_id, e in etat.items():
                qte = to_int(request.form.get(f"q_{lot_id}"))
                if qte > e["reste"]:
                    flash(f"{e['recette_nom']} : seulement {e['reste']} bouteille(s) en dépôt.",
                          "erreur")
                    return redirect(url_for("depot_client", client_id=client_id))
                if qte > 0:
                    mouvements.append((lot_id, qte, e))
            if not mouvements:
                flash("Indiquez au moins une quantité.", "erreur")
            elif action == "retour":
                for lot_id, qte, _ in mouvements:
                    conn.execute(
                        "INSERT INTO depots (client_id, lot_id, date_mouvement, type, quantite)"
                        " VALUES (?, ?, ?, 'retour', ?)", (client_id, lot_id, jour, qte))
                    maj_statut_epuise(conn, lot_id, reouvrir=True)
                conn.commit()
                flash("Bouteilles reprises : remises en stock.", "succes")
            else:
                ticket_id = facturer_releve(conn, client, jour, mouvements)
                conn.commit()
                flash("Ventes du dépôt facturées : facture en attente de paiement.", "succes")
                return redirect(url_for("ticket_detail", ticket_id=ticket_id))
        return redirect(url_for("depot_client", client_id=client_id))

    lots = [l for l in lots_avec_stock("WHERE l.statut = 'embouteille' ORDER BY l.recette_nom")
            if stock_lot(l) > 0]
    tva = taux_tva(settings())
    return render_template("depot_client.html", client=client, etat=etat_depot(conn, client_id),
                           lots=lots, stock_lot=stock_lot, tva=tva)


def facturer_releve(conn, client, jour, mouvements):
    """Relevé du revendeur : les bouteilles vendues sont facturées (paiement à échéance)."""
    conf = settings()
    tva = taux_tva(conf)
    lignes = []
    for lot_id, qte, e in mouvements:
        lot = lots_avec_stock("WHERE l.id = ?", (lot_id,))[0]
        prix_ht = e["prix_ht"] or client["prix_revendeur_ht"] or lot["prix_revendeur_ht"] or 0
        lignes.append((lot_id, qte, round(prix_ht * (1 + tva), 2)))
    sous_total = round(sum(q * p for _, q, p in lignes), 2)
    echeance = (date.fromisoformat(jour)
                + timedelta(days=int(to_float(conf.get("delai_paiement"), 30)))).isoformat()
    cur = conn.execute(
        """INSERT INTO tickets (numero, date_vente, client_id, client_nom, canal, mode_paiement,
           sous_total, total, client_adresse, notes, created_at, paye, echeance, facture_numero,
           facture_date) VALUES (?, ?, ?, ?, 'revendeur', 'a_regler', ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
        (database.prochain_numero(conn, "tickets", "numero", "T", jour[:4], 4), jour, client["id"],
         client["nom"], sous_total, sous_total, client["adresse"], "Relevé de dépôt-vente",
         datetime.now().isoformat(timespec="seconds"), echeance,
         database.prochain_numero(conn, "tickets", "facture_numero", "F", jour[:4], 4), jour))
    ticket_id = cur.lastrowid
    for lot_id, qte, prix in lignes:
        conn.execute(
            "INSERT INTO ventes (ticket_id, date_vente, client, lot_id, quantite, prix_unitaire_ttc,"
            " canal, notes) VALUES (?, ?, ?, ?, ?, ?, 'revendeur', 'Dépôt-vente')",
            (ticket_id, jour, client["nom"], lot_id, qte, prix))
        conn.execute(
            "INSERT INTO depots (client_id, lot_id, date_mouvement, type, quantite, ticket_id)"
            " VALUES (?, ?, ?, 'vente', ?, ?)", (client["id"], lot_id, jour, qte, ticket_id))
        maj_statut_epuise(conn, lot_id)
    return ticket_id


