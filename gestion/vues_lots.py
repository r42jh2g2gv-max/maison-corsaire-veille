"""Module 1 (registre des lots), module 3 (calculateur) et stock."""
from datetime import date, datetime

from flask import abort, flash, redirect, render_template, request, url_for

from calculs import (CATEGORIES_INGREDIENTS, STATUTS, STATUTS_EMBOUTEILLES,
                     TYPES_MATERIAUX, cout_revient, taux_tva, to_float)
from vues_matieres import (cout_depuis_stock, matieres_avec_stock, synchroniser_utilisation,
                           trouver_mp)
from noyau import (app, couts_par_lot, get_db, get_lot, lots_avec_stock, maj_statut_epuise,
                   parse_date, settings, stock_lot, to_int, today)


def numero_lot(conn):
    prefix = f"MC-{date.today().year}-"
    row = conn.execute(
        "SELECT numero FROM lots WHERE numero LIKE ? ORDER BY numero DESC LIMIT 1",
        (prefix + "%",),
    ).fetchone()
    seq = to_int(row["numero"].rsplit("-", 1)[1]) + 1 if row else 1
    return f"{prefix}{seq:03d}"


def synchroniser_materiaux(conn, lot_id):
    """Déduit (ou restitue) bouteilles, bouchons, étiquettes... selon le lot.

    Les matières sont consommées dès qu'un lot est embouteillé ; si l'on
    corrige le nombre de bouteilles ou que l'on revient en arrière sur le
    statut, la différence est réintégrée au stock.
    """
    lot = conn.execute("SELECT * FROM lots WHERE id = ?", (lot_id,)).fetchone()
    voulu = lot["nb_bouteilles"] if lot["statut"] in STATUTS_EMBOUTEILLES else 0
    delta = voulu - lot["materiaux_deduits"]
    if delta:
        conn.execute("UPDATE materiaux SET stock = stock - ? WHERE par_bouteille = 1", (delta,))
        conn.execute("UPDATE lots SET materiaux_deduits = ? WHERE id = ?", (voulu, lot_id))
    return delta



@app.route("/lots")
def lots():
    statut = request.args.get("statut", "")
    if statut in STATUTS:
        rows = lots_avec_stock("WHERE l.statut = ? ORDER BY l.numero DESC", (statut,))
    else:
        statut = ""
        rows = lots_avec_stock("ORDER BY l.numero DESC")
    compte = {k: 0 for k in STATUTS}
    for r in get_db().execute("SELECT statut, COUNT(*) n FROM lots GROUP BY statut"):
        compte[r["statut"]] = r["n"]
    return render_template("lots.html", lots=rows, statut=statut, compte=compte,
                           stock_lot=stock_lot)


def lire_formulaire_lot(form):
    return {
        "recette_id": to_int(form.get("recette_id")) or None,
        "recette_nom": form.get("recette_nom", "").strip(),
        "date_maceration": parse_date(form.get("date_maceration")),
        "date_embouteillage": parse_date(form.get("date_embouteillage")),
        "dlc": parse_date(form.get("dlc")),
        "nb_bouteilles": max(to_int(form.get("nb_bouteilles")), 0),
        "volume_cl": max(to_int(form.get("volume_cl"), 50), 1),
        "degre": to_float(form.get("degre"), None),
        "statut": form.get("statut") if form.get("statut") in STATUTS else "maceration",
        "notes": form.get("notes", "").strip(),
    }


@app.route("/lots/nouveau", methods=["GET", "POST"])
def lot_nouveau():
    conn = get_db()
    recettes = conn.execute("SELECT * FROM recettes ORDER BY nom").fetchall()
    if request.method == "POST":
        data = lire_formulaire_lot(request.form)
        if data["recette_id"] and not data["recette_nom"]:
            r = conn.execute("SELECT nom FROM recettes WHERE id = ?", (data["recette_id"],)).fetchone()
            data["recette_nom"] = r["nom"] if r else ""
        if not data["recette_nom"]:
            flash("Indiquez une recette (ou un nom de produit).", "erreur")
            return render_template("lot_form.html", lot=data, recettes=recettes,
                                   numero=numero_lot(conn), nouveau=True)
        numero = numero_lot(conn)
        cur = conn.execute(
            """INSERT INTO lots (numero, recette_id, recette_nom, date_maceration,
               date_embouteillage, dlc, nb_bouteilles, volume_cl, degre, statut, notes, created_at)
               VALUES (:numero, :recette_id, :recette_nom, :date_maceration, :date_embouteillage,
               :dlc, :nb_bouteilles, :volume_cl, :degre, :statut, :notes, :created_at)""",
            {**data, "numero": numero, "created_at": datetime.now().isoformat(timespec="seconds")},
        )
        lot_id = cur.lastrowid
        # Pré-remplit les ingrédients à partir de la recette (quantités pour 1 L)
        litres = to_float(request.form.get("litres"), 0)
        if data["recette_id"] and litres > 0:
            for ing in conn.execute(
                "SELECT * FROM recette_ingredients WHERE recette_id = ?", (data["recette_id"],)
            ).fetchall():
                quantite = round((ing["quantite_par_litre"] or 0) * litres, 3)
                mp = trouver_mp(conn, ing["nom"])
                mp_id = ing["mp_id"] or (mp["id"] if mp else None)
                cout = cout_depuis_stock(conn, mp_id, quantite, ing["unite"]) if mp_id else None
                if cout is None:
                    cout = round(quantite * (ing["cout_unitaire"] or 0), 2)
                ligne = conn.execute(
                    "INSERT INTO lot_ingredients (lot_id, categorie, nom, quantite, unite, cout, mp_id)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (lot_id, ing["categorie"], ing["nom"], quantite, ing["unite"], cout, mp_id),
                )
                erreur = synchroniser_utilisation(conn, ligne.lastrowid)
                if erreur:
                    flash(f"{ing['nom']} : {erreur}, stock non déduit.", "erreur")
        synchroniser_materiaux(conn, lot_id)
        conn.commit()
        flash(f"Lot {numero} créé. Les ingrédients ont été déduits du stock de matières premières.", "succes")
        return redirect(url_for("lot_detail", lot_id=lot_id))

    lot = {"date_maceration": today(), "volume_cl": 50, "statut": "maceration",
           "nb_bouteilles": 0}
    recette_id = to_int(request.args.get("recette_id"))
    if recette_id:
        r = conn.execute("SELECT * FROM recettes WHERE id = ?", (recette_id,)).fetchone()
        if r:
            lot.update(recette_id=r["id"], recette_nom=r["nom"], degre=r["degre"])
    return render_template("lot_form.html", lot=lot, recettes=recettes,
                           numero=numero_lot(conn), nouveau=True)


@app.route("/lots/<int:lot_id>")
def lot_detail(lot_id):
    conn = get_db()
    lot = get_lot(lot_id)
    conf = settings()
    ingredients = conn.execute(
        "SELECT * FROM lot_ingredients WHERE lot_id = ? ORDER BY "
        "CASE categorie WHEN 'rhum' THEN 0 WHEN 'fruit' THEN 1 WHEN 'epice' THEN 2 "
        "WHEN 'sucre' THEN 3 ELSE 4 END, id",
        (lot_id,),
    ).fetchall()
    ventes = conn.execute(
        "SELECT * FROM ventes WHERE lot_id = ? ORDER BY date_vente DESC", (lot_id,)
    ).fetchall()
    duree = None
    if lot["recette_id"]:
        r = conn.execute("SELECT duree_maceration_jours FROM recettes WHERE id = ?",
                         (lot["recette_id"],)).fetchone()
        duree = r["duree_maceration_jours"] if r else None
    jours_maceration = None
    if lot["date_maceration"]:
        fin = date.fromisoformat(lot["date_embouteillage"]) if lot["date_embouteillage"] else date.today()
        jours_maceration = (fin - date.fromisoformat(lot["date_maceration"])).days
    return render_template(
        "lot_detail.html", matieres=matieres_avec_stock("ORDER BY m.nom"), lot=lot,
        ingredients=ingredients, ventes=ventes,
        cout=cout_revient(conn, lot, conf), stock=stock_lot(lot),
        duree=duree, jours_maceration=jours_maceration,
    )


@app.route("/lots/<int:lot_id>/modifier", methods=["GET", "POST"])
def lot_modifier(lot_id):
    conn = get_db()
    lot = get_lot(lot_id)
    recettes = conn.execute("SELECT * FROM recettes ORDER BY nom").fetchall()
    if request.method == "POST":
        data = lire_formulaire_lot(request.form)
        if not data["recette_nom"]:
            flash("Le nom de la recette est obligatoire.", "erreur")
            return render_template("lot_form.html", lot={**dict(lot), **data},
                                   recettes=recettes, numero=lot["numero"], nouveau=False)
        if data["nb_bouteilles"] < lot["vendu"]:
            flash(f"{lot['vendu']} bouteilles de ce lot ont déjà été vendues : "
                  "le nombre de bouteilles ne peut pas être inférieur.", "erreur")
            return render_template("lot_form.html", lot={**dict(lot), **data},
                                   recettes=recettes, numero=lot["numero"], nouveau=False)
        conn.execute(
            """UPDATE lots SET recette_id = :recette_id, recette_nom = :recette_nom,
               date_maceration = :date_maceration, date_embouteillage = :date_embouteillage,
               dlc = :dlc, nb_bouteilles = :nb_bouteilles, volume_cl = :volume_cl,
               degre = :degre, statut = :statut, notes = :notes WHERE id = :id""",
            {**data, "id": lot_id},
        )
        conn.execute(
            """UPDATE mouvements_mp SET date_mouvement = ? WHERE lot_ingredient_id IN
               (SELECT id FROM lot_ingredients WHERE lot_id = ?)""",
            (data["date_maceration"] or today(), lot_id))
        alerte_materiaux(conn, lot_id)
        maj_statut_epuise(conn, lot_id)
        conn.commit()
        flash("Lot mis à jour.", "succes")
        return redirect(url_for("lot_detail", lot_id=lot_id))
    return render_template("lot_form.html", lot=lot, recettes=recettes,
                           numero=lot["numero"], nouveau=False)


def alerte_materiaux(conn, lot_id):
    delta = synchroniser_materiaux(conn, lot_id)
    if delta > 0:
        flash(f"{delta} unités de chaque matière (bouteille, bouchon, étiquette…) "
              "ont été déduites du stock.", "info")
    elif delta < 0:
        flash(f"{-delta} unités de chaque matière ont été réintégrées au stock.", "info")
    manquants = conn.execute(
        "SELECT nom FROM materiaux WHERE par_bouteille = 1 AND stock < 0"
    ).fetchall()
    if manquants:
        flash("Stock de matières négatif : " + ", ".join(m["nom"] for m in manquants)
              + ". Pensez à corriger le stock.", "erreur")


@app.route("/lots/<int:lot_id>/statut", methods=["POST"])
def lot_statut(lot_id):
    conn = get_db()
    lot = get_lot(lot_id)
    statut = request.form.get("statut")
    if statut not in STATUTS:
        abort(400)
    if statut in STATUTS_EMBOUTEILLES and lot["nb_bouteilles"] <= 0:
        flash("Renseignez d'abord le nombre de bouteilles produites.", "erreur")
        return redirect(url_for("lot_modifier", lot_id=lot_id))
    conn.execute("UPDATE lots SET statut = ? WHERE id = ?", (statut, lot_id))
    if statut == "embouteille" and not lot["date_embouteillage"]:
        conn.execute("UPDATE lots SET date_embouteillage = ? WHERE id = ?", (today(), lot_id))
    alerte_materiaux(conn, lot_id)
    conn.commit()
    flash(f"Statut du lot : {STATUTS[statut]}.", "succes")
    return redirect(url_for("lot_detail", lot_id=lot_id))


@app.route("/lots/<int:lot_id>/supprimer", methods=["POST"])
def lot_supprimer(lot_id):
    conn = get_db()
    lot = get_lot(lot_id)
    if lot["vendu"]:
        flash("Ce lot a des ventes enregistrées : supprimez-les d'abord "
              "(la traçabilité doit être conservée).", "erreur")
        return redirect(url_for("lot_detail", lot_id=lot_id))
    conn.execute("UPDATE lots SET statut = 'maceration' WHERE id = ?", (lot_id,))
    synchroniser_materiaux(conn, lot_id)
    conn.execute("DELETE FROM lots WHERE id = ?", (lot_id,))
    conn.commit()
    flash(f"Lot {lot['numero']} supprimé.", "succes")
    return redirect(url_for("lots"))


@app.route("/lots/<int:lot_id>/ingredients", methods=["POST"])
def ingredient_ajouter(lot_id):
    conn = get_db()
    get_lot(lot_id)
    mp_id = to_int(request.form.get("mp_id")) or None
    mp = conn.execute("SELECT * FROM matieres_premieres WHERE id = ?", (mp_id,)).fetchone() \
        if mp_id else None
    nom = mp["nom"] if mp else request.form.get("nom", "").strip()
    categorie = mp["categorie"] if mp else request.form.get("categorie")
    quantite = to_float(request.form.get("quantite"), None)
    unite = request.form.get("unite", "").strip() or (mp["unite"] if mp else "")
    if not nom or categorie not in CATEGORIES_INGREDIENTS:
        flash("Choisissez une matière première ou indiquez le nom et la catégorie.", "erreur")
        return redirect(url_for("lot_detail", lot_id=lot_id) + "#ingredients")
    cout = request.form.get("cout", "").strip()
    cout = to_float(cout) if cout else (cout_depuis_stock(conn, mp_id, quantite, unite) or 0)
    cur = conn.execute(
        "INSERT INTO lot_ingredients (lot_id, categorie, nom, quantite, unite, cout, mp_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (lot_id, categorie, nom, quantite, unite, cout, mp_id),
    )
    erreur = synchroniser_utilisation(conn, cur.lastrowid)
    conn.commit()
    if erreur:
        flash(f"Ingrédient ajouté, mais {erreur} : stock non déduit.", "erreur")
    else:
        flash(f"Ingrédient « {nom} » ajouté{' et déduit du stock' if mp else ''}.", "succes")
    return redirect(url_for("lot_detail", lot_id=lot_id) + "#ingredients")


@app.route("/lots/<int:lot_id>/ingredients/<int:ing_id>", methods=["POST"])
def ingredient_modifier(lot_id, ing_id):
    conn = get_db()
    if request.form.get("action") == "supprimer":
        # La sortie de stock liée est supprimée en cascade : la quantité revient en stock.
        conn.execute("DELETE FROM lot_ingredients WHERE id = ? AND lot_id = ?", (ing_id, lot_id))
        flash("Ingrédient retiré (quantité remise en stock si elle venait du stock).", "succes")
    else:
        conn.execute(
            "UPDATE lot_ingredients SET quantite = ?, unite = ?, cout = ? WHERE id = ? AND lot_id = ?",
            (to_float(request.form.get("quantite"), None), request.form.get("unite", "").strip(),
             to_float(request.form.get("cout")), ing_id, lot_id),
        )
        erreur = synchroniser_utilisation(conn, ing_id)
        flash(f"Ingrédient mis à jour, mais {erreur}." if erreur else "Ingrédient mis à jour.",
              "erreur" if erreur else "succes")
    conn.commit()
    return redirect(url_for("lot_detail", lot_id=lot_id) + "#ingredients")


@app.route("/lots/<int:lot_id>/fiche")
def lot_fiche(lot_id):
    conn = get_db()
    lot = get_lot(lot_id)
    conf = settings()
    ingredients = conn.execute(
        "SELECT * FROM lot_ingredients WHERE lot_id = ? ORDER BY id", (lot_id,)
    ).fetchall()
    ventes = conn.execute(
        "SELECT * FROM ventes WHERE lot_id = ? ORDER BY date_vente", (lot_id,)
    ).fetchall()
    return render_template(
        "lot_fiche.html", lot=lot, ingredients=ingredients, ventes=ventes, conf=conf,
        cout=cout_revient(conn, lot, conf), stock=stock_lot(lot),
        edition=datetime.now().strftime("%d/%m/%Y à %H:%M"),
    )


# --------------------------------------------------------------------------
# Module 3 — Calculateur de coût et de prix
# --------------------------------------------------------------------------

@app.route("/calculateur")
def calculateur():
    conn = get_db()
    conf = settings()
    lots = lots_avec_stock("ORDER BY l.numero DESC")
    lot_id = to_int(request.args.get("lot_id")) or (lots[0]["id"] if lots else 0)
    lot = next((l for l in lots if l["id"] == lot_id), None)
    cout = cout_revient(conn, lot, conf) if lot else None
    return render_template(
        "calculateur.html", lots=lots, lot=lot, cout=cout, conf=conf,
        tva=taux_tva(conf),
    )


@app.route("/calculateur/enregistrer", methods=["POST"])
def calculateur_enregistrer():
    conn = get_db()
    lot_id = to_int(request.form.get("lot_id"))
    get_lot(lot_id)
    conn.execute(
        "UPDATE lots SET prix_vente_ttc = ?, prix_revendeur_ht = ? WHERE id = ?",
        (round(to_float(request.form.get("prix_vente_ttc")), 2),
         round(to_float(request.form.get("prix_revendeur_ht")), 2), lot_id),
    )
    for key in ("marge_direct", "marge_revendeur", "coef_revendeur"):
        if request.form.get(key):
            conn.execute("UPDATE settings SET value = ? WHERE key = ?",
                         (str(to_float(request.form.get(key))), key))
    conn.commit()
    flash("Prix enregistrés pour ce lot : ils seront proposés lors des ventes.", "succes")
    return redirect(url_for("calculateur", lot_id=lot_id))


# --------------------------------------------------------------------------
# Module 4 — Stock et ventes
# --------------------------------------------------------------------------

@app.route("/stock")
def stock():
    conn = get_db()
    conf = settings()
    lots = lots_avec_stock(
        "WHERE l.statut IN ('embouteille', 'epuise') ORDER BY l.statut, l.numero DESC")
    couts = couts_par_lot(conn, conf)
    materiaux = conn.execute("SELECT * FROM materiaux ORDER BY type, nom").fetchall()
    capacite = min((m["stock"] for m in materiaux if m["par_bouteille"]), default=0)
    a_venir = conn.execute(
        "SELECT COALESCE(SUM(nb_bouteilles), 0) FROM lots WHERE statut IN ('maceration', 'pret')"
    ).fetchone()[0]
    return render_template("stock.html", lots=lots, materiaux=materiaux, couts=couts,
                           stock_lot=stock_lot, capacite=max(capacite, 0), a_venir=a_venir)


def lire_formulaire_materiau(form):
    return (
        form.get("nom", "").strip(),
        form.get("type") if form.get("type") in TYPES_MATERIAUX else "autre",
        to_int(form.get("stock")),
        max(to_int(form.get("seuil_alerte")), 0),
        max(to_float(form.get("cout_unitaire")), 0),
        1 if form.get("par_bouteille") else 0,
    )


@app.route("/materiaux", methods=["POST"])
def materiau_ajouter():
    data = lire_formulaire_materiau(request.form)
    if not data[0]:
        flash("Le nom de la matière est obligatoire.", "erreur")
    else:
        get_db().execute(
            "INSERT INTO materiaux (nom, type, stock, seuil_alerte, cout_unitaire, par_bouteille)"
            " VALUES (?, ?, ?, ?, ?, ?)", data)
        get_db().commit()
        flash(f"Matière « {data[0]} » ajoutée.", "succes")
    return redirect(url_for("stock") + "#materiaux")


@app.route("/materiaux/<int:mat_id>", methods=["POST"])
def materiau_modifier(mat_id):
    conn = get_db()
    action = request.form.get("action")
    mat = conn.execute("SELECT * FROM materiaux WHERE id = ?", (mat_id,)).fetchone()
    if not mat:
        abort(404)
    if action == "supprimer":
        conn.execute("DELETE FROM materiaux WHERE id = ?", (mat_id,))
        flash(f"« {mat['nom']} » supprimé.", "succes")
    elif action == "reception":
        qte = to_int(request.form.get("quantite"))
        conn.execute("UPDATE materiaux SET stock = stock + ? WHERE id = ?", (qte, mat_id))
        flash(f"Stock « {mat['nom']} » : {qte:+d} → {mat['stock'] + qte}.", "succes")
    else:
        data = lire_formulaire_materiau(request.form)
        if not data[0]:
            flash("Le nom de la matière est obligatoire.", "erreur")
        else:
            conn.execute(
                "UPDATE materiaux SET nom = ?, type = ?, stock = ?, seuil_alerte = ?,"
                " cout_unitaire = ?, par_bouteille = ? WHERE id = ?", (*data, mat_id))
            flash(f"« {data[0]} » mis à jour.", "succes")
    conn.commit()
    return redirect(url_for("stock") + "#materiaux")
