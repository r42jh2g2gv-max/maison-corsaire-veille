"""Module 4 — caisse, tickets, factures et historique des ventes."""
import json
from datetime import date, datetime, timedelta

from flask import (Response, abort, flash, jsonify, redirect, render_template, request,
                   url_for)

import db as database
from calculs import marge_pct, taux_tva, to_float
from emails import envoyer, smtp_configure
from noyau import (MODES_PAIEMENT, app, couts_par_lot, euro, get_db, get_or_404,
                   lots_avec_stock, maj_statut_epuise, mois_label, parse_date,
                   redirection_sure, settings, stock_lot, to_int, today)
from pdfs import facture_pdf, ticket_pdf


def lignes_ticket(conn, ticket_id):
    return conn.execute(
        """SELECT v.*, l.numero, l.recette_nom, l.volume_cl, l.degre
           FROM ventes v JOIN lots l ON l.id = v.lot_id WHERE v.ticket_id = ? ORDER BY v.id""",
        (ticket_id,),
    ).fetchall()


def bon_du_ticket(conn, ticket_id):
    row = conn.execute("SELECT code FROM bons WHERE ticket_id = ?", (ticket_id,)).fetchone()
    return row["code"] if row else None


def verifier_bon(conn, code, client_id, jour):
    """Retourne (bon, erreur)."""
    bon = conn.execute("SELECT * FROM bons WHERE upper(code) = ?",
                       (code.strip().upper(),)).fetchone()
    if not bon:
        return None, "Code de bon d'achat inconnu."
    if bon["ticket_id"]:
        return None, "Ce bon d'achat a déjà été utilisé."
    if bon["date_expiration"] and bon["date_expiration"] < jour:
        return None, f"Ce bon d'achat a expiré le {date.fromisoformat(bon['date_expiration']):%d/%m/%Y}."
    if bon["client_id"] and client_id and bon["client_id"] != client_id:
        return None, f"Ce bon est réservé à {bon['beneficiaire']}."
    return bon, None


# --------------------------------------------------------------------------
# Caisse
# --------------------------------------------------------------------------

@app.route("/caisse", methods=["GET", "POST"])
def caisse():
    conn = get_db()
    conf = settings()
    if request.method == "POST":
        ticket_id, erreurs = encaisser(conn, conf, request.form)
        if request.headers.get("X-Requested-With") == "fetch":
            if erreurs:
                return jsonify({"ok": False, "erreurs": erreurs})
            conn.commit()
            return jsonify({"ok": True, "url": url_for("ticket_detail", ticket_id=ticket_id,
                                                       nouveau=1)})
        if erreurs:
            for e in erreurs:
                flash(e, "erreur")
        else:
            conn.commit()
            return redirect(url_for("ticket_detail", ticket_id=ticket_id, nouveau=1))

    tva = taux_tva(conf)
    produits = [
        {"id": l["id"], "numero": l["numero"], "nom": l["recette_nom"],
         "volume": l["volume_cl"], "stock": stock_lot(l),
         "prix": l["prix_vente_ttc"] or 0,
         "prix_rev": round((l["prix_revendeur_ht"] or 0) * (1 + tva), 2)}
        for l in lots_avec_stock("WHERE l.statut = 'embouteille' ORDER BY l.recette_nom")
        if stock_lot(l) > 0
    ]
    clients = [
        {"id": c["id"], "nom": c["nom"], "type": c["type"],
         "prix_rev": round((c["prix_revendeur_ht"] or 0) * (1 + tva), 2),
         "consignes": c["consignes"]}
        for c in conn.execute(
            """SELECT c.*, COALESCE((SELECT SUM(quantite) FROM consignes k
                      WHERE k.client_id = c.id), 0) AS consignes
               FROM clients c ORDER BY c.nom""")
    ]
    debut = (date.today() - timedelta(days=3)).isoformat()
    evenements = conn.execute(
        """SELECT * FROM evenements WHERE COALESCE(date_fin, date_debut) >= ?
           ORDER BY date_debut LIMIT 10""", (debut,)).fetchall()
    evt_du_jour = next((e["id"] for e in evenements
                        if e["date_debut"] <= today() <= (e["date_fin"] or e["date_debut"])), "")
    return render_template(
        "caisse.html", produits=produits, clients=clients, evenements=evenements,
        evt_du_jour=evt_du_jour, consigne_montant=to_float(conf.get("consigne_montant"), 1),
        form=request.form, lot_preselect=to_int(request.args.get("lot_id")),
        client_preselect=to_int(request.args.get("client_id")),
    )


def encaisser(conn, conf, form, hors_ligne=False, avertissements=None):
    """Crée un ticket. Hors ligne, la vente a déjà eu lieu : on l'enregistre même si le stock
    ou le bon d'achat posent problème, en le signalant dans `avertissements`."""
    erreurs = []
    avertissements = avertissements if avertissements is not None else []
    try:
        panier = json.loads(form.get("panier") or "[]")
    except ValueError:
        panier = []
    lignes = []
    for item in panier:
        lot_id, qte = to_int(item.get("lot_id")), to_int(item.get("quantite"))
        prix = round(to_float(item.get("prix"), -1), 2)
        if qte > 0:
            lignes.append((lot_id, qte, prix))
    if not lignes:
        erreurs.append("Le panier est vide.")

    demande = {}
    for lot_id, qte, prix in lignes:
        demande[lot_id] = demande.get(lot_id, 0) + qte
        if prix < 0:
            erreurs.append("Un prix est manquant ou négatif.")
    for lot_id, qte in demande.items():
        lot = lots_avec_stock("WHERE l.id = ?", (lot_id,))
        if not lot:
            erreurs.append("Un produit du panier n'existe plus.")
        elif lot[0]["statut"] not in ("embouteille", "epuise") or qte > stock_lot(lot[0]):
            message = (f"Stock insuffisant pour {lot[0]['recette_nom']} "
                       f"({lot[0]['numero']}) : {stock_lot(lot[0])} disponible(s).")
            (avertissements if hors_ligne else erreurs).append(message)

    client_id = to_int(form.get("client_id")) or None
    client = None
    if client_id:
        client = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not client:
            client_id = None
    client_nom = client["nom"] if client else (form.get("client_nom", "").strip()
                                               or "Client de passage")
    jour = parse_date(form.get("date_vente")) or today()
    canal = "revendeur" if form.get("canal") == "revendeur" else "direct"
    mode = form.get("mode_paiement") if form.get("mode_paiement") in MODES_PAIEMENT else "especes"
    evenement_id = to_int(form.get("evenement_id")) or None

    sous_total = round(sum(q * p for _, q, p in lignes), 2)
    bon = None
    if form.get("bon_code", "").strip():
        bon, err = verifier_bon(conn, form["bon_code"], client_id, jour)
        if err and hors_ligne:
            avertissements.append(f"Bon d'achat non appliqué : {err}")
        elif err:
            erreurs.append(err)
    remise = round(min(bon["montant"], sous_total), 2) if bon else 0.0

    montant_consigne = to_float(conf.get("consigne_montant"), 1)
    sorties = max(to_int(form.get("consigne_btl")), 0)
    retours = max(to_int(form.get("consigne_retour")), 0)
    consigne = round((sorties - retours) * montant_consigne, 2)
    if (sorties or retours) and not client_id and client_nom == "Client de passage" \
            and not hors_ligne:
        erreurs.append("Pour une consigne, indiquez le client (pour suivre ses bouteilles).")
    if erreurs:
        return None, erreurs

    cur = conn.execute(
        """INSERT INTO tickets (numero, date_vente, client_id, client_nom, canal, mode_paiement,
           evenement_id, sous_total, remise, consigne, total, client_adresse, notes, created_at,
           uuid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (database.prochain_numero(conn, "tickets", "numero", "T", jour[:4], 4), jour, client_id,
         client_nom, canal, mode, evenement_id, sous_total, remise, consigne,
         round(sous_total - remise + consigne, 2), client["adresse"] if client else None,
         form.get("notes", "").strip(), datetime.now().isoformat(timespec="seconds"),
         form.get("uuid") or None),
    )
    ticket_id = cur.lastrowid
    for lot_id, qte, prix in lignes:
        conn.execute(
            "INSERT INTO ventes (ticket_id, date_vente, client, lot_id, quantite,"
            " prix_unitaire_ttc, canal) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, jour, client_nom, lot_id, qte, prix, canal),
        )
    for lot_id in demande:
        maj_statut_epuise(conn, lot_id)
    if bon:
        conn.execute("UPDATE bons SET ticket_id = ? WHERE id = ?", (ticket_id, bon["id"]))
    for qte, note in ((sorties, None), (-retours, "Rapportée(s) en caisse")):
        if qte:
            conn.execute(
                "INSERT INTO consignes (client_id, client_nom, date_mouvement, quantite,"
                " montant_unitaire, ticket_id, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (client_id, client_nom, jour, qte, montant_consigne, ticket_id, note),
            )
    return ticket_id, []


@app.route("/api/synchro", methods=["POST"])
def api_synchro():
    """Reçoit les ventes faites hors ligne (au marché sans réseau) et les enregistre."""
    conn = get_db()
    conf = settings()
    donnees = request.get_json(silent=True) or {}
    resultats = []
    for vente in donnees.get("ventes", [])[:200]:
        uuid = str(vente.get("uuid", ""))[:64]
        if not uuid:
            continue
        deja = conn.execute("SELECT id, numero FROM tickets WHERE uuid = ?", (uuid,)).fetchone()
        if deja:  # déjà reçue (envoi répété après une coupure)
            resultats.append({"uuid": uuid, "ok": True, "numero": deja["numero"],
                              "url": url_for("ticket_detail", ticket_id=deja["id"])})
            continue
        champs = {k: ("" if v is None else str(v)) for k, v in vente.items() if k != "panier"}
        champs["panier"] = json.dumps(vente.get("panier") or [])
        champs["uuid"] = uuid
        avertissements = []
        ticket_id, erreurs = encaisser(conn, conf, champs, hors_ligne=True,
                                       avertissements=avertissements)
        if erreurs:
            conn.rollback()
            resultats.append({"uuid": uuid, "ok": False, "erreurs": erreurs})
            continue
        conn.commit()
        numero = conn.execute("SELECT numero FROM tickets WHERE id = ?", (ticket_id,)).fetchone()[0]
        resultats.append({"uuid": uuid, "ok": True, "numero": numero,
                          "url": url_for("ticket_detail", ticket_id=ticket_id),
                          "avertissements": avertissements})
    return jsonify({"ok": True, "resultats": resultats})


@app.route("/api/bon")
def api_bon():
    """Vérification d'un code de bon d'achat depuis la caisse."""
    bon, err = verifier_bon(get_db(), request.args.get("code", ""),
                            to_int(request.args.get("client_id")) or None, today())
    if err:
        return jsonify({"ok": False, "message": err})
    return jsonify({"ok": True, "montant": bon["montant"],
                    "message": f"Bon de {euro(bon['montant'])} valable"
                               + (f" ({bon['beneficiaire']})" if bon["beneficiaire"] else "")})


# --------------------------------------------------------------------------
# Tickets et factures
# --------------------------------------------------------------------------

@app.route("/tickets/<int:ticket_id>")
def ticket_detail(ticket_id):
    conn = get_db()
    ticket = get_or_404("tickets", ticket_id)
    client = (conn.execute("SELECT * FROM clients WHERE id = ?", (ticket["client_id"],)).fetchone()
              if ticket["client_id"] else None)
    evenement = (conn.execute("SELECT * FROM evenements WHERE id = ?",
                              (ticket["evenement_id"],)).fetchone()
                 if ticket["evenement_id"] else None)
    return render_template(
        "ticket.html", ticket=ticket, lignes=lignes_ticket(conn, ticket_id), client=client,
        evenement=evenement, bon=bon_du_ticket(conn, ticket_id), nouveau=request.args.get("nouveau"),
        smtp_ok=smtp_configure(settings()), conf=settings(),
    )


def _pdf(contenu, nom):
    disposition = "attachment" if request.args.get("telecharger") else "inline"
    return Response(contenu, mimetype="application/pdf",
                    headers={"Content-Disposition": f'{disposition}; filename="{nom}"'})


@app.route("/tickets/<int:ticket_id>/ticket.pdf")
def ticket_pdf_vue(ticket_id):
    conn = get_db()
    ticket = get_or_404("tickets", ticket_id)
    return _pdf(ticket_pdf(ticket, lignes_ticket(conn, ticket_id), settings(),
                           bon_du_ticket(conn, ticket_id)), f"Ticket-{ticket['numero']}.pdf")


@app.route("/tickets/<int:ticket_id>/facture.pdf")
def facture_pdf_vue(ticket_id):
    conn = get_db()
    ticket = get_or_404("tickets", ticket_id)
    if not ticket["facture_numero"]:
        abort(404)
    return _pdf(facture_pdf(ticket, lignes_ticket(conn, ticket_id), settings(),
                            bon_du_ticket(conn, ticket_id)),
                f"Facture-{ticket['facture_numero']}.pdf")


@app.route("/tickets/<int:ticket_id>/facture", methods=["POST"])
def facture_creer(ticket_id):
    conn = get_db()
    ticket = get_or_404("tickets", ticket_id)
    if ticket["facture_numero"]:
        flash("Ce ticket a déjà une facture.", "info")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    nom = request.form.get("client_nom", "").strip() or ticket["client_nom"]
    adresse = request.form.get("client_adresse", "").strip() or ticket["client_adresse"]
    jour = today()
    numero = database.prochain_numero(conn, "tickets", "facture_numero", "F", jour[:4], 4)
    conn.execute(
        "UPDATE tickets SET facture_numero = ?, facture_date = ?, client_nom = ?,"
        " client_adresse = ? WHERE id = ?",
        (numero, jour, nom, adresse, ticket_id),
    )
    if ticket["client_id"] and adresse and request.form.get("memoriser"):
        conn.execute("UPDATE clients SET adresse = ? WHERE id = ? AND COALESCE(adresse, '') = ''",
                     (adresse, ticket["client_id"]))
    conn.commit()
    flash(f"Facture {numero} établie. Une facture ne peut plus être modifiée ni supprimée.",
          "succes")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.route("/tickets/<int:ticket_id>/envoyer", methods=["POST"])
def ticket_envoyer(ticket_id):
    conn = get_db()
    conf = settings()
    ticket = get_or_404("tickets", ticket_id)
    doc = request.form.get("document")
    email = request.form.get("email", "").strip()
    lignes, bon = lignes_ticket(conn, ticket_id), bon_du_ticket(conn, ticket_id)
    nom_prod = conf.get("producteur_nom") or "Maison Corsaire"
    if doc == "facture" and ticket["facture_numero"]:
        piece = (f"Facture-{ticket['facture_numero']}.pdf",
                 facture_pdf(ticket, lignes, conf, bon), "application/pdf")
        sujet = f"Votre facture {ticket['facture_numero']} – {nom_prod}"
        quoi = "votre facture"
    else:
        piece = (f"Ticket-{ticket['numero']}.pdf", ticket_pdf(ticket, lignes, conf, bon),
                 "application/pdf")
        sujet = f"Votre ticket de caisse – {nom_prod}"
        quoi = "votre ticket de caisse"
    texte = (f"Bonjour,\n\nMerci pour votre achat du {date.fromisoformat(ticket['date_vente']):%d/%m/%Y}."
             f"\nVous trouverez {quoi} en pièce jointe.\n\nÀ bientôt,\n{nom_prod}\n"
             f"{conf.get('producteur_telephone') or ''}\n\n"
             "L'abus d'alcool est dangereux pour la santé, à consommer avec modération.")
    try:
        envoyer(conf, email, sujet, texte, [piece])
        flash(f"{quoi.capitalize()} envoyé(e) à {email}.", "succes")
    except Exception as exc:  # noqa: BLE001
        flash(f"Envoi impossible : {exc}", "erreur")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.route("/tickets/<int:ticket_id>/supprimer", methods=["POST"])
def ticket_supprimer(ticket_id):
    conn = get_db()
    ticket = get_or_404("tickets", ticket_id)
    if ticket["facture_numero"]:
        flash("Ce ticket a une facture : il ne peut pas être supprimé "
              "(obligation de conservation).", "erreur")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    lots = [r["lot_id"] for r in conn.execute(
        "SELECT DISTINCT lot_id FROM ventes WHERE ticket_id = ?", (ticket_id,))]
    conn.execute("UPDATE bons SET ticket_id = NULL WHERE ticket_id = ?", (ticket_id,))
    conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    for lot_id in lots:
        maj_statut_epuise(conn, lot_id, reouvrir=True)
    conn.commit()
    flash(f"Ticket {ticket['numero']} supprimé : bouteilles remises en stock.", "succes")
    return redirection_sure(request.form.get("retour"), url_for("ventes"))


# --------------------------------------------------------------------------
# Historique des ventes
# --------------------------------------------------------------------------

@app.route("/ventes")
def ventes():
    conn = get_db()
    conf = settings()
    mois_dispo = [r[0] for r in conn.execute(
        "SELECT DISTINCT substr(date_vente, 1, 7) FROM tickets ORDER BY 1 DESC")]
    mois = request.args.get("mois", "")
    if mois not in mois_dispo:
        mois = "tout"
    recherche = request.args.get("q", "").strip()
    sql = """SELECT t.*, (SELECT SUM(quantite) FROM ventes v WHERE v.ticket_id = t.id) AS btl,
                    (SELECT group_concat(l.recette_nom, ', ') FROM ventes v JOIN lots l
                     ON l.id = v.lot_id WHERE v.ticket_id = t.id) AS produits
             FROM tickets t WHERE 1 = 1"""
    params = []
    if mois != "tout":
        sql += " AND t.date_vente LIKE ?"
        params.append(mois + "%")
    if recherche:
        sql += " AND (t.client_nom LIKE ? OR t.numero LIKE ? OR t.facture_numero LIKE ?)"
        params += [f"%{recherche}%"] * 3
    tickets = conn.execute(sql + " ORDER BY t.date_vente DESC, t.id DESC", params).fetchall()

    ids = [t["id"] for t in tickets]
    couts = couts_par_lot(conn, conf)
    tva = taux_tva(conf)
    ca = sum(t["sous_total"] - t["remise"] for t in tickets)
    cout_total = 0.0
    if ids:
        marques = ",".join("?" * len(ids))
        for v in conn.execute(f"SELECT lot_id, quantite FROM ventes WHERE ticket_id IN ({marques})",
                              ids):
            cout_total += v["quantite"] * couts.get(v["lot_id"], 0)
    return render_template(
        "ventes.html", tickets=tickets, mois=mois, mois_dispo=mois_dispo, mois_label=mois_label,
        ca=ca, marge=marge_pct(ca / (1 + tva), cout_total) if ca else None,
        bouteilles=sum(t["btl"] or 0 for t in tickets), recherche=recherche,
    )
