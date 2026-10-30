"""Maison Corsaire — gestion de la production de rhum arrangé."""
import os
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db as database
from calculs import (CATEGORIES_INGREDIENTS, STATUTS, STATUTS_EMBOUTEILLES,
                     TYPES_MATERIAUX, cout_revient, marge_pct, prix_depuis_marge,
                     taux_tva, to_float)

BASE = Path(__file__).parent
INSTANCE = BASE / "instance"
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
        "sept.", "oct.", "nov.", "déc."]

app = Flask(__name__)
INSTANCE.mkdir(exist_ok=True)


def _secret_key():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    path = INSTANCE / "secret_key"
    if not path.exists():
        path.write_text(secrets.token_hex(32))
    return path.read_text().strip()


app.config.update(
    SECRET_KEY=_secret_key(),
    DATABASE=os.environ.get("DATABASE", str(INSTANCE / "corsaire.db")),
    ADMIN_EMAIL=os.environ.get("ADMIN_EMAIL", "contact@maisoncorsaire.fr"),
    ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "corsaire2026"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
app.teardown_appcontext(database.close_db)
database.init_db(app)


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------

def get_db():
    return database.get_db()


def settings():
    rows = get_db().execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def today():
    return date.today().isoformat()


def parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def to_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def lots_avec_stock(where="", params=()):
    return get_db().execute(
        f"""SELECT l.*,
                   COALESCE((SELECT SUM(quantite) FROM ventes v WHERE v.lot_id = l.id), 0) AS vendu
            FROM lots l {where}""",
        params,
    ).fetchall()


def get_lot(lot_id):
    rows = lots_avec_stock("WHERE l.id = ?", (lot_id,))
    if not rows:
        abort(404)
    return rows[0]


def stock_lot(lot):
    if lot["statut"] not in STATUTS_EMBOUTEILLES:
        return 0
    return max(lot["nb_bouteilles"] - lot["vendu"], 0)


def prochain_numero(conn):
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


def maj_statut_epuise(conn, lot_id, reouvrir=False):
    """Passe le lot en « épuisé » quand tout est vendu (et l'inverse si reouvrir)."""
    lot = get_lot(lot_id)
    reste = lot["nb_bouteilles"] - lot["vendu"]
    if lot["statut"] == "embouteille" and reste <= 0:
        conn.execute("UPDATE lots SET statut = 'epuise' WHERE id = ?", (lot_id,))
    elif reouvrir and lot["statut"] == "epuise" and reste > 0:
        conn.execute("UPDATE lots SET statut = 'embouteille' WHERE id = ?", (lot_id,))


def couts_par_lot(conn, conf):
    return {lot["id"]: cout_revient(conn, lot, conf)["total"]
            for lot in conn.execute("SELECT * FROM lots").fetchall()}


def mois_label(ym):
    y, m = ym.split("-")
    return f"{MOIS[int(m) - 1]} {y}"


# --------------------------------------------------------------------------
# Filtres de gabarits, sécurité
# --------------------------------------------------------------------------

@app.template_filter("euro")
def euro(value):
    if value is None:
        return "—"
    txt = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return f"{txt} €"


@app.template_filter("nombre")
def nombre(value, decimales=0):
    if value is None:
        return "—"
    txt = f"{value:,.{decimales}f}".replace(",", " ").replace(".", ",")
    return txt


@app.template_filter("datefr")
def datefr(value):
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except ValueError:
        return value


@app.context_processor
def inject_globals():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return {
        "csrf_token": session["csrf"],
        "STATUTS": STATUTS,
        "CATEGORIES": CATEGORIES_INGREDIENTS,
        "TYPES_MATERIAUX": TYPES_MATERIAUX,
        "today": today(),
    }


@app.before_request
def securite():
    if request.endpoint in ("static", "connexion"):
        if request.method == "POST":
            verifier_csrf()
        return None
    if not session.get("user_id"):
        return redirect(url_for("connexion", next=request.path))
    if request.method == "POST":
        verifier_csrf()
    return None


def verifier_csrf():
    token = request.form.get("csrf")
    if not token or token != session.get("csrf"):
        abort(400, "Jeton de sécurité invalide, rechargez la page.")


# --------------------------------------------------------------------------
# Authentification
# --------------------------------------------------------------------------

@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//")
                            else url_for("tableau_de_bord"))
        flash("Email ou mot de passe incorrect.", "erreur")
    demo = check_password_hash(
        get_db().execute("SELECT password_hash FROM users LIMIT 1").fetchone()[0],
        "corsaire2026",
    )
    return render_template("connexion.html", demo=demo)


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect(url_for("connexion"))


# --------------------------------------------------------------------------
# Tableau de bord
# --------------------------------------------------------------------------

@app.route("/")
def tableau_de_bord():
    conn = get_db()
    conf = settings()
    tva = taux_tva(conf)
    couts = couts_par_lot(conn, conf)
    mois = today()[:7]

    ventes = conn.execute("SELECT * FROM ventes ORDER BY date_vente").fetchall()

    def stats(rows):
        ca = sum(v["quantite"] * v["prix_unitaire_ttc"] for v in rows)
        ht = ca / (1 + tva)
        cout = sum(v["quantite"] * couts.get(v["lot_id"], 0) for v in rows)
        return ca, (marge_pct(ht, cout) if ht else None), sum(v["quantite"] for v in rows)

    ventes_mois = [v for v in ventes if v["date_vente"].startswith(mois)]
    ca_mois, marge_mois, btl_mois = stats(ventes_mois)
    depuis = (date.today() - timedelta(days=365)).isoformat()
    _, marge_12m, _ = stats([v for v in ventes if v["date_vente"] >= depuis])

    lots = lots_avec_stock()
    stock_total = sum(stock_lot(l) for l in lots)

    # Courbe des 6 derniers mois
    historique = []
    y, m = date.today().year, date.today().month
    for _ in range(6):
        ym = f"{y}-{m:02d}"
        historique.append({
            "label": MOIS[m - 1],
            "ca": sum(v["quantite"] * v["prix_unitaire_ttc"]
                      for v in ventes if v["date_vente"].startswith(ym)),
        })
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    historique.reverse()
    ca_max = max((h["ca"] for h in historique), default=0) or 1

    prochains = conn.execute(
        """SELECT l.*, COALESCE(l.date_embouteillage,
                  date(l.date_maceration, '+' || COALESCE(r.duree_maceration_jours, 60) || ' days'))
                  AS date_prete
           FROM lots l LEFT JOIN recettes r ON r.id = l.recette_id
           WHERE l.statut IN ('maceration', 'pret')
           ORDER BY l.statut = 'pret' DESC, date_prete"""
    ).fetchall()

    alertes = conn.execute(
        "SELECT * FROM materiaux WHERE stock <= seuil_alerte ORDER BY type"
    ).fetchall()

    dernieres = conn.execute(
        """SELECT v.*, l.numero, l.recette_nom FROM ventes v JOIN lots l ON l.id = v.lot_id
           ORDER BY v.date_vente DESC, v.id DESC LIMIT 5"""
    ).fetchall()

    return render_template(
        "tableau_de_bord.html",
        ca_mois=ca_mois, marge_mois=marge_mois, marge_12m=marge_12m,
        btl_mois=btl_mois, nb_ventes_mois=len(ventes_mois),
        stock_total=stock_total, mois_label=mois_label(mois),
        lots_en_stock=[l for l in lots if stock_lot(l) > 0],
        historique=historique, ca_max=ca_max, prochains=prochains,
        alertes=alertes, dernieres=dernieres, stock_lot=stock_lot,
    )


# --------------------------------------------------------------------------
# Module 1 — Registre des lots
# --------------------------------------------------------------------------

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
                                   numero=prochain_numero(conn), nouveau=True)
        numero = prochain_numero(conn)
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
            ):
                conn.execute(
                    "INSERT INTO lot_ingredients (lot_id, categorie, nom, quantite, unite, cout)"
                    " VALUES (?, ?, ?, ?, ?, 0)",
                    (lot_id, ing["categorie"], ing["nom"],
                     round((ing["quantite_par_litre"] or 0) * litres, 3), ing["unite"]),
                )
        synchroniser_materiaux(conn, lot_id)
        conn.commit()
        flash(f"Lot {numero} créé. Ajoutez ou complétez maintenant les ingrédients et leurs coûts.", "succes")
        return redirect(url_for("lot_detail", lot_id=lot_id))

    lot = {"date_maceration": today(), "volume_cl": 50, "statut": "maceration",
           "nb_bouteilles": 0}
    recette_id = to_int(request.args.get("recette_id"))
    if recette_id:
        r = conn.execute("SELECT * FROM recettes WHERE id = ?", (recette_id,)).fetchone()
        if r:
            lot.update(recette_id=r["id"], recette_nom=r["nom"], degre=r["degre"])
    return render_template("lot_form.html", lot=lot, recettes=recettes,
                           numero=prochain_numero(conn), nouveau=True)


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
        "lot_detail.html", lot=lot, ingredients=ingredients, ventes=ventes,
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
    nom = request.form.get("nom", "").strip()
    categorie = request.form.get("categorie")
    if not nom or categorie not in CATEGORIES_INGREDIENTS:
        flash("Indiquez au moins le nom et la catégorie de l'ingrédient.", "erreur")
    else:
        conn.execute(
            "INSERT INTO lot_ingredients (lot_id, categorie, nom, quantite, unite, cout)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (lot_id, categorie, nom, to_float(request.form.get("quantite"), None),
             request.form.get("unite", "").strip(), to_float(request.form.get("cout"))),
        )
        conn.commit()
        flash(f"Ingrédient « {nom} » ajouté.", "succes")
    return redirect(url_for("lot_detail", lot_id=lot_id) + "#ingredients")


@app.route("/lots/<int:lot_id>/ingredients/<int:ing_id>", methods=["POST"])
def ingredient_modifier(lot_id, ing_id):
    conn = get_db()
    if request.form.get("action") == "supprimer":
        conn.execute("DELETE FROM lot_ingredients WHERE id = ? AND lot_id = ?", (ing_id, lot_id))
        flash("Ingrédient retiré.", "succes")
    else:
        conn.execute(
            "UPDATE lot_ingredients SET quantite = ?, unite = ?, cout = ? WHERE id = ? AND lot_id = ?",
            (to_float(request.form.get("quantite"), None), request.form.get("unite", "").strip(),
             to_float(request.form.get("cout")), ing_id, lot_id),
        )
        flash("Ingrédient mis à jour.", "succes")
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


@app.route("/ventes", methods=["GET", "POST"])
def ventes():
    conn = get_db()
    conf = settings()
    if request.method == "POST":
        lot_id = to_int(request.form.get("lot_id"))
        quantite = to_int(request.form.get("quantite"))
        prix = to_float(request.form.get("prix_unitaire_ttc"))
        client = request.form.get("client", "").strip()
        date_vente = parse_date(request.form.get("date_vente")) or today()
        canal = "revendeur" if request.form.get("canal") == "revendeur" else "direct"
        lot = lots_avec_stock("WHERE l.id = ?", (lot_id,))
        erreurs = []
        if not lot:
            erreurs.append("Choisissez un lot.")
        elif lot[0]["statut"] not in STATUTS_EMBOUTEILLES:
            erreurs.append("Ce lot n'est pas encore embouteillé.")
        elif quantite > stock_lot(lot[0]):
            erreurs.append(f"Stock insuffisant : il reste {stock_lot(lot[0])} bouteille(s) "
                           f"du lot {lot[0]['numero']}.")
        if quantite <= 0:
            erreurs.append("La quantité doit être supérieure à zéro.")
        if prix < 0:
            erreurs.append("Le prix ne peut pas être négatif.")
        if not client:
            erreurs.append("Indiquez le client.")
        if erreurs:
            for e in erreurs:
                flash(e, "erreur")
        else:
            conn.execute(
                "INSERT INTO ventes (date_vente, client, lot_id, quantite, prix_unitaire_ttc,"
                " canal, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (date_vente, client, lot_id, quantite, prix, canal,
                 request.form.get("notes", "").strip()),
            )
            maj_statut_epuise(conn, lot_id)
            conn.commit()
            reste = stock_lot(get_lot(lot_id))
            flash(f"Vente enregistrée : {quantite} × {lot[0]['recette_nom']} "
                  f"({euro(quantite * prix)}). Reste {reste} bouteille(s) du lot.", "succes")
            return redirect(url_for("ventes"))

    mois_dispo = [r[0] for r in conn.execute(
        "SELECT DISTINCT substr(date_vente, 1, 7) FROM ventes ORDER BY 1 DESC")]
    mois = request.args.get("mois", "")
    if mois and mois != "tout" and mois not in mois_dispo:
        mois = ""
    if not mois:
        mois = "tout"
    sql = """SELECT v.*, l.numero, l.recette_nom FROM ventes v JOIN lots l ON l.id = v.lot_id"""
    params = ()
    if mois != "tout":
        sql += " WHERE v.date_vente LIKE ?"
        params = (mois + "%",)
    rows = conn.execute(sql + " ORDER BY v.date_vente DESC, v.id DESC", params).fetchall()
    couts = couts_par_lot(conn, conf)
    tva = taux_tva(conf)
    total = sum(v["quantite"] * v["prix_unitaire_ttc"] for v in rows)
    cout_total = sum(v["quantite"] * couts.get(v["lot_id"], 0) for v in rows)
    lots_dispo = [l for l in lots_avec_stock(
        "WHERE l.statut = 'embouteille' ORDER BY l.numero DESC") if stock_lot(l) > 0]
    clients = [r[0] for r in conn.execute(
        "SELECT client FROM ventes GROUP BY client ORDER BY MAX(date_vente) DESC LIMIT 50")]
    return render_template(
        "ventes.html", ventes=rows, mois=mois, mois_dispo=mois_dispo, mois_label=mois_label,
        total=total, marge=marge_pct(total / (1 + tva), cout_total) if total else None,
        bouteilles=sum(v["quantite"] for v in rows), lots_dispo=lots_dispo, clients=clients,
        stock_lot=stock_lot, form=request.form if request.method == "POST" else {},
        lot_preselect=to_int(request.args.get("lot_id")),
    )


@app.route("/ventes/<int:vente_id>/supprimer", methods=["POST"])
def vente_supprimer(vente_id):
    conn = get_db()
    vente = conn.execute("SELECT * FROM ventes WHERE id = ?", (vente_id,)).fetchone()
    if not vente:
        abort(404)
    conn.execute("DELETE FROM ventes WHERE id = ?", (vente_id,))
    maj_statut_epuise(conn, vente["lot_id"], reouvrir=True)
    conn.commit()
    flash(f"Vente supprimée : {vente['quantite']} bouteille(s) réintégrée(s) au stock.", "succes")
    retour = request.form.get("retour", "")
    return redirect(retour if retour.startswith("/") and not retour.startswith("//")
                    else url_for("ventes"))


# --------------------------------------------------------------------------
# Paramètres
# --------------------------------------------------------------------------

@app.route("/parametres", methods=["GET", "POST"])
def parametres():
    conn = get_db()
    if request.method == "POST":
        for key in ("producteur_nom", "producteur_adresse", "siret"):
            conn.execute("UPDATE settings SET value = ? WHERE key = ?",
                         (request.form.get(key, "").strip(), key))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'tva_applicable'",
                     ("1" if request.form.get("tva_applicable") else "0",))
        for key in ("tva_taux", "accise_hlap", "secu_hlap"):
            conn.execute("UPDATE settings SET value = ? WHERE key = ?",
                         (str(max(to_float(request.form.get(key)), 0)), key))
        conn.commit()
        flash("Paramètres enregistrés.", "succes")
        return redirect(url_for("parametres"))
    user = conn.execute("SELECT email FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    return render_template("parametres.html", conf=settings(), email=user["email"])


@app.route("/parametres/compte", methods=["POST"])
def parametres_compte():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not check_password_hash(user["password_hash"], request.form.get("actuel", "")):
        flash("Mot de passe actuel incorrect.", "erreur")
        return redirect(url_for("parametres") + "#compte")
    email = request.form.get("email", "").strip().lower()
    nouveau = request.form.get("nouveau", "")
    if "@" not in email:
        flash("Adresse email invalide.", "erreur")
        return redirect(url_for("parametres") + "#compte")
    if nouveau and len(nouveau) < 8:
        flash("Le nouveau mot de passe doit contenir au moins 8 caractères.", "erreur")
        return redirect(url_for("parametres") + "#compte")
    conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user["id"]))
    if nouveau:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                     (generate_password_hash(nouveau), user["id"]))
    conn.commit()
    flash("Compte mis à jour.", "succes")
    return redirect(url_for("parametres") + "#compte")


@app.route("/parametres/donnees", methods=["POST"])
def parametres_donnees():
    conn = get_db()
    action = request.form.get("action")
    if request.form.get("confirmation", "").strip().upper() != "CONFIRMER":
        flash("Tapez CONFIRMER pour valider cette action.", "erreur")
        return redirect(url_for("parametres") + "#donnees")
    database.clear_data(conn)
    if action == "exemple":
        database.seed_demo(conn)
        flash("Données d'exemple rechargées.", "succes")
    else:
        flash("Toutes les données ont été effacées. Vous pouvez démarrer votre vrai registre.", "succes")
    conn.commit()
    return redirect(url_for("tableau_de_bord"))


@app.errorhandler(404)
def introuvable(_e):
    return render_template("erreur.html", message="Page introuvable."), 404


@app.errorhandler(400)
def requete_invalide(e):
    return render_template("erreur.html", message=e.description), 400


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
