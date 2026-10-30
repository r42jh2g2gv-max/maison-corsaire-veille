"""Module 5 — étiquette arrière (contre-étiquette) en PDF."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

NOIR = colors.HexColor("#111111")
GRIS = colors.HexColor("#555555")
ROUGE = colors.HexColor("#d0021b")
TRAIT_COUPE = colors.HexColor("#bbbbbb")


def _style(taille, gras=False, interligne=1.22, alignement=0):
    return ParagraphStyle(
        "e", fontName="Helvetica-Bold" if gras else "Helvetica", fontSize=taille,
        leading=taille * interligne, textColor=NOIR, alignment=alignement)


def _avec_allergenes_en_gras(texte, allergenes):
    """Met en gras les allergènes dans la liste des ingrédients (obligation INCO)."""
    html = escape(texte or "")
    for a in sorted(allergenes, key=len, reverse=True):
        a = a.strip()
        if not a:
            continue
        i = html.lower().find(a.lower())
        if i >= 0:
            html = html[:i] + "<b>" + html[i:i + len(a)] + "</b>" + html[i + len(a):]
    return html


def picto_femme_enceinte(c, x, y, d):
    """Pictogramme « femme enceinte » (cercle barré), coin inférieur gauche en (x, y)."""
    def p(u, v):
        return x + u * d, y + v * d

    c.saveState()
    c.setFillColor(colors.white)
    c.circle(x + d / 2, y + d / 2, d / 2, stroke=0, fill=1)
    # Silhouette de profil (tournée vers la gauche) : ventre arrondi, verre porté à la bouche
    c.setFillColor(NOIR)
    c.circle(*p(0.555, 0.765), 0.078 * d, stroke=0, fill=1)
    corps = c.beginPath()
    corps.moveTo(*p(0.555, 0.680))                                   # nuque
    corps.curveTo(*p(0.610, 0.660), *p(0.650, 0.600), *p(0.640, 0.520))  # dos
    corps.curveTo(*p(0.635, 0.470), *p(0.640, 0.420), *p(0.630, 0.380))  # reins
    corps.lineTo(*p(0.615, 0.160))                                   # arrière de la jambe
    corps.lineTo(*p(0.640, 0.130))                                   # talon
    corps.lineTo(*p(0.520, 0.130))                                   # pied
    corps.lineTo(*p(0.540, 0.160))
    corps.lineTo(*p(0.535, 0.330))                                   # avant de la jambe
    corps.curveTo(*p(0.420, 0.330), *p(0.330, 0.400), *p(0.340, 0.470))  # bas du ventre
    corps.curveTo(*p(0.350, 0.545), *p(0.430, 0.580), *p(0.475, 0.575))  # haut du ventre
    corps.curveTo(*p(0.470, 0.620), *p(0.490, 0.660), *p(0.505, 0.680))  # poitrine
    corps.close()
    c.drawPath(corps, stroke=0, fill=1)
    c.setStrokeColor(NOIR)
    c.setLineCap(1)
    c.setLineJoin(1)
    c.setLineWidth(0.06 * d)
    bras = c.beginPath()
    bras.moveTo(*p(0.560, 0.640))
    bras.lineTo(*p(0.500, 0.555))
    bras.lineTo(*p(0.445, 0.700))
    c.drawPath(bras, stroke=1, fill=0)
    verre = c.beginPath()
    verre.moveTo(*p(0.375, 0.815))
    verre.lineTo(*p(0.470, 0.815))
    verre.lineTo(*p(0.450, 0.690))
    verre.lineTo(*p(0.395, 0.690))
    verre.close()
    c.drawPath(verre, stroke=0, fill=1)
    # Cercle et barre
    c.setLineWidth(0.075 * d)
    c.circle(x + d / 2, y + d / 2, d / 2 - 0.0375 * d, stroke=1, fill=0)
    c.setStrokeColor(ROUGE)
    c.setLineWidth(0.08 * d)
    c.line(*p(0.17, 0.83), *p(0.83, 0.17))
    c.restoreState()


def dessiner_etiquette(c, x, y, L, H, e, trait_coupe=True):
    """Dessine une contre-étiquette de L × H (points) à la position (x, y)."""
    m = 3.5 * mm
    if trait_coupe:
        c.setStrokeColor(TRAIT_COUPE)
        c.setLineWidth(0.4)
        c.setDash(2, 2)
        c.rect(x, y, L, H)
        c.setDash()
    largeur = L - 2 * m

    # --- Bloc bas (fixe) : pictogramme, lot, volume/degré, producteur, tri ---
    d = min(15 * mm, largeur * 0.3)
    bas = y + m
    tri = Paragraph(escape(e["tri"] or ""), _style(5.2, interligne=1.15))
    _, h_tri = tri.wrap(largeur - d - 2 * mm, 30 * mm)
    picto_femme_enceinte(c, x + L - m - d, bas, d)
    if e["tri"]:
        tri.drawOn(c, x + m, bas)
    y_bloc = bas + max(d, h_tri) + 2 * mm

    producteur = Paragraph(
        f"Élaboré par <b>{escape(e['producteur_nom'])}</b>, {escape(e['producteur_adresse'])}",
        _style(5.6, interligne=1.2))
    _, h_prod = producteur.wrap(largeur, 30 * mm)
    producteur.drawOn(c, x + m, y_bloc)
    y_bloc += h_prod + 2 * mm

    # Volume et degré (gros caractères) + case lot à tamponner
    h_case = 9.5 * mm
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + m, y_bloc + 5.2 * mm, e["volume"])
    c.drawString(x + m, y_bloc + 0.4 * mm, e["degre"])
    l_case = min(30 * mm, largeur * 0.52)
    xc = x + L - m - l_case
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.7)
    c.rect(xc, y_bloc, l_case, h_case)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(xc + 1.3 * mm, y_bloc + h_case - 2.6 * mm, "LOT")
    if e.get("lot"):
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(xc + l_case / 2, y_bloc + 2 * mm, e["lot"])
    y_bloc += h_case + 2.2 * mm

    # --- Bloc haut (texte) : on réduit la taille jusqu'à ce que tout tienne ---
    haut = y + H - m
    place = haut - y_bloc
    allergenes = [a.strip() for a in (e["allergenes"] or "").split(",") if a.strip()]
    for taille in (7.2, 6.8, 6.4, 6.0, 5.6, 5.2, 4.8):
        blocs = [Paragraph(f"<b>{escape(e['denomination'])}</b>",
                           _style(taille + 2.2, gras=True, interligne=1.15))]
        if e["ingredients"]:
            blocs.append(Paragraph(
                "<b>Ingrédients :</b> " + _avec_allergenes_en_gras(e["ingredients"], allergenes),
                _style(taille)))
        if allergenes:
            blocs.append(Paragraph("<b>Contient : " + escape(", ".join(allergenes)) + ".</b>",
                                   _style(taille)))
        if e["mentions"]:
            blocs.append(Paragraph(escape(e["mentions"]).replace("\n", "<br/>"),
                                   _style(taille - 0.4)))
        hauteurs = [b.wrap(largeur, place)[1] for b in blocs]
        espace = 1.6 * mm
        if sum(hauteurs) + espace * (len(blocs) - 1) <= place:
            break
    yy = haut
    for b, h in zip(blocs, hauteurs):
        yy -= h
        b.drawOn(c, x + m, yy)
        yy -= espace


def etiquettes_pdf(e, largeur_mm, hauteur_mm, copies=1, planche=True):
    L, H = largeur_mm * mm, hauteur_mm * mm
    buf = BytesIO()
    if not planche:
        c = canvas.Canvas(buf, pagesize=(L, H))
        c.setTitle(f"Contre-étiquette {e['nom']}")
        for _ in range(copies):
            dessiner_etiquette(c, 0, 0, L, H, e, trait_coupe=False)
            c.showPage()
        c.save()
        return buf.getvalue()

    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Planche de contre-étiquettes {e['nom']}")
    PL, PH = A4
    marge, ecart = 8 * mm, 3 * mm
    cols = max(int((PL - 2 * marge + ecart) // (L + ecart)), 1)
    rangs = max(int((PH - 2 * marge - 6 * mm + ecart) // (H + ecart)), 1)
    par_page = cols * rangs
    x0 = (PL - (cols * L + (cols - 1) * ecart)) / 2
    for n in range(copies):
        if n and n % par_page == 0:
            c.showPage()
        if n % par_page == 0:
            c.setFont("Helvetica", 7)
            c.setFillColor(GRIS)
            c.drawString(marge, PH - marge + 1 * mm,
                         f"{e['nom']} · contre-étiquettes {largeur_mm:g} × {hauteur_mm:g} mm · "
                         "imprimer à 100 % (taille réelle), découper sur les pointillés")
        i = n % par_page
        col, rang = i % cols, i // cols
        x = x0 + col * (L + ecart)
        y = PH - marge - 6 * mm - (rang + 1) * H - rang * ecart
        dessiner_etiquette(c, x, y, L, H, e)
    c.showPage()
    c.save()
    return buf.getvalue()
