"""Bilan du mois en PDF : ventes, meilleurs rhums, marchés, avis, hygiène, plafonds.
Envoyé automatiquement par email au début du mois suivant (si l'envoi d'emails est configuré)."""
from datetime import date, timedelta
from io import BytesIO

from flask import Response, abort, flash, g, redirect, request, session, url_for
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from calculs import to_float
from noyau import MOIS_LONGS, app, couts_par_lot, get_db, set_setting, settings
from pdfs import GRIS, NUIT, OR, _decouper, _dessiner_logo, _euro, _logo


def bornes(ym):
    d = date.fromisoformat(ym + "-01")
    fin = (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return d, fin


def mois_precedent(ym, n=1):
    d = date.fromisoformat(ym + "-01")
    for _ in range(n):
        d = (d - timedelta(days=1)).replace(day=1)
    return d.strftime("%Y-%m")


def donnees_bilan(conn, conf, ym):
    from plafonds import etat_plafonds
    from rappels import ca_periode
    debut, fin = bornes(ym)
    d, f = debut.isoformat(), fin.isoformat()
    couts = couts_par_lot(conn, conf)
    ca = ca_periode(conn, debut, fin)
    ca_prec = ca_periode(conn, *bornes(mois_precedent(ym)))
    ca_an = ca_periode(conn, *bornes(mois_precedent(ym, 12)))
    ventes = conn.execute(
        """SELECT v.lot_id, v.quantite, v.prix_unitaire_ttc, v.canal, l.recette_nom
           FROM ventes v JOIN lots l ON l.id = v.lot_id WHERE v.date_vente BETWEEN ? AND ?""",
        (d, f)).fetchall()
    btl = sum(v["quantite"] for v in ventes)
    marge = sum(v["quantite"] * (v["prix_unitaire_ttc"] - couts.get(v["lot_id"], 0)) for v in ventes)
    rhums = {}
    for v in ventes:
        r = rhums.setdefault(v["recette_nom"], {"nom": v["recette_nom"], "btl": 0, "ca": 0})
        r["btl"] += v["quantite"]
        r["ca"] += v["quantite"] * v["prix_unitaire_ttc"]
    top = sorted(rhums.values(), key=lambda r: -r["ca"])[:5]
    tickets = conn.execute("SELECT COUNT(*), COALESCE(SUM(sous_total - remise), 0) FROM tickets"
                           " WHERE date_vente BETWEEN ? AND ?", (d, f)).fetchone()
    revendeurs = sum(v["quantite"] * v["prix_unitaire_ttc"] for v in ventes if v["canal"] == "revendeur")
    marches = []
    for e in conn.execute("SELECT * FROM evenements WHERE date_debut BETWEEN ? AND ? ORDER BY date_debut",
                          (d, f)):
        lignes = conn.execute("""SELECT v.lot_id, v.quantite FROM ventes v JOIN tickets t ON t.id = v.ticket_id
                                 WHERE t.evenement_id = ?""", (e["id"],)).fetchall()
        ca_e = conn.execute("SELECT COALESCE(SUM(sous_total - remise), 0) FROM tickets WHERE evenement_id = ?",
                            (e["id"],)).fetchone()[0]
        cout = sum(l["quantite"] * couts.get(l["lot_id"], 0) for l in lignes)
        marches.append({"nom": e["nom"], "date": e["date_debut"], "btl": sum(l["quantite"] for l in lignes),
                        "ca": ca_e, "benefice": ca_e - cout - e["cout_place"]})
    achats = conn.execute("SELECT COALESCE(SUM(montant_total), 0) FROM achats WHERE date_achat BETWEEN ? AND ?",
                          (d, f)).fetchone()[0]
    taux = (to_float(conf.get("urssaf_taux")) + to_float(conf.get("cfp_taux"))) / 100
    avis = conn.execute("SELECT COUNT(*), AVG(note) FROM avis WHERE substr(created_at, 1, 10) BETWEEN ? AND ?",
                        (d, f)).fetchone()
    conseils = [r[0] for r in conn.execute(
        "SELECT conseil FROM avis WHERE conseil IS NOT NULL AND substr(created_at, 1, 10) BETWEEN ? AND ?"
        " ORDER BY created_at DESC LIMIT 3", (d, f))]
    hyg = conn.execute("SELECT COUNT(*), SUM(resultat = 'non_conforme') FROM hygiene_releves"
                       " WHERE date_releve BETWEEN ? AND ?", (d, f)).fetchone()
    attente = conn.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM tickets WHERE paye = 0").fetchone()
    lots = conn.execute("SELECT COUNT(*), COALESCE(SUM(nb_bouteilles), 0) FROM lots"
                        " WHERE date_embouteillage BETWEEN ? AND ?", (d, f)).fetchone()
    evolution = []
    for k in range(5, -1, -1):
        m = mois_precedent(ym, k)
        evolution.append((m, ca_periode(conn, *bornes(m))))
    plafonds = etat_plafonds(conn, conf, min(fin, date.today()))
    return {"ym": ym, "titre": f"{MOIS_LONGS[debut.month - 1].capitalize()} {debut.year}",
            "ca": ca, "ca_prec": ca_prec, "ca_an": ca_an, "btl": btl, "marge": marge,
            "tickets": tickets[0], "panier": tickets[1] / tickets[0] if tickets[0] else 0,
            "revendeurs": revendeurs, "top": top, "marches": marches, "achats": achats,
            "cotisations": ca * taux, "avis_nb": avis[0], "avis_moy": avis[1], "conseils": conseils,
            "hyg_nb": hyg[0], "hyg_nc": hyg[1] or 0, "attente": attente, "lots": lots,
            "evolution": evolution, "plafonds": plafonds["jauges"]}


def _variation(a, b):
    if not b:
        return ""
    v = (a - b) / b * 100
    return f"{'+' if v >= 0 else ''}{v:.0f} %"


def bilan_pdf(b, conf):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    L, H = A4
    m = 16 * mm
    c.setTitle(f"Bilan {b['titre']}")
    y = H - m
    logo = _logo("symbole")
    if logo:
        _dessiner_logo(c, logo, L - m - 8 * mm, y - 10 * mm, 14 * mm, centre=True)
    c.setFillColor(OR)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(m, y - 2 * mm, (conf.get("producteur_nom") or "Maison Corsaire").upper() + " · BILAN DU MOIS")
    c.setFillColor(NUIT)
    c.setFont("Times-Bold", 24)
    c.drawString(m, y - 12 * mm, b["titre"])
    y -= 22 * mm

    # Chiffres clés : 4 tuiles
    tuiles = [("Chiffre d'affaires", _euro(b["ca"]),
               " · ".join(x for x in (f"{_variation(b['ca'], b['ca_prec'])} vs mois préc." if b["ca_prec"] else "",
                                      f"{_variation(b['ca'], b['ca_an'])} sur un an" if b["ca_an"] else "") if x)),
              ("Bouteilles vendues", str(b["btl"]), f"{b['tickets']} ticket(s) · panier {_euro(b['panier'])}"),
              ("Marge sur ventes", _euro(b["marge"]), "prix de vente − coût de revient"),
              ("À déclarer (estim.)", _euro(b["cotisations"]), f"achats du mois : {_euro(b['achats'])}")]
    w = (L - 2 * m - 3 * 4 * mm) / 4
    for i, (titre, valeur, sous) in enumerate(tuiles):
        x = m + i * (w + 4 * mm)
        c.setFillColorRGB(0.97, 0.95, 0.91)
        c.roundRect(x, y - 22 * mm, w, 22 * mm, 3 * mm, fill=1, stroke=0)
        c.setFillColor(GRIS)
        c.setFont("Helvetica", 7.5)
        c.drawString(x + 3 * mm, y - 5.5 * mm, titre)
        c.setFillColor(NUIT)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(x + 3 * mm, y - 13 * mm, valeur)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(GRIS)
        for k, ligne in enumerate(_decouper(c, sous, "Helvetica", 6.5, w - 6 * mm)[:2]):
            c.drawString(x + 3 * mm, y - 17.5 * mm - k * 2.8 * mm, ligne)
    y -= 31 * mm

    def titre(t):
        nonlocal y
        c.setFillColor(OR)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m, y, t.upper())
        c.setStrokeColor(OR)
        c.setLineWidth(0.6)
        c.line(m, y - 2 * mm, L - m, y - 2 * mm)
        y -= 7.5 * mm

    def ligne(gauche, droite="", milieu="", gras=False):
        nonlocal y
        c.setFillColor(NUIT)
        c.setFont("Helvetica-Bold" if gras else "Helvetica", 9)
        c.drawString(m, y, gauche[:70])
        if milieu:
            c.setFillColor(GRIS)
            c.drawRightString(L - m - 45 * mm, y, milieu)
            c.setFillColor(NUIT)
        c.drawRightString(L - m, y, droite)
        y -= 5.2 * mm

    titre("Évolution du chiffre d'affaires (6 mois)")
    maxi = max((v for _, v in b["evolution"]), default=0) or 1
    largeur_barre = L - 2 * m - 60 * mm
    for ym, v in b["evolution"]:
        d = date.fromisoformat(ym + "-01")
        c.setFillColor(NUIT)
        c.setFont("Helvetica-Bold" if ym == b["ym"] else "Helvetica", 8.5)
        c.drawString(m, y, f"{MOIS_LONGS[d.month - 1].capitalize()} {d.year}")
        c.setFillColor(OR if ym == b["ym"] else colors_gris())
        c.rect(m + 32 * mm, y - 0.6 * mm, max(largeur_barre * v / maxi, 0.5), 3.4 * mm, fill=1, stroke=0)
        c.setFillColor(NUIT)
        c.drawRightString(L - m, y, _euro(v))
        y -= 5 * mm
    y -= 3 * mm

    titre("Meilleurs rhums du mois")
    if b["top"]:
        for r in b["top"]:
            ligne(r["nom"], _euro(r["ca"]), f"{r['btl']} btl")
    else:
        ligne("Aucune vente ce mois-ci.")
    if b["revendeurs"]:
        ligne("dont ventes aux revendeurs", _euro(b["revendeurs"]))
    y -= 3 * mm

    if b["marches"]:
        titre("Marchés et événements")
        for e in b["marches"]:
            ligne(f"{e['nom']} ({date.fromisoformat(e['date']):%d/%m})",
                  f"bénéfice {_euro(e['benefice'])}", f"{e['btl']} btl · {_euro(e['ca'])}")
        y -= 3 * mm

    titre("En bref")
    if b["lots"][0]:
        ligne(f"Lots mis en bouteille : {b['lots'][0]}", f"{b['lots'][1]} bouteilles")
    avis = (f"{b['avis_nb']} avis client(s)" + (f" · moyenne {b['avis_moy']:.1f}/5" if b["avis_moy"] else "")
            if b["avis_nb"] else "Aucun nouvel avis client")
    ligne(avis)
    for conseil in b["conseils"]:
        ligne(f"   « {conseil[:80]} »")
    ligne(f"Cahier d'hygiène : {b['hyg_nb']} enregistrement(s)"
          + (f", dont {b['hyg_nc']} non conforme(s)" if b["hyg_nc"] else ""))
    if b["attente"][0]:
        ligne(f"Factures en attente de paiement : {b['attente'][0]}", _euro(b["attente"][1]))
    for j in b["plafonds"]:
        ligne(f"{j['titre']} : {j['pct']:.0f} % atteint", f"{_euro(j['ca'])} / {_euro(j['plafond'])}")

    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS)
    c.drawCentredString(L / 2, 10 * mm, "Chiffre d'affaires encaissé (date de paiement), avoirs déduits. "
                        "Cotisations estimées avec les taux des Paramètres.")
    c.showPage()
    c.save()
    return buf.getvalue()


def colors_gris():
    from reportlab.lib import colors
    return colors.HexColor("#c9ccd3")


@app.route("/chiffres/bilan/<ym>.pdf")
def bilan_mensuel(ym):
    try:
        bornes(ym)
    except ValueError:
        abort(404)
    pdf = bilan_pdf(donnees_bilan(get_db(), settings(), ym), settings())
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="Bilan-{ym}.pdf"'})


def envoyer_bilan(conf, ym):
    from emails import envoyer
    b = donnees_bilan(get_db(), conf, ym)
    envoyer(conf, conf.get("producteur_email") or conf.get("smtp_expediteur") or conf.get("smtp_user"),
            f"Bilan de {b['titre'].lower()} – {conf.get('producteur_nom') or 'Maison Corsaire'}",
            f"Bonjour,\n\nVoici le bilan de {b['titre'].lower()} : {_euro(b['ca'])} de chiffre d'affaires, "
            f"{b['btl']} bouteille(s) vendue(s).\n\nLe détail est dans le PDF joint.\n",
            [(f"Bilan-{ym}.pdf", bilan_pdf(b, conf), "application/pdf")])


@app.route("/chiffres/bilan/<ym>/envoyer", methods=["POST"])
def bilan_envoyer(ym):
    try:
        envoyer_bilan(settings(), ym)
        flash("Bilan envoyé par email.", "succes")
    except Exception as e:  # noqa: BLE001 — message clair pour l'utilisateur
        flash(f"Envoi impossible : {e}", "erreur")
    return redirect(url_for("chiffres") + "#bilans")


@app.before_request
def bilan_automatique():
    """Le 1er passage du mois, le bilan du mois écoulé part par email (une seule fois)."""
    if g.get("bilan_verifie") or not session.get("user_id") or request.endpoint in (None, "static"):
        return
    g.bilan_verifie = True
    conf = settings()
    if conf.get("bilan_email_auto", "1") != "1":
        return
    from emails import smtp_configure
    precedent = mois_precedent(date.today().strftime("%Y-%m"))
    if conf.get("bilan_envoye") == precedent or not smtp_configure(conf):
        return
    set_setting("bilan_envoye", precedent)  # noté d'abord : jamais deux envois
    get_db().commit()
    try:
        envoyer_bilan(conf, precedent)
    except Exception:  # noqa: BLE001 — un échec d'email ne bloque jamais l'application
        pass
