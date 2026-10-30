"""Stock de matières premières (rhum, fruits, épices, sucre) et registre des achats."""
from datetime import date, datetime
from pathlib import Path

from flask import abort, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from calculs import CATEGORIES_INGREDIENTS, convertir, to_float
from noyau import (INSTANCE, MODES_PAIEMENT, app, get_db, get_or_404, parse_date,
                   redirection_sure, to_int, today)

JUSTIFICATIFS = INSTANCE / "justificatifs"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".heic", ".webp"}
TYPES_MOUVEMENTS = {"achat": "Achat", "utilisation": "Utilisation", "ajustement": "Ajustement"}

SQL_STOCK = """
SELECT m.*, COALESCE((SELECT SUM(quantite) FROM mouvements_mp v WHERE v.mp_id = m.id), 0) AS stock
FROM matieres_premieres m
"""


def matieres_avec_stock(where="", params=()):
    return get_db().execute(SQL_STOCK + where, params).fetchall()


def en_alerte(mp):
    return mp["seuil_alerte"] > 0 and mp["stock"] <= mp["seuil_alerte"]


app.jinja_env.globals["mp_en_alerte"] = en_alerte
app.jinja_env.globals["TYPES_MOUVEMENTS"] = TYPES_MOUVEMENTS


def trouver_mp(conn, nom):
    return conn.execute("SELECT * FROM matieres_premieres WHERE lower(nom) = lower(?)",
                        ((nom or "").strip(),)).fetchone()


def synchroniser_utilisation(conn, lot_ingredient_id):
    """Recalcule la sortie de stock liée à un ingrédient de lot."""
    conn.execute("DELETE FROM mouvements_mp WHERE lot_ingredient_id = ?", (lot_ingredient_id,))
    ing = conn.execute(
        """SELECT i.*, l.date_maceration, m.unite AS unite_mp FROM lot_ingredients i
           JOIN lots l ON l.id = i.lot_id
           LEFT JOIN matieres_premieres m ON m.id = i.mp_id WHERE i.id = ?""",
        (lot_ingredient_id,)).fetchone()
    if not ing or not ing["mp_id"]:
        return None
    qte = convertir(ing["quantite"] or 0, ing["unite"], ing["unite_mp"])
    if qte is None:
        return f"unité « {ing['unite']} » incompatible avec le stock en {ing['unite_mp']}"
    if qte:
        conn.execute(
            "INSERT INTO mouvements_mp (mp_id, date_mouvement, type, quantite, lot_ingredient_id)"
            " VALUES (?, ?, 'utilisation', ?, ?)",
            (ing["mp_id"], ing["date_maceration"] or today(), -qte, lot_ingredient_id))
    return None


def cout_depuis_stock(conn, mp_id, quantite, unite):
    mp = conn.execute("SELECT * FROM matieres_premieres WHERE id = ?", (mp_id,)).fetchone()
    if not mp:
        return None
    qte = convertir(quantite or 0, unite, mp["unite"])
    return round(qte * mp["cout_unitaire"], 2) if qte is not None else None


# --------------------------------------------------------------------------
# Matières premières
# --------------------------------------------------------------------------

def lire_mp(form):
    return {
        "nom": form.get("nom", "").strip(),
        "categorie": form.get("categorie") if form.get("categorie") in CATEGORIES_INGREDIENTS
        else "autre",
        "unite": form.get("unite", "").strip() or "kg",
        "seuil_alerte": max(to_float(form.get("seuil_alerte")), 0),
        "cout_unitaire": max(to_float(form.get("cout_unitaire")), 0),
        "fournisseur": form.get("fournisseur", "").strip(),
        "allergene": form.get("allergene", "").strip(),
        "nom_etiquette": form.get("nom_etiquette", "").strip() or None,
        "notes": form.get("notes", "").strip(),
    }


@app.route("/matieres")
def matieres():
    rows = matieres_avec_stock(
        """ORDER BY CASE m.categorie WHEN 'rhum' THEN 0 WHEN 'fruit' THEN 1 WHEN 'epice' THEN 2
           WHEN 'sucre' THEN 3 ELSE 4 END, m.nom""")
    return render_template("matieres.html", matieres=rows,
                           valeur=sum(max(m["stock"], 0) * m["cout_unitaire"] for m in rows))


@app.route("/matieres", methods=["POST"])
def matiere_ajouter():
    conn = get_db()
    data = lire_mp(request.form)
    if not data["nom"]:
        flash("Le nom de la matière première est obligatoire.", "erreur")
        return redirect(url_for("matieres"))
    if trouver_mp(conn, data["nom"]):
        flash(f"« {data['nom']} » existe déjà.", "erreur")
        return redirect(url_for("matieres"))
    cur = conn.execute(
        """INSERT INTO matieres_premieres (nom, categorie, unite, seuil_alerte, cout_unitaire,
           fournisseur, allergene, notes, nom_etiquette) VALUES (:nom, :categorie, :unite,
           :seuil_alerte, :cout_unitaire, :fournisseur, :allergene, :notes, :nom_etiquette)""",
        data)
    stock_initial = to_float(request.form.get("stock_initial"))
    if stock_initial:
        conn.execute(
            "INSERT INTO mouvements_mp (mp_id, date_mouvement, type, quantite, notes)"
            " VALUES (?, ?, 'ajustement', ?, 'Stock initial')", (cur.lastrowid, today(), stock_initial))
    # Relie les recettes qui utilisent déjà ce nom
    conn.execute("UPDATE recette_ingredients SET mp_id = ? WHERE lower(nom) = lower(?) AND mp_id IS NULL",
                 (cur.lastrowid, data["nom"]))
    conn.commit()
    flash(f"« {data['nom']} » ajouté au stock.", "succes")
    return redirection_sure(request.form.get("retour"),
                            url_for("matiere_detail", mp_id=cur.lastrowid))


@app.route("/matieres/<int:mp_id>", methods=["GET", "POST"])
def matiere_detail(mp_id):
    conn = get_db()
    get_or_404("matieres_premieres", mp_id)
    if request.method == "POST":
        if request.form.get("action") == "supprimer":
            mp = get_or_404("matieres_premieres", mp_id)
            conn.execute("DELETE FROM matieres_premieres WHERE id = ?", (mp_id,))
            conn.commit()
            flash(f"« {mp['nom']} » supprimé. Les lots et achats passés sont conservés.", "succes")
            return redirect(url_for("matieres"))
        data = lire_mp(request.form)
        if not data["nom"]:
            flash("Le nom est obligatoire.", "erreur")
        else:
            conn.execute(
                """UPDATE matieres_premieres SET nom = :nom, categorie = :categorie, unite = :unite,
                   seuil_alerte = :seuil_alerte, cout_unitaire = :cout_unitaire,
                   fournisseur = :fournisseur, allergene = :allergene, notes = :notes,
                   nom_etiquette = :nom_etiquette WHERE id = :id""", {**data, "id": mp_id})
            conn.commit()
            flash("Matière première mise à jour.", "succes")
        return redirect(url_for("matiere_detail", mp_id=mp_id))
    mp = matieres_avec_stock("WHERE m.id = ?", (mp_id,))[0]
    mouvements = conn.execute(
        """SELECT v.*, l.id AS lot_id, l.numero AS lot_numero, a.id AS achat_id,
                  a.fournisseur AS achat_fournisseur
           FROM mouvements_mp v
           LEFT JOIN lot_ingredients i ON i.id = v.lot_ingredient_id
           LEFT JOIN lots l ON l.id = i.lot_id
           LEFT JOIN achat_lignes al ON al.id = v.achat_ligne_id
           LEFT JOIN achats a ON a.id = al.achat_id
           WHERE v.mp_id = ? ORDER BY v.date_mouvement DESC, v.id DESC""", (mp_id,)).fetchall()
    return render_template("matiere_detail.html", mp=mp, mouvements=mouvements)


@app.route("/matieres/<int:mp_id>/inventaire", methods=["POST"])
def matiere_inventaire(mp_id):
    """Corrige un écart : on saisit le stock réellement constaté."""
    conn = get_db()
    mp = matieres_avec_stock("WHERE m.id = ?", (mp_id,))
    if not mp:
        abort(404)
    reel = request.form.get("stock_reel", "").strip()
    if reel == "":
        flash("Indiquez la quantité réellement en stock.", "erreur")
        return redirect(url_for("matiere_detail", mp_id=mp_id))
    ecart = round(to_float(reel) - mp[0]["stock"], 4)
    if ecart:
        conn.execute(
            "INSERT INTO mouvements_mp (mp_id, date_mouvement, type, quantite, notes)"
            " VALUES (?, ?, 'ajustement', ?, ?)",
            (mp_id, parse_date(request.form.get("date")) or today(), ecart,
             request.form.get("notes", "").strip() or "Inventaire"))
        conn.commit()
        flash(f"Stock corrigé : écart de {ecart:+g} {mp[0]['unite']}.", "succes")
    else:
        flash("Aucun écart : le stock est juste.", "info")
    return redirection_sure(request.form.get("retour"), url_for("matiere_detail", mp_id=mp_id))


@app.route("/mouvements/<int:mvt_id>", methods=["POST"])
def mouvement_modifier(mvt_id):
    conn = get_db()
    mvt = get_or_404("mouvements_mp", mvt_id)
    if request.form.get("action") == "supprimer":
        conn.execute("DELETE FROM mouvements_mp WHERE id = ?", (mvt_id,))
        flash("Mouvement supprimé : le stock a été recalculé.", "succes")
    else:
        quantite = to_float(request.form.get("quantite"))
        sens = -1 if mvt["type"] == "utilisation" else 1
        conn.execute(
            "UPDATE mouvements_mp SET quantite = ?, date_mouvement = ?, notes = ? WHERE id = ?",
            (sens * abs(quantite) if mvt["type"] != "ajustement" else quantite,
             parse_date(request.form.get("date")) or mvt["date_mouvement"],
             request.form.get("notes", "").strip() or None, mvt_id))
        flash("Mouvement corrigé : le stock a été recalculé.", "succes")
    conn.commit()
    return redirect(url_for("matiere_detail", mp_id=mvt["mp_id"]) + "#mouvements")


# --------------------------------------------------------------------------
# Registre des achats
# --------------------------------------------------------------------------

def articles_achat(conn):
    """Liste des articles pouvant être achetés (matières premières et conditionnement)."""
    mps = conn.execute("SELECT id, nom, unite, cout_unitaire FROM matieres_premieres ORDER BY nom")
    mats = conn.execute("SELECT id, nom, cout_unitaire FROM materiaux ORDER BY nom")
    return ([{"cle": f"mp:{m['id']}", "nom": m["nom"], "unite": m["unite"], "groupe": "Matières premières"}
             for m in mps] +
            [{"cle": f"mat:{m['id']}", "nom": m["nom"], "unite": "pièce", "groupe": "Conditionnement"}
             for m in mats])


def lire_lignes(form):
    lignes = []
    for cle, designation, qte, unite, montant in zip(
            form.getlist("l_article"), form.getlist("l_designation"), form.getlist("l_qte"),
            form.getlist("l_unite"), form.getlist("l_montant")):
        designation = designation.strip()
        if not designation and not cle:
            continue
        lignes.append({"cle": cle, "designation": designation, "quantite": to_float(qte, None),
                       "unite": unite.strip(), "montant": round(to_float(montant), 2)})
    return lignes


def annuler_lignes(conn, achat_id):
    """Retire du stock ce qu'un achat y avait ajouté, puis supprime ses lignes."""
    for l in conn.execute("SELECT * FROM achat_lignes WHERE achat_id = ?", (achat_id,)):
        if l["materiau_id"] and l["quantite"]:
            conn.execute("UPDATE materiaux SET stock = stock - ? WHERE id = ?",
                         (int(round(l["quantite"])), l["materiau_id"]))
    conn.execute("DELETE FROM achat_lignes WHERE achat_id = ?", (achat_id,))  # mouvements en cascade


def appliquer_lignes(conn, achat_id, jour, lignes):
    avertissements = []
    for l in lignes:
        mp_id = materiau_id = None
        type_, _, ident = l["cle"].partition(":")
        if type_ == "mp":
            mp = conn.execute("SELECT * FROM matieres_premieres WHERE id = ?", (to_int(ident),)).fetchone()
            if mp:
                mp_id = mp["id"]
                l["designation"] = l["designation"] or mp["nom"]
                l["unite"] = l["unite"] or mp["unite"]
        elif type_ == "mat":
            mat = conn.execute("SELECT * FROM materiaux WHERE id = ?", (to_int(ident),)).fetchone()
            if mat:
                materiau_id = mat["id"]
                l["designation"] = l["designation"] or mat["nom"]
                l["unite"] = "pièce"
        cur = conn.execute(
            "INSERT INTO achat_lignes (achat_id, mp_id, materiau_id, designation, quantite, unite,"
            " montant) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (achat_id, mp_id, materiau_id, l["designation"] or "Article", l["quantite"],
             l["unite"], l["montant"]))
        if mp_id and l["quantite"]:
            qte = convertir(l["quantite"], l["unite"], mp["unite"])
            if qte is None:
                avertissements.append(f"{l['designation']} : unité « {l['unite']} » incompatible "
                                      f"avec le stock en {mp['unite']}, stock non mis à jour.")
                continue
            conn.execute(
                "INSERT INTO mouvements_mp (mp_id, date_mouvement, type, quantite, achat_ligne_id)"
                " VALUES (?, ?, 'achat', ?, ?)", (mp_id, jour, qte, cur.lastrowid))
            if l["montant"] and qte:
                conn.execute("UPDATE matieres_premieres SET cout_unitaire = ? WHERE id = ?",
                             (round(l["montant"] / qte, 4), mp_id))
        if materiau_id and l["quantite"]:
            conn.execute("UPDATE materiaux SET stock = stock + ? WHERE id = ?",
                         (int(round(l["quantite"])), materiau_id))
            if l["montant"]:
                conn.execute("UPDATE materiaux SET cout_unitaire = ? WHERE id = ?",
                             (round(l["montant"] / l["quantite"], 4), materiau_id))
    return avertissements


def enregistrer_justificatif(achat_id):
    fichier = request.files.get("justificatif")
    if not fichier or not fichier.filename:
        return None
    ext = Path(fichier.filename).suffix.lower()
    if ext not in EXTENSIONS:
        flash("Justificatif ignoré : formats acceptés JPG, PNG, PDF, HEIC.", "erreur")
        return None
    JUSTIFICATIFS.mkdir(parents=True, exist_ok=True)
    nom = f"{achat_id}-{datetime.now():%Y%m%d%H%M%S}-{secure_filename(fichier.filename) or 'piece' + ext}"
    fichier.save(JUSTIFICATIFS / nom)
    return nom


def lire_achat(form):
    return {
        "date_achat": parse_date(form.get("date_achat")) or today(),
        "fournisseur": form.get("fournisseur", "").strip(),
        "reference": form.get("reference", "").strip() or None,
        "mode_paiement": form.get("mode_paiement") if form.get("mode_paiement") in MODES_PAIEMENT
        else "carte",
        "notes": form.get("notes", "").strip() or None,
    }


@app.route("/achats")
def achats():
    conn = get_db()
    annee = request.args.get("annee") or today()[:4]
    rows = conn.execute(
        """SELECT a.*, (SELECT group_concat(designation, ', ') FROM achat_lignes l
                        WHERE l.achat_id = a.id) AS detail
           FROM achats a WHERE a.date_achat LIKE ? ORDER BY a.date_achat DESC, a.id DESC""",
        (annee + "%",)).fetchall()
    annees = [r[0] for r in conn.execute(
        "SELECT DISTINCT substr(date_achat, 1, 4) FROM achats ORDER BY 1 DESC")] or [annee]
    par_fournisseur = conn.execute(
        """SELECT fournisseur, SUM(montant_total) total, COUNT(*) n FROM achats
           WHERE date_achat LIKE ? GROUP BY fournisseur ORDER BY total DESC LIMIT 6""",
        (annee + "%",)).fetchall()
    return render_template("achats.html", achats=rows, annee=annee, annees=annees,
                           total=sum(a["montant_total"] for a in rows),
                           par_fournisseur=par_fournisseur)


@app.route("/achats/nouveau", methods=["GET", "POST"])
def achat_nouveau():
    conn = get_db()
    if request.method == "POST":
        data = lire_achat(request.form)
        lignes = lire_lignes(request.form)
        if not data["fournisseur"] or not lignes:
            flash("Indiquez le fournisseur et au moins une ligne d'achat.", "erreur")
        else:
            cur = conn.execute(
                """INSERT INTO achats (date_achat, fournisseur, reference, mode_paiement,
                   montant_total, notes, created_at) VALUES (:date_achat, :fournisseur, :reference,
                   :mode_paiement, :total, :notes, :created_at)""",
                {**data, "total": round(sum(l["montant"] for l in lignes), 2),
                 "created_at": datetime.now().isoformat(timespec="seconds")})
            achat_id = cur.lastrowid
            for a in appliquer_lignes(conn, achat_id, data["date_achat"], lignes):
                flash(a, "erreur")
            justificatif = enregistrer_justificatif(achat_id)
            if justificatif:
                conn.execute("UPDATE achats SET justificatif = ? WHERE id = ?", (justificatif, achat_id))
            conn.commit()
            flash("Achat enregistré : stock mis à jour.", "succes")
            return redirect(url_for("achats"))
    return render_template("achat_form.html", achat={"date_achat": today(), "mode_paiement": "carte"},
                           lignes=[], articles=articles_achat(conn), nouveau=True,
                           fournisseurs=_fournisseurs(conn),
                           mp_preselect=request.args.get("article", ""))


def _fournisseurs(conn):
    return [r[0] for r in conn.execute(
        "SELECT fournisseur FROM achats UNION SELECT fournisseur FROM matieres_premieres"
        " WHERE fournisseur IS NOT NULL AND fournisseur != '' ORDER BY 1")]


@app.route("/achats/<int:achat_id>", methods=["GET", "POST"])
def achat_modifier(achat_id):
    conn = get_db()
    achat = get_or_404("achats", achat_id)
    if request.method == "POST":
        if request.form.get("action") == "supprimer":
            annuler_lignes(conn, achat_id)
            conn.execute("DELETE FROM achats WHERE id = ?", (achat_id,))
            if achat["justificatif"]:
                (JUSTIFICATIFS / achat["justificatif"]).unlink(missing_ok=True)
            conn.commit()
            flash("Achat supprimé : les quantités ont été retirées du stock.", "succes")
            return redirect(url_for("achats"))
        data = lire_achat(request.form)
        lignes = lire_lignes(request.form)
        if not data["fournisseur"] or not lignes:
            flash("Indiquez le fournisseur et au moins une ligne d'achat.", "erreur")
            return redirect(url_for("achat_modifier", achat_id=achat_id))
        annuler_lignes(conn, achat_id)
        for a in appliquer_lignes(conn, achat_id, data["date_achat"], lignes):
            flash(a, "erreur")
        conn.execute(
            """UPDATE achats SET date_achat = :date_achat, fournisseur = :fournisseur,
               reference = :reference, mode_paiement = :mode_paiement, montant_total = :total,
               notes = :notes WHERE id = :id""",
            {**data, "total": round(sum(l["montant"] for l in lignes), 2), "id": achat_id})
        justificatif = enregistrer_justificatif(achat_id)
        if justificatif:
            if achat["justificatif"]:
                (JUSTIFICATIFS / achat["justificatif"]).unlink(missing_ok=True)
            conn.execute("UPDATE achats SET justificatif = ? WHERE id = ?", (justificatif, achat_id))
        conn.commit()
        flash("Achat modifié : stock recalculé.", "succes")
        return redirect(url_for("achats"))
    lignes = conn.execute("SELECT * FROM achat_lignes WHERE achat_id = ? ORDER BY id",
                          (achat_id,)).fetchall()
    lignes = [{**dict(l), "cle": f"mp:{l['mp_id']}" if l["mp_id"] else
               (f"mat:{l['materiau_id']}" if l["materiau_id"] else "")} for l in lignes]
    return render_template("achat_form.html", achat=achat, lignes=lignes,
                           articles=articles_achat(conn), nouveau=False,
                           fournisseurs=_fournisseurs(conn), mp_preselect="")


@app.route("/achats/<int:achat_id>/justificatif")
def achat_justificatif(achat_id):
    achat = get_or_404("achats", achat_id)
    if not achat["justificatif"]:
        abort(404)
    chemin = JUSTIFICATIFS / achat["justificatif"]
    if not chemin.exists():
        abort(404)
    return send_file(chemin)
