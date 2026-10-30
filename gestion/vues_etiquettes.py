"""Module 5 — contre-étiquettes réglementaires par recette ou par lot."""
import re

from flask import Response, flash, redirect, render_template, request, url_for

from calculs import convertir, to_float
from noyau import app, get_db, get_or_404, nombre, set_setting, settings, to_int
from etiquette_pdf import etiquettes_pdf

DENOMINATION = "Boisson spiritueuse à base de rhum"
app.jinja_env.globals["DENOMINATION_DEFAUT"] = DENOMINATION



def nom_pour_etiquette(nom, nom_etiquette=None):
    """« Rhum agricole blanc 50° » → « rhum agricole blanc » (sauf nom d'étiquette choisi)."""
    if nom_etiquette:
        return nom_etiquette.strip()
    n = re.sub(r"\s*\(.*?\)", "", nom or "")
    n = re.sub(r"\s*\d+(?:[.,]\d+)?\s*°", "", n).strip()
    return n[:1].lower() + n[1:] if len(n) > 1 and not n[1].isupper() else n


def composer_liste(lignes):
    """lignes : (nom, quantité, unité, nom_etiquette, allergène).
    Retourne le texte des ingrédients (ordre décroissant de quantité) et les allergènes."""
    cumul, ordre = {}, []
    for nom, quantite, unite, nom_etiquette, allergene in lignes:
        poids = -1.0  # pièces (gousses, citrons) : en fin de liste
        for base in ("g", "ml"):  # approximation : 1 L ≈ 1 kg
            q = convertir(quantite or 0, unite, base)
            if q is not None:
                poids = q
                break
        cle = nom_pour_etiquette(nom, nom_etiquette)
        if cle.lower() not in cumul:
            ordre.append(cle)
            cumul[cle.lower()] = [0.0, set()]
        cumul[cle.lower()][0] += poids
        if allergene:
            cumul[cle.lower()][1].add(allergene.strip())
    noms = sorted(ordre, key=lambda n: -cumul[n.lower()][0])
    texte = ", ".join(noms)
    texte = (texte[:1].upper() + texte[1:] + ".") if texte else ""
    allergenes = sorted({a for v in cumul.values() for a in v[1]})
    return texte, allergenes


def ingredients_recette(conn, recette_id):
    return composer_liste(conn.execute(
        """SELECT i.nom, i.quantite_par_litre, i.unite, m.nom_etiquette, m.allergene
           FROM recette_ingredients i LEFT JOIN matieres_premieres m ON m.id = i.mp_id
           WHERE i.recette_id = ?""", (recette_id,)).fetchall())


def ingredients_lot(conn, lot_id):
    return composer_liste(conn.execute(
        """SELECT i.nom, i.quantite, i.unite, m.nom_etiquette, m.allergene
           FROM lot_ingredients i LEFT JOIN matieres_premieres m ON m.id = i.mp_id
           WHERE i.lot_id = ?""", (lot_id,)).fetchall())


def fusion_allergenes(auto, supplementaires):
    vus, liste = set(), []
    for a in list(auto) + [x.strip() for x in (supplementaires or "").split(",")]:
        if a and a.lower() not in vus:
            vus.add(a.lower())
            liste.append(a)
    return ", ".join(liste)


def donnees_etiquette(conn, recette=None, lot=None):
    """Les ingrédients suivent ce qui est réellement utilisé : ceux du lot pour une étiquette
    de lot, ceux de la recette sinon (sauf liste personnalisée sur la recette)."""
    conf = settings()
    nom = (recette["nom"] if recette else None) or (lot["recette_nom"] if lot else "")
    texte, allergenes = ingredients_lot(conn, lot["id"]) if lot else ("", [])
    if not texte and recette:
        texte, allergenes = ingredients_recette(conn, recette["id"])
        if recette["etiquette_ingredients"]:
            texte = recette["etiquette_ingredients"]
    degre = (lot["degre"] if lot and lot["degre"] is not None else None) \
        or (recette["degre"] if recette else None)
    volume = lot["volume_cl"] if lot else to_int(request.args.get("volume"), 50) or 50
    return {
        "nom": nom,
        "denomination": (recette["denomination"] if recette and recette["denomination"]
                         else DENOMINATION),
        "ingredients": texte,
        "allergenes": fusion_allergenes(allergenes, recette["allergenes"] if recette else ""),
        "mentions": recette["etiquette_mentions"] if recette else "",
        "volume": f"{volume} cl",
        "degre": f"{nombre(degre, 1).replace(',0', '')} % vol." if degre else "… % vol.",
        "producteur_nom": conf.get("producteur_nom") or "",
        "producteur_adresse": conf.get("producteur_adresse") or "",
        "tri": conf.get("etiquette_tri") or "",
        "lot": lot["numero"] if lot and request.args.get("lot_imprime") else None,
    }


@app.route("/etiquettes")
def etiquettes():
    conn = get_db()
    recettes = conn.execute("SELECT * FROM recettes ORDER BY nom").fetchall()
    lots = conn.execute(
        "SELECT * FROM lots WHERE statut IN ('pret', 'embouteille', 'maceration')"
        " ORDER BY numero DESC").fetchall()
    fiches = []
    for r in recettes:
        texte, allergenes = ingredients_recette(conn, r["id"])
        fiches.append({"r": r, "auto": texte, "allergenes_auto": ", ".join(allergenes)})
    apercus_lots = {}
    for l in lots:
        e = donnees_etiquette(conn, recette=conn.execute(
            "SELECT * FROM recettes WHERE id = ?", (l["recette_id"],)).fetchone()
            if l["recette_id"] else None, lot=l)
        apercus_lots[l["id"]] = e["ingredients"] + (f" Contient : {e['allergenes']}."
                                                    if e["allergenes"] else "")
    return render_template("etiquettes.html", fiches=fiches, lots=lots, conf=settings(),
                           apercus_lots=apercus_lots,
                           choisie=to_int(request.args.get("recette")))


@app.route("/etiquettes/recette/<int:recette_id>", methods=["POST"])
def etiquette_enregistrer(recette_id):
    conn = get_db()
    get_or_404("recettes", recette_id)
    f = request.form
    auto = ingredients_recette(conn, recette_id)[0]
    texte = f.get("etiquette_ingredients", "").strip()
    personnalisee = f.get("action") != "auto" and texte and texte != auto
    conn.execute(
        "UPDATE recettes SET denomination = ?, etiquette_ingredients = ?, allergenes = ?,"
        " etiquette_mentions = ? WHERE id = ?",
        (f.get("denomination", "").strip() or None, texte if personnalisee else None,
         f.get("allergenes", "").strip(), f.get("etiquette_mentions", "").strip() or None,
         recette_id))
    conn.commit()
    flash("Étiquette enregistrée" + (" (liste d'ingrédients personnalisée)." if personnalisee
                                     else " : la liste d'ingrédients suit automatiquement la recette."),
          "succes")
    return redirect(url_for("etiquettes", recette=recette_id) + f"#recette-{recette_id}")


@app.route("/etiquettes/reglages", methods=["POST"])
def etiquettes_reglages():
    set_setting("etiquette_largeur", str(min(max(to_float(request.form.get("largeur"), 70), 30), 190)))
    set_setting("etiquette_hauteur", str(min(max(to_float(request.form.get("hauteur"), 100), 30), 270)))
    set_setting("etiquette_tri", request.form.get("tri", "").strip())
    get_db().commit()
    flash("Format d'étiquette enregistré.", "succes")
    return redirect(url_for("etiquettes"))


def _reponse(e):
    conf = settings()
    pdf = etiquettes_pdf(
        e, to_float(conf.get("etiquette_largeur"), 70), to_float(conf.get("etiquette_hauteur"), 100),
        copies=min(max(to_int(request.args.get("copies"), 1), 1), 500),
        planche=request.args.get("format") != "unite")
    nom = "".join(ch if ch.isalnum() else "-" for ch in e["nom"])[:40]
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="Etiquette-{nom}.pdf"'})


@app.route("/etiquettes/recette/<int:recette_id>.pdf")
def etiquette_recette_pdf(recette_id):
    recette = get_or_404("recettes", recette_id)
    return _reponse(donnees_etiquette(get_db(), recette=recette))


@app.route("/etiquettes/lot/<int:lot_id>.pdf")
def etiquette_lot_pdf(lot_id):
    conn = get_db()
    lot = get_or_404("lots", lot_id)
    recette = conn.execute("SELECT * FROM recettes WHERE id = ?", (lot["recette_id"],)).fetchone() \
        if lot["recette_id"] else None
    return _reponse(donnees_etiquette(conn, recette=recette, lot=lot))
