"""Module 2 — bibliothèque de recettes."""
from flask import flash, redirect, render_template, request, url_for

from calculs import CATEGORIES_INGREDIENTS, PERTE_DEFAUT, convertir, to_float
from noyau import app, get_db, get_or_404, settings, to_int


def cout_unitaire_estime(ing):
    """Prix par unité de la recette : celui du stock (dernier achat) s'il est relié, sinon saisi."""
    if ing["mp_id"] and ing["cout_mp"]:
        facteur = convertir(1, ing["unite"], ing["unite_mp"])
        if facteur is not None:
            return ing["cout_mp"] * facteur
    return ing["cout_unitaire"]


def details_recette(conn, recette):
    """Ingrédients et coût estimé d'une recette (pour 1 L mis en macération)."""
    ingredients = conn.execute(
        "SELECT i.*, m.cout_unitaire AS cout_mp, m.unite AS unite_mp, m.allergene,"
        " COALESCE((SELECT SUM(quantite) FROM mouvements_mp v WHERE v.mp_id = m.id), 0) AS stock_mp"
        " FROM recette_ingredients i LEFT JOIN matieres_premieres m ON m.id = i.mp_id"
        " WHERE i.recette_id = ? ORDER BY "
        "CASE i.categorie WHEN 'rhum' THEN 0 WHEN 'fruit' THEN 1 WHEN 'epice' THEN 2 "
        "WHEN 'sucre' THEN 3 ELSE 4 END, i.id",
        (recette["id"],),
    ).fetchall()
    ingredients = [dict(i, cout_estime=cout_unitaire_estime(i)) for i in ingredients]
    cout_litre = sum((i["quantite_par_litre"] or 0) * (i["cout_estime"] or 0) for i in ingredients)
    complet = all(i["cout_estime"] for i in ingredients) and bool(ingredients)
    nb_lots = conn.execute("SELECT COUNT(*) FROM lots WHERE recette_id = ?",
                           (recette["id"],)).fetchone()[0]
    return {"ingredients": ingredients, "cout_litre": cout_litre, "complet": complet,
            "nb_lots": nb_lots}


def cout_materiaux_bouteille(conn):
    return conn.execute(
        "SELECT COALESCE(SUM(cout_unitaire), 0) FROM materiaux WHERE par_bouteille = 1"
    ).fetchone()[0]


def _contexte_formulaire(conn):
    from vues_matieres import repertoire_ingredients
    return {"repertoire": repertoire_ingredients(),
            "materiaux": cout_materiaux_bouteille(conn)}


def rendement(recette):
    """Part du volume mis en macération qui finit en bouteille."""
    perte = recette["perte_pct"] if recette["perte_pct"] is not None else PERTE_DEFAUT
    return 1 - perte / 100


@app.route("/recettes")
def recettes():
    conn = get_db()
    rows = conn.execute("SELECT * FROM recettes ORDER BY nom").fetchall()
    return render_template(
        "recettes.html",
        recettes=[(r, details_recette(conn, r)) for r in rows],
        materiaux=cout_materiaux_bouteille(conn), rendement=rendement,
    )


def enregistrer_ingredients(conn, recette_id, form):
    """Chaque ligne vient du répertoire (ing_mp) ou est saisie librement (hors répertoire)."""
    conn.execute("DELETE FROM recette_ingredients WHERE recette_id = ?", (recette_id,))
    noms = form.getlist("ing_nom")
    mps = form.getlist("ing_mp")
    mps += [""] * (len(noms) - len(mps))  # lignes sans choix de répertoire
    lignes = zip(mps, form.getlist("ing_categorie"), noms,
                 form.getlist("ing_qte"), form.getlist("ing_unite"), form.getlist("ing_cout"))
    for mp_id, categorie, nom, qte, unite, cout in lignes:
        mp = conn.execute("SELECT * FROM matieres_premieres WHERE id = ?",
                          (to_int(mp_id),)).fetchone() if to_int(mp_id) else None
        if mp:
            nom, categorie, cout = mp["nom"], mp["categorie"], None  # prix : celui du stock
            unite = unite.strip() or mp["unite"]
        if not nom.strip():
            continue
        conn.execute(
            "INSERT INTO recette_ingredients (recette_id, categorie, nom, quantite_par_litre,"
            " unite, cout_unitaire, mp_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (recette_id, categorie if categorie in CATEGORIES_INGREDIENTS else "autre",
             nom.strip(), to_float(qte, None), unite.strip(), to_float(cout, None),
             mp["id"] if mp else None),
        )
    # Lignes libres : reliées au répertoire si un ingrédient porte le même nom
    conn.execute(
        """UPDATE recette_ingredients SET mp_id = (SELECT m.id FROM matieres_premieres m
           WHERE lower(m.nom) = lower(recette_ingredients.nom))
           WHERE recette_id = ? AND mp_id IS NULL""",
        (recette_id,))


def lire_recette(form):
    return {
        "nom": form.get("nom", "").strip(),
        "duree_maceration_jours": max(to_int(form.get("duree_maceration_jours"), 60), 0),
        "degre": to_float(form.get("degre"), None),
        "notes_degustation": form.get("notes_degustation", "").strip(),
        "instructions": form.get("instructions", "").strip(),
        "perte_pct": min(max(to_float(form.get("perte_pct"), PERTE_DEFAUT), 0), 95),
    }


@app.route("/recettes/nouvelle", methods=["GET", "POST"])
def recette_nouvelle():
    conn = get_db()
    if request.method == "POST":
        data = lire_recette(request.form)
        if not data["nom"]:
            flash("Le nom de la recette est obligatoire.", "erreur")
        else:
            cur = conn.execute(
                """INSERT INTO recettes (nom, duree_maceration_jours, degre, notes_degustation,
                   instructions, perte_pct) VALUES (:nom, :duree_maceration_jours, :degre,
                   :notes_degustation, :instructions, :perte_pct)""", data)
            enregistrer_ingredients(conn, cur.lastrowid, request.form)
            conn.commit()
            flash(f"Recette « {data['nom']} » créée.", "succes")
            return redirect(url_for("recettes") + f"#recette-{cur.lastrowid}")
    return render_template("recette_form.html",
                           recette={"duree_maceration_jours": 60, "perte_pct": PERTE_DEFAUT},
                           ingredients=[], nouveau=True, **_contexte_formulaire(conn))


@app.route("/recettes/<int:recette_id>/modifier", methods=["GET", "POST"])
def recette_modifier(recette_id):
    conn = get_db()
    recette = get_or_404("recettes", recette_id)
    if request.method == "POST":
        data = lire_recette(request.form)
        if not data["nom"]:
            flash("Le nom de la recette est obligatoire.", "erreur")
        else:
            conn.execute(
                """UPDATE recettes SET nom = :nom, duree_maceration_jours = :duree_maceration_jours,
                   degre = :degre, notes_degustation = :notes_degustation,
                   instructions = :instructions, perte_pct = :perte_pct WHERE id = :id""",
                {**data, "id": recette_id})
            enregistrer_ingredients(conn, recette_id, request.form)
            conn.commit()
            flash("Recette mise à jour.", "succes")
            return redirect(url_for("recettes") + f"#recette-{recette_id}")
    return render_template("recette_form.html", recette=recette,
                           ingredients=details_recette(conn, recette)["ingredients"],
                           nouveau=False, **_contexte_formulaire(conn))


@app.route("/recettes/<int:recette_id>/dupliquer", methods=["POST"])
def recette_dupliquer(recette_id):
    """Nouvelle recette à partir d'une existante (variante, nouvel assemblage)."""
    conn = get_db()
    r = get_or_404("recettes", recette_id)
    cur = conn.execute(
        """INSERT INTO recettes (nom, duree_maceration_jours, degre, notes_degustation,
           instructions, perte_pct) VALUES (?, ?, ?, ?, ?, ?)""",
        (f"{r['nom']} (variante)", r["duree_maceration_jours"], r["degre"],
         r["notes_degustation"], r["instructions"], r["perte_pct"]))
    conn.execute(
        """INSERT INTO recette_ingredients (recette_id, categorie, nom, quantite_par_litre, unite,
           cout_unitaire, mp_id) SELECT ?, categorie, nom, quantite_par_litre, unite,
           cout_unitaire, mp_id FROM recette_ingredients WHERE recette_id = ? ORDER BY id""",
        (cur.lastrowid, recette_id))
    conn.commit()
    flash(f"Copie de « {r['nom']} » créée : renommez-la et ajustez l'assemblage.", "succes")
    return redirect(url_for("recette_modifier", recette_id=cur.lastrowid))


@app.route("/recettes/<int:recette_id>/supprimer", methods=["POST"])
def recette_supprimer(recette_id):
    conn = get_db()
    recette = get_or_404("recettes", recette_id)
    conn.execute("DELETE FROM recettes WHERE id = ?", (recette_id,))
    conn.commit()
    flash(f"Recette « {recette['nom']} » supprimée. Les lots déjà produits sont conservés.",
          "succes")
    return redirect(url_for("recettes"))


@app.route("/recettes/<int:recette_id>/fiche")
def recette_fiche(recette_id):
    conn = get_db()
    recette = get_or_404("recettes", recette_id)
    litres = max(to_float(request.args.get("litres"), 10), 0.1)
    return render_template(
        "recette_fiche.html", recette=recette, d=details_recette(conn, recette),
        litres=litres, conf=settings(), materiaux=cout_materiaux_bouteille(conn),
        rendement=rendement(recette),
    )
