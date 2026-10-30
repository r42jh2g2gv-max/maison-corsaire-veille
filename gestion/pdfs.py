"""Génération des PDF : ticket de caisse, facture, bon d'achat."""
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A6, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

NUIT = colors.HexColor("#0f1d33")
OR = colors.HexColor("#b8902f")
GRIS = colors.HexColor("#5b6170")
LIGNE = colors.HexColor("#d8cfbd")
MODERATION = ("L'abus d'alcool est dangereux pour la santé, à consommer avec modération.")


def _euro(v):
    txt = f"{v:,.2f}".replace(",", " ").replace(".", ",")
    return f"{txt} €"


def _date(iso):
    return date.fromisoformat(iso[:10]).strftime("%d/%m/%Y") if iso else ""


def _tva(conf):
    if conf.get("tva_applicable") == "1":
        return float(conf.get("tva_taux") or 20) / 100
    return 0.0


def _decouper(c, texte, police, taille, largeur):
    """Coupe un texte en lignes tenant dans la largeur donnée."""
    lignes = []
    for paragraphe in (texte or "").split("\n"):
        mots, courante = paragraphe.split(), ""
        for mot in mots:
            essai = f"{courante} {mot}".strip()
            if c.stringWidth(essai, police, taille) <= largeur:
                courante = essai
            else:
                if courante:
                    lignes.append(courante)
                courante = mot
        lignes.append(courante)
    return lignes


def _designation(l):
    deg = f" · {l['degre']:g} % vol." if l["degre"] else ""
    return f"{l['recette_nom']} {l['volume_cl']} cl{deg}", f"Lot {l['numero']}"


# --------------------------------------------------------------------------
# Ticket de caisse (format 80 mm)
# --------------------------------------------------------------------------

def ticket_pdf(ticket, lignes, conf, bon_code=None):
    largeur = 80 * mm
    marge = 5 * mm
    hauteur = (104 + 11 * len(lignes) + (6 if ticket["remise"] else 0)
               + (6 if ticket["consigne"] else 0)) * mm
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(largeur, hauteur))
    c.setTitle(f"Ticket {ticket['numero']}")
    y = hauteur - 10 * mm
    centre = largeur / 2

    c.setFillColor(NUIT)
    c.setFont("Times-Bold", 15)
    c.drawCentredString(centre, y, conf.get("producteur_nom") or "Maison Corsaire")
    y -= 4.5 * mm
    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS)
    for ligne in _decouper(c, conf.get("producteur_adresse"), "Helvetica", 7, largeur - 2 * marge):
        c.drawCentredString(centre, y, ligne)
        y -= 3.4 * mm
    contact = " · ".join(x for x in (conf.get("producteur_telephone"),
                                     conf.get("producteur_email")) if x)
    if contact:
        c.drawCentredString(centre, y, contact)
        y -= 3.4 * mm
    if conf.get("siret"):
        c.drawCentredString(centre, y, f"SIRET {conf['siret']}")
        y -= 3.4 * mm

    y -= 2 * mm
    c.setStrokeColor(OR)
    c.setLineWidth(0.8)
    c.line(marge, y, largeur - marge, y)
    y -= 5 * mm
    c.setFillColor(NUIT)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(marge, y, f"Ticket {ticket['numero']}")
    c.setFont("Helvetica", 8)
    c.drawRightString(largeur - marge, y, _date(ticket["date_vente"]))
    y -= 4 * mm
    c.setFillColor(GRIS)
    c.drawString(marge, y, f"Client : {ticket['client_nom']}"[:48])
    y -= 6 * mm

    c.setStrokeColor(LIGNE)
    c.setLineWidth(0.5)
    for l in lignes:
        nom, lot = _designation(l)
        c.setFillColor(NUIT)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(marge, y, nom[:46])
        y -= 3.8 * mm
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GRIS)
        c.drawString(marge, y, f"{lot}   {l['quantite']} × {_euro(l['prix_unitaire_ttc'])}")
        c.setFillColor(NUIT)
        c.drawRightString(largeur - marge, y, _euro(l["quantite"] * l["prix_unitaire_ttc"]))
        y -= 3 * mm
        c.line(marge, y, largeur - marge, y)
        y -= 4.2 * mm

    def total(label, valeur, gras=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if gras else "Helvetica", 10 if gras else 8)
        c.setFillColor(NUIT)
        c.drawString(marge, y, label)
        c.drawRightString(largeur - marge, y, valeur)
        y -= (6 if gras else 4.5) * mm

    total("Sous-total", _euro(ticket["sous_total"]))
    if ticket["remise"]:
        total(f"Bon d'achat {bon_code or ''}".strip(), "- " + _euro(ticket["remise"]))
    if ticket["consigne"]:
        total("Consigne bouteilles", _euro(ticket["consigne"]))
    y -= 1 * mm
    c.setStrokeColor(OR)
    c.line(marge, y + 4 * mm, largeur - marge, y + 4 * mm)
    total("TOTAL", _euro(ticket["total"]), gras=True)

    from noyau import MODES_PAIEMENT  # import tardif : évite une boucle d'import
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS)
    c.drawString(marge, y, f"Réglé par : {MODES_PAIEMENT.get(ticket['mode_paiement'], '')}")
    y -= 4.5 * mm
    tva = _tva(conf)
    if tva:
        ht = (ticket["sous_total"] - ticket["remise"]) / (1 + tva)
        c.drawString(marge, y, f"Dont TVA {tva * 100:g} % : {_euro(ht * tva)}")
    else:
        c.drawString(marge, y, "TVA non applicable, art. 293 B du CGI")
    y -= 7 * mm

    c.setFillColor(NUIT)
    c.setFont("Times-Italic", 10)
    c.drawCentredString(centre, y, "Merci et à bientôt !")
    y -= 5 * mm
    c.setFont("Helvetica", 6)
    c.setFillColor(GRIS)
    for ligne in _decouper(c, MODERATION, "Helvetica", 6, largeur - 2 * marge):
        c.drawCentredString(centre, y, ligne)
        y -= 3 * mm
    c.showPage()
    c.save()
    return buf.getvalue()


# --------------------------------------------------------------------------
# Facture A4
# --------------------------------------------------------------------------

def facture_pdf(ticket, lignes, conf, bon_code=None):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Facture {ticket['facture_numero']}")
    L, H = A4
    m = 18 * mm
    tva = _tva(conf)

    # En-tête : producteur
    c.setFillColor(NUIT)
    c.rect(0, H - 8 * mm, L, 8 * mm, fill=1, stroke=0)
    c.setFillColor(OR)
    c.rect(0, H - 9 * mm, L, 1 * mm, fill=1, stroke=0)
    y = H - 24 * mm
    c.setFillColor(NUIT)
    c.setFont("Times-Bold", 22)
    c.drawString(m, y, conf.get("producteur_nom") or "Maison Corsaire")
    c.setFont("Helvetica", 9)
    c.setFillColor(GRIS)
    y -= 6 * mm
    infos = [conf.get("producteur_adresse"), conf.get("producteur_telephone"),
             conf.get("producteur_email"),
             f"SIRET : {conf['siret']}" if conf.get("siret") else None,
             "Entrepreneur individuel"]
    for info in filter(None, infos):
        c.drawString(m, y, info)
        y -= 4.5 * mm

    # Bloc facture (droite)
    c.setFillColor(NUIT)
    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(L - m, H - 24 * mm, "FACTURE")
    c.setFont("Helvetica", 10)
    c.drawRightString(L - m, H - 31 * mm, f"N° {ticket['facture_numero']}")
    c.setFillColor(GRIS)
    c.drawRightString(L - m, H - 36.5 * mm, f"Date de facture : {_date(ticket['facture_date'])}")
    c.drawRightString(L - m, H - 41.5 * mm, f"Date de vente : {_date(ticket['date_vente'])}")
    c.drawRightString(L - m, H - 46.5 * mm, f"Réf. ticket : {ticket['numero']}")

    # Client
    y = min(y, H - 56 * mm) - 6 * mm
    c.setStrokeColor(LIGNE)
    c.setFillColor(colors.HexColor("#f7f2e8"))
    hauteur_client = 26 * mm
    c.roundRect(L / 2, y - hauteur_client + 6 * mm, L / 2 - m, hauteur_client, 3 * mm,
                fill=1, stroke=1)
    c.setFillColor(OR)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(L / 2 + 5 * mm, y, "FACTURÉ À")
    c.setFillColor(NUIT)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(L / 2 + 5 * mm, y - 6 * mm, ticket["client_nom"][:45])
    c.setFont("Helvetica", 9)
    yy = y - 11 * mm
    for ligne in _decouper(c, ticket["client_adresse"] or "", "Helvetica", 9, L / 2 - m - 10 * mm)[:3]:
        c.drawString(L / 2 + 5 * mm, yy, ligne)
        yy -= 4.5 * mm
    y -= hauteur_client + 6 * mm

    # Tableau des lignes
    cols = [m, m + 92 * mm, m + 112 * mm, m + 142 * mm]
    fin = L - m
    c.setFillColor(NUIT)
    c.rect(m, y - 2.5 * mm, fin - m, 8 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    suffixe = " HT" if tva else ""
    c.drawString(cols[0] + 3 * mm, y, "Désignation")
    c.drawRightString(cols[2] - 3 * mm, y, "Qté")
    c.drawRightString(cols[3] - 3 * mm, y, f"Prix unit.{suffixe}")
    c.drawRightString(fin - 3 * mm, y, f"Total{suffixe}")
    y -= 10 * mm
    for l in lignes:
        nom, lot = _designation(l)
        pu = l["prix_unitaire_ttc"] / (1 + tva)
        c.setFillColor(NUIT)
        c.setFont("Helvetica", 9.5)
        c.drawString(cols[0] + 3 * mm, y, nom[:55])
        c.drawRightString(cols[2] - 3 * mm, y, str(l["quantite"]))
        c.drawRightString(cols[3] - 3 * mm, y, _euro(pu))
        c.drawRightString(fin - 3 * mm, y, _euro(pu * l["quantite"]))
        c.setFillColor(GRIS)
        c.setFont("Helvetica", 8)
        c.drawString(cols[0] + 3 * mm, y - 4 * mm, lot)
        y -= 7 * mm
        c.setStrokeColor(LIGNE)
        c.line(m, y + 1 * mm, fin, y + 1 * mm)
        y -= 4 * mm

    # Totaux
    y -= 2 * mm
    x_label = L - m - 75 * mm

    def ligne_total(label, valeur, gras=False):
        nonlocal y
        c.setFillColor(NUIT)
        c.setFont("Helvetica-Bold" if gras else "Helvetica", 11 if gras else 9.5)
        c.drawString(x_label, y, label)
        c.drawRightString(fin - 3 * mm, y, valeur)
        y -= (8 if gras else 5.5) * mm

    net_produits = ticket["sous_total"] - ticket["remise"]
    ligne_total(f"Total produits{suffixe}", _euro(ticket["sous_total"] / (1 + tva)))
    if ticket["remise"]:
        ligne_total(f"Bon d'achat {bon_code or ''}".strip(), "- " + _euro(ticket["remise"] / (1 + tva)))
    if tva:
        ligne_total(f"TVA {tva * 100:g} %", _euro(net_produits - net_produits / (1 + tva)))
    if ticket["consigne"]:
        ligne_total("Consigne bouteilles (remboursable)", _euro(ticket["consigne"]))
    c.setStrokeColor(OR)
    c.setLineWidth(1)
    c.line(x_label, y + 4 * mm, fin, y + 4 * mm)
    y -= 1 * mm
    ligne_total("NET À PAYER" if not tva else "TOTAL TTC", _euro(ticket["total"]), gras=True)
    if not tva:
        c.setFont("Helvetica-Oblique", 8.5)
        c.setFillColor(GRIS)
        c.drawRightString(fin - 3 * mm, y + 3 * mm, "TVA non applicable, art. 293 B du CGI")
        y -= 3 * mm

    # Règlement et mentions
    from noyau import MODES_PAIEMENT
    y -= 6 * mm
    c.setFillColor(NUIT)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(m, y, "Règlement")
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.setFillColor(GRIS)
    c.drawString(m, y, f"Réglée le {_date(ticket['date_vente'])} par "
                       f"{MODES_PAIEMENT.get(ticket['mode_paiement'], '').lower()}.")
    y -= 4.5 * mm
    mentions = [conf.get("conditions_paiement") or ""]
    if conf.get("iban"):
        mentions.append(f"IBAN : {conf['iban']}")
    mentions.append("Pas d'escompte pour paiement anticipé. Pour les clients professionnels, "
                    "tout retard de paiement entraîne des pénalités au taux de trois fois "
                    "le taux d'intérêt légal et une indemnité forfaitaire de 40 € pour "
                    "frais de recouvrement.")
    for mention in filter(None, mentions):
        for ligne in _decouper(c, mention, "Helvetica", 8.5, L - 2 * m):
            c.drawString(m, y, ligne)
            y -= 4 * mm

    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRIS)
    c.drawCentredString(L / 2, 12 * mm, MODERATION)
    c.drawCentredString(L / 2, 8 * mm, f"{conf.get('producteur_nom') or ''} · "
                                       f"Facture {ticket['facture_numero']}")
    c.showPage()
    c.save()
    return buf.getvalue()


# --------------------------------------------------------------------------
# Bon d'achat (A6 paysage)
# --------------------------------------------------------------------------

def bon_pdf(bon, conf):
    buf = BytesIO()
    taille = landscape(A6)
    c = canvas.Canvas(buf, pagesize=taille)
    c.setTitle(f"Bon d'achat {bon['code']}")
    L, H = taille
    c.setFillColor(NUIT)
    c.rect(0, 0, L, H, fill=1, stroke=0)
    # Veinage « bois » discret
    c.setStrokeColor(colors.HexColor("#1b2c4b"))
    c.setLineWidth(0.6)
    for i in range(0, int(L), 9):
        c.line(i, 0, i + 30, H)
    c.setStrokeColor(OR)
    c.setLineWidth(1.4)
    c.roundRect(5 * mm, 5 * mm, L - 10 * mm, H - 10 * mm, 4 * mm)
    c.setLineWidth(0.5)
    c.roundRect(7 * mm, 7 * mm, L - 14 * mm, H - 14 * mm, 3 * mm)

    c.setFillColor(colors.HexColor("#e6c983"))
    c.setFont("Times-Bold", 15)
    c.drawCentredString(L / 2, H - 19 * mm, conf.get("producteur_nom") or "Maison Corsaire")
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(L / 2, H - 24 * mm, "BON D'ACHAT", charSpace=2.5)
    c.setFont("Times-Bold", 38)
    c.drawCentredString(L / 2, H / 2 - 6 * mm, _euro(bon["montant"]))
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    if bon["beneficiaire"]:
        c.drawCentredString(L / 2, H / 2 - 15 * mm, f"Offert à {bon['beneficiaire']}")
    if bon["motif"]:
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(L / 2, H / 2 - 20 * mm, bon["motif"][:70])
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#e6c983"))
    c.drawString(12 * mm, 12 * mm, f"Code : {bon['code']}")
    if bon["date_expiration"]:
        c.drawRightString(L - 12 * mm, 12 * mm, f"Valable jusqu'au {_date(bon['date_expiration'])}")
    c.setFont("Helvetica", 5.5)
    c.setFillColor(colors.HexColor("#b4bfd2"))
    c.drawCentredString(L / 2, 8.5 * mm, "Utilisable en une fois, non remboursable. " + MODERATION)
    c.showPage()
    c.save()
    return buf.getvalue()
