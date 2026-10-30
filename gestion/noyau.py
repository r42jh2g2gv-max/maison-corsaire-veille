"""Application Flask, configuration et outils partagés par tous les modules."""
import os
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, abort, g, render_template, request, session, url_for, redirect

import db as database
from calculs import (CATEGORIES_INGREDIENTS, STATUTS, STATUTS_EMBOUTEILLES,
                     TYPES_MATERIAUX, cout_revient)

BASE = Path(__file__).parent
INSTANCE = BASE / "instance"
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
        "sept.", "oct.", "nov.", "déc."]
MOIS_LONGS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
              "septembre", "octobre", "novembre", "décembre"]
MODES_PAIEMENT = {"especes": "Espèces", "carte": "Carte", "virement": "Virement",
                  "cheque": "Chèque"}
TYPES_CLIENTS = {"particulier": "Particulier", "revendeur": "Revendeur",
                 "professionnel": "Professionnel"}
TYPES_EVENEMENTS = {"marche": "Marché", "salon": "Salon", "degustation": "Dégustation",
                    "autre": "Autre"}

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
# Accès aux données
# --------------------------------------------------------------------------

def get_db():
    return database.get_db()


def settings():
    if "settings" not in g:
        rows = get_db().execute("SELECT key, value FROM settings").fetchall()
        g.settings = {r["key"]: r["value"] for r in rows}
    return g.settings


def set_setting(key, value):
    get_db().execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    g.pop("settings", None)


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


def get_or_404(table, ident):
    row = get_db().execute(f"SELECT * FROM {table} WHERE id = ?", (ident,)).fetchone()
    if not row:
        abort(404)
    return row


def stock_lot(lot):
    if lot["statut"] not in STATUTS_EMBOUTEILLES:
        return 0
    return max(lot["nb_bouteilles"] - lot["vendu"], 0)


def couts_par_lot(conn, conf):
    return {lot["id"]: cout_revient(conn, lot, conf)["total"]
            for lot in conn.execute("SELECT * FROM lots").fetchall()}


def maj_statut_epuise(conn, lot_id, reouvrir=False):
    """Passe le lot en « épuisé » quand tout est vendu (et l'inverse si reouvrir)."""
    lot = get_lot(lot_id)
    reste = lot["nb_bouteilles"] - lot["vendu"]
    if lot["statut"] == "embouteille" and reste <= 0:
        conn.execute("UPDATE lots SET statut = 'epuise' WHERE id = ?", (lot_id,))
    elif reouvrir and lot["statut"] == "epuise" and reste > 0:
        conn.execute("UPDATE lots SET statut = 'embouteille' WHERE id = ?", (lot_id,))


def mois_label(ym):
    y, m = ym.split("-")
    return f"{MOIS_LONGS[int(m) - 1]} {y}"


def redirection_sure(cible, defaut):
    if cible and cible.startswith("/") and not cible.startswith("//"):
        return redirect(cible)
    return redirect(defaut)


# --------------------------------------------------------------------------
# Filtres de gabarits
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
    return f"{value:,.{decimales}f}".replace(",", " ").replace(".", ",")


@app.template_filter("datefr")
def datefr(value):
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except ValueError:
        return value


@app.template_filter("datecourte")
def datecourte(value):
    if not value:
        return ""
    d = date.fromisoformat(value[:10])
    return f"{d.day} {MOIS[d.month - 1]}"


@app.template_filter("moisabrege")
def moisabrege(value):
    return MOIS[int(value[5:7]) - 1] if value else ""


@app.template_filter("jours")
def jours(value):
    """« aujourd'hui », « demain », « dans 9 j », « il y a 3 j »."""
    if not value:
        return ""
    n = (date.fromisoformat(value[:10]) - date.today()).days
    if n == 0:
        return "aujourd'hui"
    if n == 1:
        return "demain"
    if n == -1:
        return "hier"
    return f"dans {n} j" if n > 0 else f"il y a {-n} j"


@app.context_processor
def inject_globals():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return {
        "csrf_token": session["csrf"],
        "STATUTS": STATUTS,
        "CATEGORIES": CATEGORIES_INGREDIENTS,
        "TYPES_MATERIAUX": TYPES_MATERIAUX,
        "MODES_PAIEMENT": MODES_PAIEMENT,
        "TYPES_CLIENTS": TYPES_CLIENTS,
        "TYPES_EVENEMENTS": TYPES_EVENEMENTS,
        "today": today(),
        "theme": request.cookies.get("theme", "sombre"),
    }


# --------------------------------------------------------------------------
# Sécurité : connexion obligatoire et jeton CSRF
# --------------------------------------------------------------------------

PUBLIC = ("static", "connexion", "theme")


@app.before_request
def securite():
    if request.method == "POST":
        token = request.form.get("csrf") or request.headers.get("X-CSRF")
        if not token or token != session.get("csrf"):
            abort(400, "Jeton de sécurité invalide, rechargez la page.")
    if request.endpoint in PUBLIC:
        return None
    if not session.get("user_id"):
        return redirect(url_for("connexion", next=request.path))
    return None


@app.route("/theme/<nom>")
def theme(nom):
    resp = redirection_sure(request.args.get("next"), url_for("tableau_de_bord"))
    resp.set_cookie("theme", "clair" if nom == "clair" else "sombre",
                    max_age=3600 * 24 * 365, samesite="Lax")
    return resp


@app.errorhandler(404)
def introuvable(_e):
    return render_template("erreur.html", message="Page introuvable."), 404


@app.errorhandler(400)
def requete_invalide(e):
    return render_template("erreur.html", message=e.description), 400
