"""Affiche de prix pour le stand : rhums en stock, prix, coffrets, QR code « Votre avis »."""
import os
from io import BytesIO

from flask import Response, request, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from calculs import to_float
from noyau import app, get_db, lots_avec_stock, settings, stock_lot
from pdfs import GRIS, MODERATION, NUIT, OR, _decouper, _dessiner_logo, _euro, _logo

CREME = colors.HexColor("#fbf7ef")


def carte_des_prix(conn):
    """Un produit par recette et contenance en stock, au prix de vente le plus récent."""
    produits = {}
    for l in lots_avec_stock("WHERE l.statut = 'embouteille' AND COALESCE(l.essai, 0) = 0"
                             " ORDER BY l.date_embouteillage"):
        if stock_lot(l) <= 0 or not l["prix_vente_ttc"]:
            continue
        cle = (l["recette_nom"], l["volume_cl"])
        produits[cle] = {"nom": l["recette_nom"], "volume": l["volume_cl"], "degre": l["degre"],
                         "prix": l["prix_vente_ttc"], "recette_id": l["recette_id"]}
    notes = {r["id"]: r["notes_degustation"] for r in
             conn.execute("SELECT id, notes_degustation FROM recettes")}
    liste = sorted(produits.values(), key=lambda p: (p["nom"], p["volume"]))
    for p in liste:
        p["notes"] = notes.get(p["recette_id"])
    from vues_coffrets import disponibles
    coffrets = [c for c in conn.execute("SELECT * FROM coffrets WHERE actif = 1 ORDER BY prix_ttc")
                if disponibles(conn, c["id"]) > 0]
    return liste, coffrets


@app.route("/affiche-prix.pdf")
def affiche_prix():
    conn = get_db()
    conf = settings()
    produits, coffrets = carte_des_prix(conn)
    taille = A3 if request.args.get("format") == "A3" else A4
    avec_notes = request.args.get("notes", "1") == "1"
    L, H = taille
    k = L / A4[0]
    m = 14 * mm * k
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=taille)
    c.setTitle("Affiche de prix")
    c.setFillColor(CREME)
    c.rect(0, 0, L, H, fill=1, stroke=0)
    c.setStrokeColor(OR)
    c.setLineWidth(2.2 * k)
    c.roundRect(m / 2, m / 2, L - m, H - m, 6 * mm * k)

    y = H - m - 4 * mm * k
    logo = _logo()
    if logo and logo[2]:  # logo complet
        _dessiner_logo(c, logo, L / 2, y - 30 * mm * k, 34 * mm * k, centre=True)
        y -= 36 * mm * k
    else:
        if logo:
            _dessiner_logo(c, logo, L / 2, y - 18 * mm * k, 20 * mm * k, centre=True)
            y -= 24 * mm * k
        c.setFillColor(NUIT)
        c.setFont("Times-Bold", 30 * k)
        c.drawCentredString(L / 2, y - 6 * mm * k, conf.get("producteur_nom") or "Maison Corsaire")
        y -= 12 * mm * k
    c.setFillColor(OR)
    c.setFont("Helvetica-Bold", 10 * k)
    c.drawCentredString(L / 2, y, "RHUMS ARRANGÉS ARTISANAUX", charSpace=3 * k)
    y -= 12 * mm * k

    # Place disponible pour la liste : on réduit la taille si beaucoup de produits
    bas = m + 52 * mm * k
    n = len(produits) + (len(coffrets) + 1 if coffrets else 0)
    base = (24 if avec_notes else 16) * mm * k
    dispo = y - bas
    echelle = min(max(dispo / (max(n, 1) * base), .45), 1.7)  # peu de produits : plus grand
    pas = base * echelle
    y -= max(dispo - n * pas, 0) / 2 * .8  # liste centrée verticalement
    t_nom, t_prix, t_note = 17 * k * max(echelle, .62), 19 * k * max(echelle, .62), 9 * k * max(echelle, .7)
    x0, x1 = m + 8 * mm * k, L - m - 8 * mm * k

    def produit(nom, detail, prix, note=None):
        nonlocal y
        c.setFillColor(NUIT)
        c.setFont("Times-Bold", t_nom)
        c.drawString(x0, y, nom[:42])
        largeur_nom = c.stringWidth(nom[:42], "Times-Bold", t_nom)
        c.setFont("Helvetica", t_nom * .55)
        c.setFillColor(GRIS)
        c.drawString(x0 + largeur_nom + 3 * mm * k, y + 0.5 * mm, detail)
        c.setFillColor(OR)
        c.setFont("Times-Bold", t_prix)
        c.drawRightString(x1, y, prix)
        # pointillés entre le nom et le prix
        debut = x0 + largeur_nom + c.stringWidth(detail, "Helvetica", t_nom * .55) + 6 * mm * k
        fin = x1 - c.stringWidth(prix, "Times-Bold", t_prix) - 3 * mm * k
        if fin > debut:
            c.setStrokeColor(colors.HexColor("#d8c9b0"))
            c.setDash(1, 3 * k)
            c.setLineWidth(.8 * k)
            c.line(debut, y + 1 * mm, fin, y + 1 * mm)
            c.setDash()
        y -= t_nom * .5
        if note and avec_notes:
            c.setFillColor(GRIS)
            c.setFont("Helvetica-Oblique", t_note)
            for i, ligne in enumerate(_decouper(c, note, "Helvetica-Oblique", t_note,
                                                x1 - x0 - 30 * mm * k)[:2 if echelle >= 1 else 1]):
                c.drawString(x0, y - t_note * .6 - i * t_note * 1.25, ligne)
        y -= pas - t_nom * .5

    if not produits:
        c.setFillColor(GRIS)
        c.setFont("Helvetica", 12 * k)
        c.drawCentredString(L / 2, y, "Aucun rhum en stock avec un prix de vente.")
        y -= 12 * mm * k
    for p in produits:
        detail = f"{p['volume']} cl" + (f" · {to_float(p['degre']):g} % vol." if p["degre"] else "")
        produit(p["nom"], detail, _euro(p["prix"]).replace(",00", ""), p["notes"])
    if coffrets:
        y -= 2 * mm * k
        c.setFillColor(OR)
        c.setFont("Helvetica-Bold", 10 * k)
        c.drawCentredString(L / 2, y, "COFFRETS", charSpace=3 * k)
        y -= 9 * mm * k
        for cf in coffrets:
            produit(cf["nom"], "", _euro(cf["prix_ttc"]).replace(",00", ""), cf["notes"])

    # Pied : consigne, fidélité, QR avis, mentions légales
    yb = m + 6 * mm * k
    from fidelite import regles, texte_avantage, texte_condition
    infos = []
    r = regles(conf)
    if r["active"]:
        infos.append(f"Fidélité : {texte_condition(r)} = {texte_avantage(r)} au prochain passage")
    if to_float(conf.get("consigne_montant")):
        infos.append(f"Bouteille consignée {_euro(to_float(conf.get('consigne_montant')))}, "
                     "remboursée au retour")
    cote = 30 * mm * k
    from etiquette_pdf import dessiner_qr
    lien = url_for("avis_public", _external=True,
                   _scheme="https" if os.environ.get("HTTPS") == "1" else None)
    dessiner_qr(c, lien, x1 - cote, yb + 8 * mm * k, cote)
    c.setFillColor(NUIT)
    c.setFont("Helvetica-Bold", 8 * k)
    c.drawCentredString(x1 - cote / 2, yb + 4.5 * mm * k, "Votre avis compte !")
    yy = yb + 8 * mm * k + cote - 4 * mm * k
    c.setFont("Helvetica", 10 * k)
    for info in infos:
        for ligne in _decouper(c, "• " + info, "Helvetica", 10 * k, x1 - x0 - cote - 8 * mm * k):
            c.drawString(x0, yy, ligne)
            yy -= 5.2 * mm * k
    c.setFillColor(GRIS)
    c.setFont("Helvetica-Bold", 8.5 * k)
    c.drawString(x0, yb + 4.5 * mm * k, "Vente d'alcool interdite aux mineurs.")
    c.setFont("Helvetica", 7.5 * k)
    c.drawString(x0, yb, MODERATION)
    c.showPage()
    c.save()
    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="Affiche-prix.pdf"'})
