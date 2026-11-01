"""Fiche de production à imprimer : ce qu'il faut peser pour un lot, avec cases à cocher."""
from datetime import date, timedelta
from io import BytesIO

from flask import Response, request
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from calculs import PERTE_DEFAUT, bouteilles_estimees, convertir, to_float
from noyau import app, get_db, get_or_404, settings
from pdfs import GRIS, NUIT, OR, _date, _decouper, _dessiner_logo, _logo

ORDRE = "CASE categorie WHEN 'rhum' THEN 0 WHEN 'fruit' THEN 1 WHEN 'epice' THEN 2 " \
        "WHEN 'sucre' THEN 3 ELSE 4 END, id"
CONTROLES = ["Plan de travail et ustensiles nettoyés et désinfectés",
             "Bocaux / cuves lavés, rincés et secs",
             "Fruits lavés, triés (pas de fruit abîmé), épluchés",
             "Mains lavées, cheveux attachés, tablier propre",
             "Étiquette de cuve posée : n° de lot + date"]


def _quantite(q, unite):
    if q is None:
        return "—"
    unite = unite or ""
    if unite == "g" and q >= 1000:
        q, unite = q / 1000, "kg"
    elif unite == "ml" and q >= 1000:
        q, unite = q / 1000, "L"
    texte = f"{q:,.3f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")
    return f"{texte} {unite}".strip()


def stock_matiere(conn, mp_id):
    if not mp_id:
        return None
    row = conn.execute(
        """SELECT m.unite, COALESCE((SELECT SUM(quantite) FROM mouvements_mp v WHERE v.mp_id = m.id), 0)
           AS stock FROM matieres_premieres m WHERE m.id = ?""", (mp_id,)).fetchone()
    return row


def fiche_pdf(f, conf):
    """f : titre, sous_titre, infos [(libellé, valeur)], ingredients [(nom, qté, unité, stock)],
    instructions, numero_lot."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    L, H = A4
    m = 15 * mm
    c.setTitle(f"Fiche de production {f['titre']}")
    y = H - m
    logo = _logo("symbole")
    if logo:
        _dessiner_logo(c, logo, m + 7 * mm, y - 12 * mm, 14 * mm, centre=True)
    x0 = m + (18 * mm if logo else 0)
    c.setFillColor(OR)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x0, y - 3 * mm, "FICHE DE PRODUCTION")
    c.setFillColor(NUIT)
    c.setFont("Times-Bold", 20)
    c.drawString(x0, y - 11 * mm, f["titre"][:48])
    c.setFont("Helvetica", 9)
    c.setFillColor(GRIS)
    c.drawString(x0, y - 16.5 * mm, f["sous_titre"][:110])
    # Case n° de lot (à remplir ou pré-remplie)
    c.setStrokeColor(NUIT)
    c.setLineWidth(0.8)
    c.rect(L - m - 48 * mm, y - 17 * mm, 48 * mm, 15 * mm)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(NUIT)
    c.drawString(L - m - 46.5 * mm, y - 5.5 * mm, "N° DE LOT")
    if f.get("numero_lot"):
        c.setFont("Courier-Bold", 13)
        c.drawCentredString(L - m - 24 * mm, y - 13.5 * mm, f["numero_lot"])
    y -= 24 * mm
    c.setStrokeColor(OR)
    c.setLineWidth(1)
    c.line(m, y, L - m, y)
    y -= 7 * mm

    # Informations en 2 colonnes
    c.setFont("Helvetica", 9)
    col = (L - 2 * m) / 2
    for i, (lib, val) in enumerate(f["infos"]):
        x = m + (i % 2) * col
        c.setFillColor(GRIS)
        c.drawString(x, y, lib)
        c.setFillColor(NUIT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 42 * mm, y, str(val)[:40])
        c.setFont("Helvetica", 9)
        if i % 2:
            y -= 5.5 * mm
    if len(f["infos"]) % 2:
        y -= 5.5 * mm
    y -= 4 * mm

    # Tableau des pesées
    largeurs = [9 * mm, 62 * mm, 30 * mm, 26 * mm, 30 * mm, 23 * mm]
    titres = ["", "Ingrédient", "À peser", "En stock", "Lot fournisseur", "Pesé"]
    c.setFillColor(NUIT)
    c.rect(m, y - 2.5 * mm, sum(largeurs), 8 * mm, fill=1, stroke=0)
    c.setFillColorRGB(0.92, 0.79, 0.51)
    c.setFont("Helvetica-Bold", 8.5)
    x = m
    for t, w in zip(titres, largeurs):
        c.drawString(x + 2 * mm, y, t)
        x += w
    y -= 9 * mm
    c.setLineWidth(0.4)
    for nom, q, unite, stock in f["ingredients"]:
        x = m
        c.setStrokeColor(NUIT)
        c.rect(x + 2.5 * mm, y - 1 * mm, 4 * mm, 4 * mm)
        x += largeurs[0]
        c.setFillColor(NUIT)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + 2 * mm, y, nom[:34])
        x += largeurs[1]
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x + 2 * mm, y, _quantite(q, unite))
        x += largeurs[2]
        c.setFont("Helvetica", 8.5)
        if isinstance(stock, str):
            c.setFillColor(GRIS)
            c.drawString(x + 2 * mm, y, stock)
        elif stock is not None:
            besoin = convertir(q, unite, stock[0])
            manque = besoin is not None and stock[1] < besoin - 1e-9
            c.setFillColorRGB(0.75, 0.15, 0.1) if manque else c.setFillColor(GRIS)
            c.drawString(x + 2 * mm, y, _quantite(stock[1], stock[0]) + (" !" if manque else ""))
        else:
            c.setFillColor(GRIS)
            c.drawString(x + 2 * mm, y, "—")
        x += largeurs[3]
        c.setStrokeColor(GRIS)
        c.line(x + 2 * mm, y - 1.5 * mm, x + largeurs[4] - 2 * mm, y - 1.5 * mm)
        x += largeurs[4]
        c.line(x + 2 * mm, y - 1.5 * mm, x + largeurs[5] - 2 * mm, y - 1.5 * mm)
        y -= 4.5 * mm
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.line(m, y, m + sum(largeurs), y)
        y -= 5.5 * mm
        if y < 80 * mm:
            c.showPage()
            y = H - m
    y -= 3 * mm

    def titre(t):
        nonlocal y
        c.setFillColor(OR)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m, y, t.upper())
        y -= 6 * mm

    titre("Avant de commencer")
    c.setFont("Helvetica", 9)
    for ctrl in CONTROLES:
        c.setStrokeColor(NUIT)
        c.rect(m, y - 1 * mm, 3.6 * mm, 3.6 * mm)
        c.setFillColor(NUIT)
        c.drawString(m + 6 * mm, y, ctrl)
        y -= 5.5 * mm
    y -= 3 * mm
    if f.get("instructions"):
        titre("Étapes")
        c.setFillColor(NUIT)
        c.setFont("Helvetica", 9)
        for paragraphe in f["instructions"].splitlines():
            for ligne in _decouper(c, paragraphe, "Helvetica", 9, L - 2 * m) or [""]:
                if y < 40 * mm:
                    c.showPage()
                    y = H - m
                    c.setFont("Helvetica", 9)
                    c.setFillColor(NUIT)
                c.drawString(m, y, ligne)
                y -= 4.6 * mm
        y -= 3 * mm
    if y < 45 * mm:
        c.showPage()
        y = H - m
    titre("Observations (aspect, odeur, écarts de pesée…)")
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    for _ in range(3):
        y -= 2 * mm
        c.line(m, y, L - m, y)
        y -= 5 * mm
    y -= 4 * mm
    c.setFillColor(NUIT)
    c.setFont("Helvetica", 9)
    c.drawString(m, y, "Date et heure : ____________________")
    c.drawString(L / 2, y, "Fait par : ____________________")
    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS)
    c.drawCentredString(L / 2, 10 * mm, f"{conf.get('producteur_nom') or 'Maison Corsaire'} · "
                        "à conserver avec le registre des lots (traçabilité)")
    c.showPage()
    c.save()
    return buf.getvalue()


def _reponse(pdf, nom):
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="Production-{nom}.pdf"'})


@app.route("/lots/<int:lot_id>/production.pdf")
def production_lot(lot_id):
    conn = get_db()
    lot = get_or_404("lots", lot_id)
    recette = conn.execute("SELECT * FROM recettes WHERE id = ?", (lot["recette_id"],)).fetchone() \
        if lot["recette_id"] else None
    ings = conn.execute(f"SELECT * FROM lot_ingredients WHERE lot_id = ? ORDER BY {ORDRE}",
                        (lot_id,)).fetchall()
    duree = recette["duree_maceration_jours"] if recette and recette["duree_maceration_jours"] else None
    fin = (date.fromisoformat(lot["date_maceration"]) + timedelta(days=duree)).isoformat() \
        if lot["date_maceration"] and duree else None
    infos = [("Mise en macération", _date(lot["date_maceration"]) if lot["date_maceration"] else "—"),
             ("Fin prévue", _date(fin) if fin else "—"),
             ("Volume à macérer", f"{to_float(lot['volume_macere_l']):g} L" if lot["volume_macere_l"] else "—"),
             ("Perte prévue", f"{lot['perte_pct'] if lot['perte_pct'] is not None else PERTE_DEFAUT:g} %"),
             ("Bouteilles visées", f"{lot['nb_bouteilles']} × {lot['volume_cl']} cl"),
             ("Degré visé", f"{lot['degre']:g} % vol." if lot["degre"] else "—")]
    f = {"titre": lot["recette_nom"], "numero_lot": lot["numero"],
         "sous_titre": "Lot d'essai" if lot["essai"] else "Cochez chaque ingrédient une fois pesé.",
         "infos": infos,
         # déjà déduits du stock à la création du lot
         "ingredients": [(i["nom"], i["quantite"], i["unite"], "déduit" if i["mp_id"] else None)
                         for i in ings],
         "instructions": recette["instructions"] if recette else None}
    return _reponse(fiche_pdf(f, settings()), lot["numero"])


@app.route("/recettes/<int:recette_id>/production.pdf")
def production_recette(recette_id):
    """Fiche avant de créer le lot : quantités pour le nombre de litres choisi."""
    conn = get_db()
    recette = get_or_404("recettes", recette_id)
    litres = min(max(to_float(request.args.get("litres"), 10), 0.1), 2000)
    ings = conn.execute(f"SELECT * FROM recette_ingredients WHERE recette_id = ? ORDER BY {ORDRE}",
                        (recette_id,)).fetchall()
    perte = recette["perte_pct"] if recette["perte_pct"] is not None else PERTE_DEFAUT
    volume = 50
    infos = [("Volume à macérer", f"{litres:g} L"),
             ("Durée de macération", f"{recette['duree_maceration_jours'] or 60} jours"),
             ("Perte prévue", f"{perte:g} %"),
             ("Bouteilles estimées", f"≈ {bouteilles_estimees(litres, perte, volume)} × {volume} cl"),
             ("Degré visé", f"{recette['degre']:g} % vol." if recette["degre"] else "—"),
             ("Date", "____ / ____ / ________")]
    f = {"titre": recette["nom"], "numero_lot": None,
         "sous_titre": f"Quantités calculées pour {litres:g} L. Cochez chaque ingrédient une fois pesé.",
         "infos": infos,
         "ingredients": [(i["nom"], (i["quantite_par_litre"] or 0) * litres if i["quantite_par_litre"]
                          is not None else None, i["unite"], stock_matiere(conn, i["mp_id"]))
                         for i in ings],
         "instructions": recette["instructions"]}
    return _reponse(fiche_pdf(f, settings()), f"{litres:g}L")
