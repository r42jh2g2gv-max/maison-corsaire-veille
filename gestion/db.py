"""Base de données SQLite : schéma, connexion et données d'exemple."""
import sqlite3
from datetime import date, timedelta

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS recettes (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    duree_maceration_jours INTEGER DEFAULT 60,
    degre REAL,
    notes_degustation TEXT
);

CREATE TABLE IF NOT EXISTS recette_ingredients (
    id INTEGER PRIMARY KEY,
    recette_id INTEGER NOT NULL REFERENCES recettes(id) ON DELETE CASCADE,
    categorie TEXT NOT NULL,
    nom TEXT NOT NULL,
    quantite_par_litre REAL,
    unite TEXT
);

CREATE TABLE IF NOT EXISTS lots (
    id INTEGER PRIMARY KEY,
    numero TEXT UNIQUE NOT NULL,
    recette_id INTEGER REFERENCES recettes(id) ON DELETE SET NULL,
    recette_nom TEXT NOT NULL,
    date_maceration TEXT,
    date_embouteillage TEXT,
    dlc TEXT,
    nb_bouteilles INTEGER NOT NULL DEFAULT 0,
    volume_cl INTEGER NOT NULL DEFAULT 50,
    degre REAL,
    statut TEXT NOT NULL DEFAULT 'maceration',
    notes TEXT,
    -- nombre de bouteilles pour lesquelles les matières (bouteille, bouchon...)
    -- ont déjà été déduites du stock
    materiaux_deduits INTEGER NOT NULL DEFAULT 0,
    prix_vente_ttc REAL,
    prix_revendeur_ht REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lot_ingredients (
    id INTEGER PRIMARY KEY,
    lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
    categorie TEXT NOT NULL,
    nom TEXT NOT NULL,
    quantite REAL,
    unite TEXT,
    cout REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS materiaux (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    type TEXT NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    seuil_alerte INTEGER NOT NULL DEFAULT 0,
    cout_unitaire REAL NOT NULL DEFAULT 0,
    -- 1 = une unité consommée par bouteille embouteillée
    par_bouteille INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ventes (
    id INTEGER PRIMARY KEY,
    date_vente TEXT NOT NULL,
    client TEXT NOT NULL,
    lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    quantite INTEGER NOT NULL,
    prix_unitaire_ttc REAL NOT NULL,
    canal TEXT NOT NULL DEFAULT 'direct',
    notes TEXT
);
"""

DEFAULT_SETTINGS = {
    "producteur_nom": "Maison Corsaire",
    "producteur_adresse": "12 rue des Flibustiers, 17000 La Rochelle",
    "siret": "",
    "tva_applicable": "0",
    "tva_taux": "20",
    "accise_hlap": "0",
    "secu_hlap": "0",
    "marge_direct": "60",
    "marge_revendeur": "40",
    "coef_revendeur": "1.8",
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.executescript(SCHEMA)
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
    if not conn.execute("SELECT 1 FROM users").fetchone():
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (
                app.config["ADMIN_EMAIL"],
                generate_password_hash(app.config["ADMIN_PASSWORD"]),
            ),
        )
        seed_demo(conn)
    conn.commit()
    conn.close()


def clear_data(conn):
    """Supprime lots, ventes, recettes et matières (garde compte et réglages)."""
    for table in ("ventes", "lot_ingredients", "lots",
                  "recette_ingredients", "recettes", "materiaux"):
        conn.execute(f"DELETE FROM {table}")


def seed_demo(conn):
    """Données d'exemple, datées par rapport à aujourd'hui."""
    today = date.today()

    def d(days):
        return (today + timedelta(days=days)).isoformat()

    recettes = [
        ("Ananas – Vanille de Madagascar", 60, 32,
         "Nez gourmand de vanille, bouche ronde d'ananas rôti, finale douce.",
         [("rhum", "Rhum agricole blanc 50°", 0.7, "L"),
          ("fruit", "Ananas Victoria", 0.35, "kg"),
          ("epice", "Gousse de vanille", 1, "pièce"),
          ("sucre", "Sucre de canne roux", 50, "g")]),
        ("Mangue – Passion", 75, 30,
         "Explosion tropicale, acidité vive de la passion, très fruité.",
         [("rhum", "Rhum agricole blanc 50°", 0.7, "L"),
          ("fruit", "Mangue", 0.3, "kg"),
          ("fruit", "Fruit de la passion", 0.1, "kg"),
          ("sucre", "Sirop de canne", 40, "ml")]),
        ("Café – Cacao", 75, 33,
         "Notes torréfiées, cacao amer, bel équilibre avec le rhum ambré.",
         [("rhum", "Rhum ambré 45°", 0.75, "L"),
          ("epice", "Grains de café arabica", 40, "g"),
          ("epice", "Fèves de cacao", 30, "g"),
          ("sucre", "Sucre de canne roux", 40, "g")]),
        ("Coco – Citron vert", 45, 30,
         "Frais et soyeux, coco toastée et zeste de citron vert.",
         [("rhum", "Rhum agricole blanc 50°", 0.7, "L"),
          ("fruit", "Noix de coco râpée toastée", 80, "g"),
          ("fruit", "Citron vert (zestes)", 2, "pièce"),
          ("sucre", "Sucre de canne roux", 40, "g")]),
    ]
    recette_ids = []
    for nom, duree, degre, notes, ingredients in recettes:
        cur = conn.execute(
            "INSERT INTO recettes (nom, duree_maceration_jours, degre, notes_degustation)"
            " VALUES (?, ?, ?, ?)",
            (nom, duree, degre, notes),
        )
        recette_ids.append(cur.lastrowid)
        conn.executemany(
            "INSERT INTO recette_ingredients"
            " (recette_id, categorie, nom, quantite_par_litre, unite) VALUES (?, ?, ?, ?, ?)",
            [(cur.lastrowid, *ing) for ing in ingredients],
        )

    year = today.year
    # (recette, macération, embouteillage, nb, statut, prix TTC, prix revendeur HT, ingrédients, notes)
    lots = [
        (0, -240, -180, 24, "epuise", 34.0, 22.0,
         [("rhum", "Rhum agricole blanc 50°", 8.5, "L", 119.0),
          ("fruit", "Ananas Victoria", 4.2, "kg", 25.2),
          ("epice", "Gousse de vanille", 12, "pièce", 30.0),
          ("sucre", "Sucre de canne roux", 0.6, "kg", 2.4)],
         "Premier lot de l'année. Très bon retour clients."),
        (1, -200, -125, 22, "embouteille", 36.0, 23.0,
         [("rhum", "Rhum agricole blanc 50°", 7.7, "L", 107.8),
          ("fruit", "Mangue", 3.3, "kg", 19.8),
          ("fruit", "Fruit de la passion", 1.1, "kg", 13.2),
          ("sucre", "Sirop de canne", 0.45, "L", 3.6)],
         ""),
        (2, -150, -75, 20, "embouteille", 38.0, 24.0,
         [("rhum", "Rhum ambré 45°", 7.5, "L", 127.5),
          ("epice", "Grains de café arabica", 0.4, "kg", 12.0),
          ("epice", "Fèves de cacao", 0.3, "kg", 9.0),
          ("sucre", "Sucre de canne roux", 0.4, "kg", 1.6)],
         "Café torréfié par un artisan local."),
        (0, -62, None, 24, "pret", None, None,
         [("rhum", "Rhum agricole blanc 50°", 8.5, "L", 119.0),
          ("fruit", "Ananas Victoria", 4.2, "kg", 27.3),
          ("epice", "Gousse de vanille", 12, "pièce", 32.4),
          ("sucre", "Sucre de canne roux", 0.6, "kg", 2.4)],
         "Goûté : prêt, à embouteiller cette semaine."),
        (3, -25, None, 20, "maceration", None, None,
         [("rhum", "Rhum agricole blanc 50°", 7.0, "L", 98.0),
          ("fruit", "Noix de coco râpée toastée", 0.8, "kg", 9.6),
          ("fruit", "Citron vert (zestes)", 20, "pièce", 6.0),
          ("sucre", "Sucre de canne roux", 0.4, "kg", 1.6)],
         "Nouvelle recette, à goûter à J+30."),
    ]
    lot_ids = []
    for i, (r, mac, emb, nb, statut, pv, pr, ingredients, notes) in enumerate(lots, 1):
        bottled = statut in ("embouteille", "epuise")
        cur = conn.execute(
            """INSERT INTO lots (numero, recette_id, recette_nom, date_maceration,
                date_embouteillage, dlc, nb_bouteilles, volume_cl, degre, statut, notes,
                materiaux_deduits, prix_vente_ttc, prix_revendeur_ht, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 50, ?, ?, ?, ?, ?, ?, ?)""",
            (f"MC-{year}-{i:03d}", recette_ids[r], recettes[r][0], d(mac),
             d(emb) if emb is not None else None,
             d(emb + 730) if emb is not None else None,
             nb, recettes[r][2], statut, notes, nb if bottled else 0, pv, pr, d(mac)),
        )
        lot_ids.append(cur.lastrowid)
        conn.executemany(
            "INSERT INTO lot_ingredients (lot_id, categorie, nom, quantite, unite, cout)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [(cur.lastrowid, *ing) for ing in ingredients],
        )

    conn.executemany(
        "INSERT INTO materiaux (nom, type, stock, seuil_alerte, cout_unitaire, par_bouteille)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("Bouteille flasque 50 cl", "bouteille", 46, 30, 1.20, 1),
            ("Bouchon liège tête bois", "bouchon", 112, 30, 0.45, 1),
            ("Étiquette avant + contre-étiquette", "etiquette", 18, 30, 0.38, 1),
            ("Étui kraft + calage", "emballage", 55, 20, 0.95, 1),
            ("Cire de scellage (pastille)", "autre", 140, 40, 0.12, 1),
        ],
    )

    # (lot index, jours, client, quantité, prix TTC, canal)
    ventes = [
        (0, -175, "Marché de Noël – stand", 6, 34.0, "direct"),
        (0, -160, "Cave Le Galion", 10, 22.0, "revendeur"),
        (0, -140, "Sophie M.", 2, 34.0, "direct"),
        (0, -110, "Épicerie fine Bâbord", 6, 22.0, "revendeur"),
        (1, -118, "Marché des producteurs", 5, 36.0, "direct"),
        (1, -90, "Cave Le Galion", 6, 23.0, "revendeur"),
        (1, -60, "Julien R.", 1, 36.0, "direct"),
        (1, -21, "Comité d'entreprise Atlantique", 3, 33.0, "direct"),
        (2, -70, "Épicerie fine Bâbord", 4, 24.0, "revendeur"),
        (2, -40, "Vente en ligne", 2, 38.0, "direct"),
        (2, -12, "Marché du port", 3, 38.0, "direct"),
        (2, -3, "Claire D.", 1, 38.0, "direct"),
    ]
    conn.executemany(
        "INSERT INTO ventes (date_vente, client, lot_id, quantite, prix_unitaire_ttc, canal)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [(d(days), client, lot_ids[li], q, p, canal)
         for li, days, client, q, p, canal in ventes],
    )
    # Une vente datée du jour même, pour que le CA du mois ne soit jamais vide.
    conn.execute(
        "INSERT INTO ventes (date_vente, client, lot_id, quantite, prix_unitaire_ttc, canal)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (today.isoformat(), "Vente à domicile", lot_ids[1], 2, 36.0, "direct"),
    )
