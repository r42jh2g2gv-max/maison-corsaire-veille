"""Clientèle : fiches clients, bons d'achat, consignes et envoi de nouveautés."""
from datetime import date, datetime, timedelta
from urllib.parse import quote

from flask import Response, abort, flash, redirect, render_template, request, url_for

from calculs import to_float
from db import code_bon
from emails import envoyer, smtp_configure
from noyau import (TYPES_CLIENTS, app, euro, get_db, get_or_404, parse_date,
                   redirection_sure, settings, to_int, today)
from pdfs import bon_pdf

STATS_CLIENTS = """
SELECT c.*,
  COALESCE((SELECT SUM(v.quantite) FROM ventes v JOIN tickets t ON t.id = v.ticket_id
            WHERE t.client_id = c.id), 0) AS bouteilles,
  COALESCE((SELECT SUM(t.sous_total - t.remise) FROM tickets t WHERE t.client_id = c.id), 0)
    AS depense,
  (SELECT MAX(t.date_vente) FROM tickets t WHERE t.client_id = c.id) AS dernier_achat,
  COALESCE((SELECT SUM(k.quantite) FROM consignes k WHERE k.client_id = c.id), 0) AS consignes,
  (SELECT COUNT(*) FROM bons b WHERE b.client_id = c.id AND b.ticket_id IS NULL
     AND (b.date_expiration IS NULL OR b.date_expiration >= date('now', 'localtime'))) AS bons_actifs
FROM clients c
"""


def lire_client(form):
    return {
        "nom": form.get("nom", "").strip(),
        "type": form.get("type") if form.get("type") in TYPES_CLIENTS else "particulier",
        "email": form.get("email", "").strip().lower(),
        "telephone": form.get("telephone", "").strip(),
        "adresse": form.get("adresse", "").strip(),
        "notes": form.get("notes", "").strip(),
        "accepte_infos": 1 if form.get("accepte_infos") else 0,
        "prix_revendeur_ht": to_float(form.get("prix_revendeur_ht"), None),
    }


@app.route("/clients")
def clients():
    conn = get_db()
    type_ = request.args.get("type", "")
    q = request.args.get("q", "").strip()
    sql, params = STATS_CLIENTS + " WHERE 1 = 1", []
    if type_ in TYPES_CLIENTS:
        sql += " AND c.type = ?"
        params.append(type_)
    else:
        type_ = ""
    if q:
        sql += " AND (c.nom LIKE ? OR c.email LIKE ? OR c.telephone LIKE ?)"
        params += [f"%{q}%"] * 3
    rows = conn.execute(sql + " ORDER BY dernier_achat IS NULL, dernier_achat DESC, c.nom",
                        params).fetchall()
    compte = {k: 0 for k in TYPES_CLIENTS}
    for r in conn.execute("SELECT type, COUNT(*) n FROM clients GROUP BY type"):
        compte[r["type"]] = r["n"]
    abonnes = conn.execute(
        "SELECT COUNT(*) FROM clients WHERE accepte_infos = 1 AND COALESCE(email, '') != ''"
    ).fetchone()[0]
    return render_template("clients.html", clients=rows, type_=type_, q=q, compte=compte,
                           abonnes=abonnes)


@app.route("/clients/nouveau", methods=["GET", "POST"])
def client_nouveau():
    if request.method == "POST":
        data = lire_client(request.form)
        if not data["nom"]:
            flash("Le nom du client est obligatoire.", "erreur")
            return render_template("client_form.html", client=data, nouveau=True)
        cur = get_db().execute(
            """INSERT INTO clients (nom, type, email, telephone, adresse, notes, accepte_infos,
               prix_revendeur_ht, created_at) VALUES (:nom, :type, :email, :telephone, :adresse,
               :notes, :accepte_infos, :prix_revendeur_ht, :created_at)""",
            {**data, "created_at": today()},
        )
        get_db().commit()
        flash(f"Client « {data['nom']} » ajouté.", "succes")
        return redirection_sure(request.form.get("retour"),
                                url_for("client_detail", client_id=cur.lastrowid))
    return render_template("client_form.html", client={"type": "particulier"}, nouveau=True)


@app.route("/clients/<int:client_id>/modifier", methods=["GET", "POST"])
def client_modifier(client_id):
    client = get_or_404("clients", client_id)
    if request.method == "POST":
        data = lire_client(request.form)
        if not data["nom"]:
            flash("Le nom du client est obligatoire.", "erreur")
            return render_template("client_form.html", client={**dict(client), **data},
                                   nouveau=False)
        get_db().execute(
            """UPDATE clients SET nom = :nom, type = :type, email = :email,
               telephone = :telephone, adresse = :adresse, notes = :notes,
               accepte_infos = :accepte_infos, prix_revendeur_ht = :prix_revendeur_ht
               WHERE id = :id""", {**data, "id": client_id})
        get_db().commit()
        flash("Fiche client mise à jour.", "succes")
        return redirect(url_for("client_detail", client_id=client_id))
    return render_template("client_form.html", client=client, nouveau=False)


@app.route("/clients/<int:client_id>")
def client_detail(client_id):
    conn = get_db()
    client = conn.execute(STATS_CLIENTS + " WHERE c.id = ?", (client_id,)).fetchone()
    if not client:
        abort(404)
    tickets = conn.execute(
        """SELECT t.*, (SELECT SUM(quantite) FROM ventes v WHERE v.ticket_id = t.id) AS btl,
                  (SELECT group_concat(l.recette_nom, ', ') FROM ventes v JOIN lots l
                   ON l.id = v.lot_id WHERE v.ticket_id = t.id) AS produits
           FROM tickets t WHERE t.client_id = ? ORDER BY t.date_vente DESC, t.id DESC""",
        (client_id,)).fetchall()
    bons = conn.execute("SELECT * FROM bons WHERE client_id = ? ORDER BY date_emission DESC",
                        (client_id,)).fetchall()
    consignes = conn.execute(
        "SELECT * FROM consignes WHERE client_id = ? ORDER BY date_mouvement DESC, id DESC",
        (client_id,)).fetchall()
    conf = settings()
    return render_template(
        "client_detail.html", client=client, tickets=tickets, bons=bons, consignes=consignes,
        consigne_montant=to_float(conf.get("consigne_montant"), 1),
        expiration_defaut=(date.today() + timedelta(days=365)).isoformat(),
        smtp_ok=smtp_configure(conf),
    )


@app.route("/clients/<int:client_id>/supprimer", methods=["POST"])
def client_supprimer(client_id):
    conn = get_db()
    client = get_or_404("clients", client_id)
    # Les tickets et factures sont conservés (obligation comptable) avec le nom du client.
    conn.execute("DELETE FROM bons WHERE client_id = ? AND ticket_id IS NULL", (client_id,))
    conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    flash(f"Client « {client['nom']} » supprimé. Ses tickets et factures sont conservés "
          "pour la comptabilité.", "succes")
    return redirect(url_for("clients"))


@app.route("/clients/<int:client_id>/consigne", methods=["POST"])
def client_consigne(client_id):
    conn = get_db()
    client = get_or_404("clients", client_id)
    conf = settings()
    qte = max(to_int(request.form.get("quantite")), 0)
    sens = request.form.get("sens")
    if not qte:
        flash("Indiquez un nombre de bouteilles.", "erreur")
        return redirect(url_for("client_detail", client_id=client_id) + "#consignes")
    signe = -1 if sens == "retour" else 1
    montant = to_float(conf.get("consigne_montant"), 1)
    conn.execute(
        "INSERT INTO consignes (client_id, client_nom, date_mouvement, quantite, montant_unitaire,"
        " notes) VALUES (?, ?, ?, ?, ?, ?)",
        (client_id, client["nom"], parse_date(request.form.get("date")) or today(),
         signe * qte, montant, request.form.get("notes", "").strip() or None),
    )
    if sens == "retour" and request.form.get("remettre_en_stock"):
        mat = conn.execute(
            "SELECT id, nom FROM materiaux WHERE type = 'bouteille' ORDER BY id LIMIT 1").fetchone()
        if mat:
            conn.execute("UPDATE materiaux SET stock = stock + ? WHERE id = ?", (qte, mat["id"]))
            flash(f"{qte} bouteille(s) remise(s) dans le stock « {mat['nom']} ».", "info")
    conn.commit()
    if sens == "retour":
        flash(f"Retour de {qte} bouteille(s) : rendez {euro(qte * montant)} au client.", "succes")
    else:
        flash(f"{qte} bouteille(s) consignée(s) : {euro(qte * montant)} encaissé(s).", "succes")
    return redirect(url_for("client_detail", client_id=client_id) + "#consignes")


# --------------------------------------------------------------------------
# Bons d'achat
# --------------------------------------------------------------------------

def statut_bon(bon):
    if bon["ticket_id"]:
        return "utilise"
    if bon["date_expiration"] and bon["date_expiration"] < today():
        return "expire"
    return "actif"


app.jinja_env.globals["statut_bon"] = statut_bon


@app.route("/bons")
def bons():
    conn = get_db()
    rows = conn.execute(
        """SELECT b.*, t.numero AS ticket_numero FROM bons b
           LEFT JOIN tickets t ON t.id = b.ticket_id ORDER BY b.date_emission DESC, b.id DESC"""
    ).fetchall()
    clients = conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()
    return render_template(
        "bons.html", bons=rows, clients=clients,
        expiration_defaut=(date.today() + timedelta(days=365)).isoformat(),
        client_preselect=to_int(request.args.get("client_id")),
    )


@app.route("/bons", methods=["POST"])
def bon_creer():
    conn = get_db()
    montant = round(to_float(request.form.get("montant")), 2)
    client_id = to_int(request.form.get("client_id")) or None
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone() \
        if client_id else None
    beneficiaire = client["nom"] if client else request.form.get("beneficiaire", "").strip()
    if montant <= 0:
        flash("Le montant du bon doit être supérieur à zéro.", "erreur")
        return redirection_sure(request.form.get("retour"), url_for("bons"))
    code = code_bon()
    while conn.execute("SELECT 1 FROM bons WHERE code = ?", (code,)).fetchone():
        code = code_bon()
    conn.execute(
        "INSERT INTO bons (code, client_id, beneficiaire, montant, motif, date_emission,"
        " date_expiration) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (code, client["id"] if client else None, beneficiaire or None, montant,
         request.form.get("motif", "").strip() or None, today(),
         parse_date(request.form.get("date_expiration"))),
    )
    conn.commit()
    flash(f"Bon d'achat {code} de {euro(montant)} créé.", "succes")
    return redirection_sure(request.form.get("retour"), url_for("bons"))


@app.route("/bons/<int:bon_id>.pdf")
def bon_pdf_vue(bon_id):
    bon = get_or_404("bons", bon_id)
    disposition = "attachment" if request.args.get("telecharger") else "inline"
    return Response(bon_pdf(bon, settings()), mimetype="application/pdf",
                    headers={"Content-Disposition":
                             f'{disposition}; filename="Bon-achat-{bon["code"]}.pdf"'})


@app.route("/bons/<int:bon_id>/envoyer", methods=["POST"])
def bon_envoyer(bon_id):
    conn = get_db()
    conf = settings()
    bon = get_or_404("bons", bon_id)
    email = request.form.get("email", "").strip()
    nom_prod = conf.get("producteur_nom") or "Maison Corsaire"
    expiration = (f" Il est valable jusqu'au {date.fromisoformat(bon['date_expiration']):%d/%m/%Y}."
                  if bon["date_expiration"] else "")
    texte = (f"Bonjour{' ' + bon['beneficiaire'] if bon['beneficiaire'] else ''},\n\n"
             f"{nom_prod} vous offre un bon d'achat de {euro(bon['montant'])} "
             f"(code {bon['code']}).{expiration}\n"
             f"{bon['motif'] + chr(10) if bon['motif'] else ''}"
             "Présentez-le (imprimé ou sur votre téléphone) lors de votre prochain achat.\n\n"
             f"À bientôt,\n{nom_prod}\n\n"
             "L'abus d'alcool est dangereux pour la santé, à consommer avec modération.")
    try:
        envoyer(conf, email, f"Un bon d'achat de {euro(bon['montant'])} vous attend – {nom_prod}",
                texte, [(f"Bon-achat-{bon['code']}.pdf", bon_pdf(bon, conf), "application/pdf")])
        conn.execute("UPDATE bons SET envoye_le = ? WHERE id = ?", (today(), bon_id))
        conn.commit()
        flash(f"Bon d'achat envoyé à {email}.", "succes")
    except Exception as exc:  # noqa: BLE001
        flash(f"Envoi impossible : {exc}", "erreur")
    return redirection_sure(request.form.get("retour"), url_for("bons"))


@app.route("/bons/<int:bon_id>/supprimer", methods=["POST"])
def bon_supprimer(bon_id):
    conn = get_db()
    bon = get_or_404("bons", bon_id)
    if bon["ticket_id"]:
        flash("Ce bon a été utilisé : il est conservé dans l'historique.", "erreur")
    else:
        conn.execute("DELETE FROM bons WHERE id = ?", (bon_id,))
        conn.commit()
        flash(f"Bon {bon['code']} annulé.", "succes")
    return redirection_sure(request.form.get("retour"), url_for("bons"))


# --------------------------------------------------------------------------
# Nouveautés : message aux clients qui l'ont accepté
# --------------------------------------------------------------------------

@app.route("/clients/message", methods=["GET", "POST"])
def clients_message():
    conn = get_db()
    conf = settings()
    abonnes = conn.execute(
        """SELECT * FROM clients WHERE accepte_infos = 1 AND COALESCE(email, '') != ''
           ORDER BY nom""").fetchall()
    nom_prod = conf.get("producteur_nom") or "Maison Corsaire"
    signature = (f"\n\nÀ bientôt,\n{nom_prod}\n\n"
                 "L'abus d'alcool est dangereux pour la santé, à consommer avec modération.\n"
                 "Vous recevez ce message car vous avez accepté d'être informé(e) de nos "
                 "nouveautés. Pour ne plus rien recevoir, répondez simplement « STOP ».")
    mailto = None
    if request.method == "POST":
        sujet = request.form.get("sujet", "").strip()
        corps = request.form.get("corps", "").strip()
        ids = {to_int(i) for i in request.form.getlist("destinataires")}
        dest = [c for c in abonnes if c["id"] in ids]
        if not sujet or not corps or not dest:
            flash("Indiquez un sujet, un message et au moins un destinataire.", "erreur")
        elif request.form.get("mode") == "smtp":
            envoyes, echecs = 0, []
            for c in dest:
                try:
                    envoyer(conf, c["email"], sujet, f"Bonjour {c['nom']},\n\n{corps}{signature}")
                    envoyes += 1
                except Exception as exc:  # noqa: BLE001
                    echecs.append(f"{c['nom']} ({exc})")
            if envoyes:
                conn.execute(
                    "INSERT INTO messages (date_envoi, sujet, corps, nb_destinataires, mode)"
                    " VALUES (?, ?, ?, ?, 'email')",
                    (datetime.now().isoformat(timespec="minutes"), sujet, corps, envoyes))
                conn.commit()
                flash(f"Message envoyé à {envoyes} client(s), chacun individuellement.", "succes")
            for e in echecs:
                flash(f"Échec : {e}", "erreur")
            if envoyes:
                return redirect(url_for("clients_message"))
        else:
            # Sans serveur d'envoi : on ouvre la messagerie du téléphone, destinataires en copie
            # cachée pour qu'ils ne voient pas les adresses des autres.
            mailto = ("mailto:?bcc=" + ",".join(quote(c["email"]) for c in dest)
                      + "&subject=" + quote(sujet) + "&body=" + quote(f"Bonjour,\n\n{corps}{signature}"))
            conn.execute(
                "INSERT INTO messages (date_envoi, sujet, corps, nb_destinataires, mode)"
                " VALUES (?, ?, ?, ?, 'messagerie')",
                (datetime.now().isoformat(timespec="minutes"), sujet, corps, len(dest)))
            conn.commit()
    historique = conn.execute("SELECT * FROM messages ORDER BY date_envoi DESC LIMIT 20").fetchall()
    return render_template(
        "clients_message.html", abonnes=abonnes, historique=historique, mailto=mailto,
        smtp_ok=smtp_configure(conf), form=request.form, signature=signature,
    )
