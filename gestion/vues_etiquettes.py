"""Module 5 — contre-étiquettes réglementaires par recette ou par lot."""
from flask import Response, flash, redirect, render_template, request, url_for

from calculs import convertir, to_float
from noyau import app, get_db, get_or_404, nombre, set_setting, settings, to_int
from etiquette_pdf import etiquettes_pdf



def ingredients_proposes(conn, recette_id):
    """Liste d'ingrédients par ordre décroissant de quantité (à relire avant impression)."""
    rows = conn.execute(
        "SELECT i.*, m.allergene FROM recette_ingredients i"
        " LEFT JOIN matieres_premieres m ON m.id = i.mp_id WHERE i.recette_id = ?",
        (recette_id,)).fetchall()

    def poids(i):
        # Approximation : 1 L ≈ 1 kg ; les pièces (gousses, citrons) passent en fin de liste.
        for unite in ("g", "ml"):
            q = convertir(i["quantite_par_litre"] or 0, i["unite"], unite)
            if q is not None:
                return q
        return -1

    noms = []
    for i in sorted(rows, key=poids, reverse=True):
        nom = i["nom"].split("(")[0].strip()
        noms.append(nom[0].lower() + nom[1:] if len(nom) > 1 and not nom[1].isupper() else nom)
    texte = ", ".join(noms)
    allergenes = sorted({i["allergene"] for i in rows if i["allergene"]})
    return (texte[0].upper() + texte[1:] + "." if texte else ""), ", ".join(allergenes)


def donnees_etiquette(conn, recette=None, lot=None):
    conf = settings()
    nom = (recette["nom"] if recette else None) or (lot["recette_nom"] if lot else "")
    proposes = ingredients_proposes(conn, recette["id"]) if recette else ("", "")
    degre = (lot["degre"] if lot and lot["degre"] is not None else None) \
        or (recette["degre"] if recette else None)
    volume = lot["volume_cl"] if lot else to_int(request.args.get("volume"), 50) or 50
    return {
        "nom": nom,
        "denomination": (recette["denomination"] if recette and recette["denomination"]
                         else f"Rhum arrangé {nom}"),
        "ingredients": (recette["etiquette_ingredients"] if recette and
                        recette["etiquette_ingredients"] else proposes[0]),
        "allergenes": (recette["allergenes"] if recette and recette["allergenes"] is not None
                       else proposes[1]),
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
        proposes = ingredients_proposes(conn, r["id"])
        fiches.append({"r": r, "ingredients_proposes": proposes[0],
                       "allergenes_proposes": proposes[1]})
    return render_template("etiquettes.html", fiches=fiches, lots=lots, conf=settings(),
                           choisie=to_int(request.args.get("recette")))


@app.route("/etiquettes/recette/<int:recette_id>", methods=["POST"])
def etiquette_enregistrer(recette_id):
    get_or_404("recettes", recette_id)
    f = request.form
    get_db().execute(
        "UPDATE recettes SET denomination = ?, etiquette_ingredients = ?, allergenes = ?,"
        " etiquette_mentions = ? WHERE id = ?",
        (f.get("denomination", "").strip() or None, f.get("etiquette_ingredients", "").strip() or None,
         f.get("allergenes", "").strip(), f.get("etiquette_mentions", "").strip() or None,
         recette_id))
    get_db().commit()
    flash("Textes de l'étiquette enregistrés.", "succes")
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
