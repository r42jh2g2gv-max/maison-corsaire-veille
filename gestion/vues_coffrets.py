"""Coffrets : plusieurs bouteilles vendues (ou offertes) en un seul article."""
from flask import flash, redirect, render_template, request, url_for

from calculs import to_float
from noyau import app, get_db, get_or_404, lots_avec_stock, stock_lot, to_int


def choisir_lots(conn, recette_id, volume_cl, quantite, forcer=False):
    """Bouteilles à prendre pour une recette et une contenance : les plus anciens lots d'abord.
    Retourne [(lot_id, quantité)] ou None si le stock ne suffit pas (sauf forcer=True)."""
    lots = [l for l in lots_avec_stock(
        """WHERE l.recette_id = ? AND l.volume_cl = ? AND l.statut IN ('embouteille', 'epuise')
           ORDER BY COALESCE(l.date_embouteillage, l.created_at), l.id""",
        (recette_id, volume_cl))]
    choix, reste = [], quantite
    for l in lots:
        q = min(stock_lot(l), reste)
        if q > 0:
            choix.append((l["id"], q))
            reste -= q
        if not reste:
            return choix
    if forcer and lots:  # vente déjà faite hors ligne : on l'impute au lot le plus récent
        choix.append((lots[-1]["id"], reste))
        return choix
    return None


def elements(conn, coffret_id):
    return conn.execute(
        """SELECT e.*, r.nom AS recette_nom FROM coffret_elements e
           LEFT JOIN recettes r ON r.id = e.recette_id WHERE e.coffret_id = ? ORDER BY e.id""",
        (coffret_id,)).fetchall()


def disponibles(conn, coffret_id):
    """Nombre de coffrets réalisables avec le stock actuel."""
    els = elements(conn, coffret_id)
    if not els:
        return 0
    possibles = []
    for e in els:
        stock = sum(stock_lot(l) for l in lots_avec_stock(
            "WHERE l.recette_id = ? AND l.volume_cl = ? AND l.statut = 'embouteille'",
            (e["recette_id"], e["volume_cl"])))
        possibles.append(stock // max(e["quantite"], 1))
    return min(possibles)


def composer(conn, coffret_id, nombre, prix_total, forcer=False):
    """Détaille la vente de `nombre` coffrets en lignes (lot, quantité, prix unitaire).
    Le prix du coffret est réparti au prorata du prix de chaque bouteille."""
    els = elements(conn, coffret_id)
    lignes = []
    for e in els:
        choix = choisir_lots(conn, e["recette_id"], e["volume_cl"], e["quantite"] * nombre, forcer)
        if choix is None:
            return None, f"Stock insuffisant pour {e['recette_nom']} {e['volume_cl']} cl."
        for lot_id, q in choix:
            lot = lots_avec_stock("WHERE l.id = ?", (lot_id,))[0]
            lignes.append([lot_id, q, lot["prix_vente_ttc"] or e["volume_cl"] / 50 * 30])
    poids = sum(q * p for _, q, p in lignes) or 1
    for ligne in lignes:  # prix de chaque bouteille dans le coffret
        ligne[2] = round(prix_total * ligne[2] / poids, 2)
    ecart = round(prix_total * nombre - sum(q * p for _, q, p in lignes), 2)
    if ecart and lignes:  # arrondi reporté sur la dernière ligne d'une bouteille
        dernier = lignes[-1]
        if dernier[1] == 1:
            dernier[2] = round(dernier[2] + ecart, 2)
        else:
            dernier[1] -= 1
            lignes.append([dernier[0], 1, round(dernier[2] + ecart, 2)])
    return [tuple(l) for l in lignes], None


@app.route("/coffrets")
def coffrets():
    conn = get_db()
    liste = conn.execute("SELECT * FROM coffrets ORDER BY actif DESC, nom").fetchall()
    return render_template(
        "coffrets.html",
        coffrets=[{"c": c, "elements": elements(conn, c["id"]),
                   "dispo": disponibles(conn, c["id"])} for c in liste],
        recettes=conn.execute("SELECT id, nom FROM recettes ORDER BY nom").fetchall(),
        emballages=conn.execute("SELECT id, nom, stock FROM materiaux ORDER BY nom").fetchall(),
        formats=sorted({l["volume_cl"] for l in lots_avec_stock()} | {20, 35, 50, 70}),
    )


def enregistrer(conn, coffret_id, form):
    conn.execute("DELETE FROM coffret_elements WHERE coffret_id = ?", (coffret_id,))
    for recette, cl, qte in zip(form.getlist("el_recette"), form.getlist("el_cl"),
                                form.getlist("el_qte")):
        if to_int(recette) and to_int(qte) > 0:
            conn.execute(
                "INSERT INTO coffret_elements (coffret_id, recette_id, volume_cl, quantite)"
                " VALUES (?, ?, ?, ?)", (coffret_id, to_int(recette), to_int(cl, 50), to_int(qte)))


def lire(form):
    return {"nom": form.get("nom", "").strip(),
            "prix_ttc": max(to_float(form.get("prix_ttc")), 0),
            "prix_revendeur_ht": to_float(form.get("prix_revendeur_ht"), None),
            "materiau_id": to_int(form.get("materiau_id")) or None,
            "actif": 1 if form.get("actif", "1") else 0,
            "notes": form.get("notes", "").strip() or None}


@app.route("/coffrets", methods=["POST"])
def coffret_creer():
    conn = get_db()
    data = lire(request.form)
    if not data["nom"]:
        flash("Donnez un nom au coffret.", "erreur")
        return redirect(url_for("coffrets"))
    cur = conn.execute(
        """INSERT INTO coffrets (nom, prix_ttc, prix_revendeur_ht, materiau_id, actif, notes)
           VALUES (:nom, :prix_ttc, :prix_revendeur_ht, :materiau_id, :actif, :notes)""", data)
    enregistrer(conn, cur.lastrowid, request.form)
    conn.commit()
    flash(f"Coffret « {data['nom']} » créé : il apparaît dans la caisse.", "succes")
    return redirect(url_for("coffrets") + f"#coffret-{cur.lastrowid}")


@app.route("/coffrets/<int:coffret_id>", methods=["POST"])
def coffret_modifier(coffret_id):
    conn = get_db()
    get_or_404("coffrets", coffret_id)
    if request.form.get("action") == "supprimer":
        conn.execute("DELETE FROM coffrets WHERE id = ?", (coffret_id,))
        conn.commit()
        flash("Coffret supprimé (les ventes passées sont conservées).", "succes")
        return redirect(url_for("coffrets"))
    data = lire(request.form)
    data["actif"] = 1 if request.form.get("actif") else 0
    conn.execute(
        """UPDATE coffrets SET nom = :nom, prix_ttc = :prix_ttc, prix_revendeur_ht = :prix_revendeur_ht,
           materiau_id = :materiau_id, actif = :actif, notes = :notes WHERE id = :id""",
        {**data, "id": coffret_id})
    enregistrer(conn, coffret_id, request.form)
    conn.commit()
    flash("Coffret mis à jour.", "succes")
    return redirect(url_for("coffrets") + f"#coffret-{coffret_id}")
