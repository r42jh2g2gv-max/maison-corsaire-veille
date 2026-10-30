"""Base de données SQLite : schéma, migrations et données d'exemple."""
import secrets
import sqlite3
from datetime import date, datetime, timedelta

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
    notes_degustation TEXT,
    instructions TEXT
);

CREATE TABLE IF NOT EXISTS recette_ingredients (
    id INTEGER PRIMARY KEY,
    recette_id INTEGER NOT NULL REFERENCES recettes(id) ON DELETE CASCADE,
    categorie TEXT NOT NULL,
    nom TEXT NOT NULL,
    quantite_par_litre REAL,
    unite TEXT,
    -- prix d'achat par unité (€/L, €/kg, €/pièce...) pour estimer le coût
    cout_unitaire REAL
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

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'particulier',
    email TEXT,
    telephone TEXT,
    adresse TEXT,
    notes TEXT,
    -- consentement à recevoir les nouveautés (RGPD)
    accepte_infos INTEGER NOT NULL DEFAULT 0,
    prix_revendeur_ht REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evenements (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'marche',
    date_debut TEXT NOT NULL,
    date_fin TEXT,
    lieu TEXT,
    cout_place REAL NOT NULL DEFAULT 0,
    btl_prevues INTEGER NOT NULL DEFAULT 0,
    date_limite_inscription TEXT,
    inscrit INTEGER NOT NULL DEFAULT 0,
    stock_pret INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS bons (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    beneficiaire TEXT,
    montant REAL NOT NULL,
    motif TEXT,
    date_emission TEXT NOT NULL,
    date_expiration TEXT,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE SET NULL,
    envoye_le TEXT
);

-- Un ticket = un encaissement (une ou plusieurs lignes de vente)
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    numero TEXT UNIQUE NOT NULL,
    date_vente TEXT NOT NULL,
    client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    client_nom TEXT NOT NULL,
    canal TEXT NOT NULL DEFAULT 'direct',
    mode_paiement TEXT NOT NULL DEFAULT 'especes',
    evenement_id INTEGER REFERENCES evenements(id) ON DELETE SET NULL,
    sous_total REAL NOT NULL DEFAULT 0,
    remise REAL NOT NULL DEFAULT 0,
    consigne REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    facture_numero TEXT UNIQUE,
    facture_date TEXT,
    client_adresse TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ventes (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    date_vente TEXT NOT NULL,
    client TEXT NOT NULL,
    lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    quantite INTEGER NOT NULL,
    prix_unitaire_ttc REAL NOT NULL,
    canal TEXT NOT NULL DEFAULT 'direct',
    notes TEXT
);

-- Bouteilles consignées : quantité > 0 = remise au client, < 0 = rapportée
CREATE TABLE IF NOT EXISTS consignes (
    id INTEGER PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    client_nom TEXT NOT NULL,
    date_mouvement TEXT NOT NULL,
    quantite INTEGER NOT NULL,
    montant_unitaire REAL NOT NULL,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    date_envoi TEXT NOT NULL,
    sujet TEXT NOT NULL,
    corps TEXT NOT NULL,
    nb_destinataires INTEGER NOT NULL DEFAULT 0,
    mode TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matieres_premieres (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    categorie TEXT NOT NULL DEFAULT 'autre',
    unite TEXT NOT NULL DEFAULT 'kg',
    seuil_alerte REAL NOT NULL DEFAULT 0,
    -- prix d'achat par unité de stock (dernier achat)
    cout_unitaire REAL NOT NULL DEFAULT 0,
    fournisseur TEXT,
    allergene TEXT,
    notes TEXT
);

-- Stock = somme des mouvements (achat +, utilisation -, ajustement +/-)
CREATE TABLE IF NOT EXISTS mouvements_mp (
    id INTEGER PRIMARY KEY,
    mp_id INTEGER NOT NULL REFERENCES matieres_premieres(id) ON DELETE CASCADE,
    date_mouvement TEXT NOT NULL,
    type TEXT NOT NULL,
    quantite REAL NOT NULL,
    lot_ingredient_id INTEGER REFERENCES lot_ingredients(id) ON DELETE CASCADE,
    achat_ligne_id INTEGER REFERENCES achat_lignes(id) ON DELETE CASCADE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS achats (
    id INTEGER PRIMARY KEY,
    date_achat TEXT NOT NULL,
    fournisseur TEXT NOT NULL,
    reference TEXT,
    mode_paiement TEXT NOT NULL DEFAULT 'carte',
    montant_total REAL NOT NULL DEFAULT 0,
    justificatif TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS achat_lignes (
    id INTEGER PRIMARY KEY,
    achat_id INTEGER NOT NULL REFERENCES achats(id) ON DELETE CASCADE,
    mp_id INTEGER REFERENCES matieres_premieres(id) ON DELETE SET NULL,
    materiau_id INTEGER REFERENCES materiaux(id) ON DELETE SET NULL,
    designation TEXT NOT NULL,
    quantite REAL,
    unite TEXT,
    montant REAL NOT NULL DEFAULT 0
);

-- Bouteilles sorties du stock sans vente : cadeau, concours, dégustation, casse...
CREATE TABLE IF NOT EXISTS sorties (
    id INTEGER PRIMARY KEY,
    date_sortie TEXT NOT NULL,
    lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
    quantite INTEGER NOT NULL,
    motif TEXT NOT NULL,
    beneficiaire TEXT,
    evenement_id INTEGER REFERENCES evenements(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS declarations (
    periode TEXT PRIMARY KEY,
    declare_le TEXT NOT NULL,
    montant REAL
);
"""

DEFAULT_SETTINGS = {
    "producteur_nom": "Maison Corsaire",
    "producteur_adresse": "12 rue des Flibustiers, 17000 La Rochelle",
    "producteur_email": "",
    "producteur_telephone": "",
    "siret": "",
    "iban": "",
    "tva_applicable": "0",
    "tva_taux": "20",
    "accise_hlap": "0",
    "secu_hlap": "0",
    "marge_direct": "60",
    "marge_revendeur": "40",
    "coef_revendeur": "1.8",
    "consigne_montant": "1",
    "urssaf_taux": "12.3",
    "cfp_taux": "0.1",
    "urssaf_periodicite": "mensuelle",
    "conditions_paiement": "Paiement à réception de facture.",
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_password": "",
    "smtp_expediteur": "",
    "etiquette_largeur": "70",
    "etiquette_hauteur": "75",
    "etiquette_tri": "Bouteille en verre et bouchon : à déposer dans le bac de tri.",
}

# Colonnes ajoutées après la première version : (table, colonne, définition)
MIGRATIONS = [
    ("recettes", "instructions", "TEXT"),
    ("recette_ingredients", "cout_unitaire", "REAL"),
    ("ventes", "ticket_id", "INTEGER REFERENCES tickets(id) ON DELETE CASCADE"),
    ("lot_ingredients", "mp_id", "INTEGER REFERENCES matieres_premieres(id) ON DELETE SET NULL"),
    ("recette_ingredients", "mp_id", "INTEGER REFERENCES matieres_premieres(id) ON DELETE SET NULL"),
    ("recettes", "denomination", "TEXT"),
    ("recettes", "etiquette_ingredients", "TEXT"),
    ("recettes", "allergenes", "TEXT"),
    ("recettes", "etiquette_mentions", "TEXT"),
    ("tickets", "uuid", "TEXT"),
    ("matieres_premieres", "nom_etiquette", "TEXT"),
    ("recettes", "perte_pct", "REAL"),
    ("lots", "volume_macere_l", "REAL"),
    ("lots", "perte_pct", "REAL"),
    ("lots", "volume_obtenu_l", "REAL"),
    ("matieres_premieres", "degre", "REAL"),
]


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


def migrer(conn):
    for table, colonne, definition in MIGRATIONS:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        if colonne not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {colonne} {definition}")
    # Les ventes de la première version n'avaient pas de ticket : on en crée un par vente.
    for v in conn.execute("SELECT * FROM ventes WHERE ticket_id IS NULL").fetchall():
        row = dict(v)
        total = row["quantite"] * row["prix_unitaire_ttc"]
        cur = conn.execute(
            """INSERT INTO tickets (numero, date_vente, client_nom, canal, mode_paiement,
               sous_total, total, created_at) VALUES (?, ?, ?, ?, 'especes', ?, ?, ?)""",
            (prochain_numero(conn, "tickets", "numero", "T", row["date_vente"][:4], 4),
             row["date_vente"], row["client"], row["canal"], total, total,
             datetime.now().isoformat(timespec="seconds")),
        )
        conn.execute("UPDATE ventes SET ticket_id = ? WHERE id = ?", (cur.lastrowid, row["id"]))


def prochain_numero(conn, table, colonne, prefixe, annee, chiffres):
    """Numérotation continue par année : T-2026-0001, F-2026-0001..."""
    debut = f"{prefixe}-{annee}-"
    row = conn.execute(
        f"SELECT {colonne} FROM {table} WHERE {colonne} LIKE ? ORDER BY {colonne} DESC LIMIT 1",
        (debut + "%",),
    ).fetchone()
    seq = int(row[0].rsplit("-", 1)[1]) + 1 if row else 1
    return f"{debut}{seq:0{chiffres}d}"


def code_bon():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "MC-" + "".join(secrets.choice(alphabet) for _ in range(4)) + "-" + \
        "".join(secrets.choice(alphabet) for _ in range(4))


def init_db(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    migrer(conn)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS tickets_uuid ON tickets(uuid)")
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    if not conn.execute("SELECT 1 FROM users").fetchone():
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (app.config["ADMIN_EMAIL"], generate_password_hash(app.config["ADMIN_PASSWORD"])),
        )
        seed_demo(conn)
    conn.commit()
    conn.close()


def clear_data(conn):
    """Supprime toutes les données métier (garde le compte et les réglages)."""
    for table in ("sorties", "consignes", "bons", "ventes", "tickets", "messages", "declarations",
                  "evenements", "clients", "mouvements_mp", "achat_lignes", "achats",
                  "lot_ingredients", "lots", "recette_ingredients", "recettes",
                  "matieres_premieres", "materiaux"):
        conn.execute(f"DELETE FROM {table}")


def seed_demo(conn):
    """Données d'exemple, datées par rapport à aujourd'hui."""
    today = date.today()
    now = datetime.now().isoformat(timespec="seconds")

    def d(days):
        return (today + timedelta(days=days)).isoformat()

    recettes = [
        ("Ananas – Vanille de Madagascar", 60, 32,
         "Nez gourmand de vanille, bouche ronde d'ananas rôti, finale douce.",
         "1. Peler l'ananas, le couper en cubes de 2 cm et le rôtir 10 min à 200 °C.\n"
         "2. Fendre les gousses de vanille et gratter les grains.\n"
         "3. Mettre fruits, vanille et sucre dans la bonbonne, couvrir de rhum.\n"
         "4. Remuer doucement une fois par semaine. Goûter à partir de J+45.\n"
         "5. Filtrer, laisser reposer 48 h puis embouteiller.",
         [("rhum", "Rhum agricole blanc 50°", 0.7, "L", 14.0),
          ("fruit", "Ananas Victoria", 0.35, "kg", 6.5),
          ("epice", "Gousse de vanille", 1, "pièce", 2.6),
          ("sucre", "Sucre de canne roux", 50, "g", 0.004)]),
        ("Mangue – Passion", 75, 30,
         "Explosion tropicale, acidité vive de la passion, très fruité.",
         "1. Couper la mangue en lamelles, évider les fruits de la passion.\n"
         "2. Ajouter le sirop de canne puis le rhum.\n"
         "3. Macérer à l'abri de la lumière, remuer chaque semaine.\n"
         "4. Filtrer finement (pulpe de passion) avant l'embouteillage.",
         [("rhum", "Rhum agricole blanc 50°", 0.7, "L", 14.0),
          ("fruit", "Mangue", 0.3, "kg", 6.0),
          ("fruit", "Fruit de la passion", 0.1, "kg", 12.0),
          ("sucre", "Sirop de canne", 40, "ml", 0.008)]),
        ("Café – Cacao", 75, 33,
         "Notes torréfiées, cacao amer, bel équilibre avec le rhum ambré.",
         "1. Concasser grossièrement les grains de café et les fèves de cacao.\n"
         "2. Mélanger avec le sucre, couvrir de rhum ambré.\n"
         "3. Goûter à J+30 : retirer le café si l'amertume domine.\n"
         "4. Filtrer au papier avant embouteillage.",
         [("rhum", "Rhum ambré 45°", 0.75, "L", 17.0),
          ("epice", "Grains de café arabica", 40, "g", 0.03),
          ("epice", "Fèves de cacao", 30, "g", 0.03),
          ("sucre", "Sucre de canne roux", 40, "g", 0.004)]),
        ("Coco – Citron vert", 45, 30,
         "Frais et soyeux, coco toastée et zeste de citron vert.",
         "1. Toaster la noix de coco râpée à sec à la poêle.\n"
         "2. Prélever les zestes de citron vert sans le blanc.\n"
         "3. Macérer avec le sucre et le rhum, remuer chaque semaine.\n"
         "4. Filtrer au tamis fin puis au papier.",
         [("rhum", "Rhum agricole blanc 50°", 0.7, "L", 14.0),
          ("fruit", "Noix de coco râpée toastée", 80, "g", 0.012),
          ("fruit", "Citron vert (zestes)", 2, "pièce", 0.3),
          ("sucre", "Sucre de canne roux", 40, "g", 0.004)]),
    ]
    recette_ids = []
    for nom, duree, degre, notes, instructions, ingredients in recettes:
        cur = conn.execute(
            "INSERT INTO recettes (nom, duree_maceration_jours, degre, notes_degustation, instructions)"
            " VALUES (?, ?, ?, ?, ?)",
            (nom, duree, degre, notes, instructions),
        )
        recette_ids.append(cur.lastrowid)
        conn.executemany(
            "INSERT INTO recette_ingredients"
            " (recette_id, categorie, nom, quantite_par_litre, unite, cout_unitaire)"
            " VALUES (?, ?, ?, ?, ?, ?)",
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
        (3, -46, None, 20, "maceration", None, None,
         [("rhum", "Rhum agricole blanc 50°", 7.0, "L", 98.0),
          ("fruit", "Noix de coco râpée toastée", 0.8, "kg", 9.6),
          ("fruit", "Citron vert (zestes)", 20, "pièce", 6.0),
          ("sucre", "Sucre de canne roux", 0.4, "kg", 1.6)],
         "Nouvelle recette, à goûter."),
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

    clients = [
        ("Cave Le Galion", "revendeur", "contact@cave-legalion.fr", "05 46 41 00 00",
         "4 quai Duperré, 17000 La Rochelle", "Commande toutes les 6 semaines environ.", 1, 22.0),
        ("Épicerie fine Bâbord", "revendeur", "bonjour@epicerie-babord.fr", "05 46 22 11 11",
         "18 rue du Port, 17300 Rochefort", "", 1, 22.0),
        ("Sophie Martin", "particulier", "sophie.martin@exemple.fr", "06 12 34 56 78",
         "", "Adore la Mangue – Passion.", 1, None),
        ("Julien Robert", "particulier", "julien.robert@exemple.fr", "06 98 76 54 32",
         "", "", 0, None),
        ("Claire Dubois", "particulier", "claire.dubois@exemple.fr", "",
         "", "Rencontrée au marché du port.", 1, None),
        ("Comité d'entreprise Atlantique", "professionnel", "ce@atlantique-exemple.fr",
         "05 46 00 00 00", "Zone industrielle, 17180 Périgny", "Coffrets de fin d'année.", 0, None),
    ]
    client_ids = []
    for c in clients:
        cur = conn.execute(
            """INSERT INTO clients (nom, type, email, telephone, adresse, notes, accepte_infos,
               prix_revendeur_ht, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*c, d(-260)),
        )
        client_ids.append(cur.lastrowid)

    evenements = [
        ("Marché de printemps", "marche", -175, None, "Place de Verdun, La Rochelle", 20, 20, None, 1, 1),
        ("Marché des producteurs", "marche", -118, None, "Halles de Rochefort", 15, 15, None, 1, 1),
        ("Marché du port", "marche", -12, None, "Vieux-Port, La Rochelle", 15, 12, None, 1, 1),
        ("Marché de producteurs de Surgères", "marche", 9, None, "Place du Château, Surgères",
         25, 30, 3, 0, 0),
        ("Dégustation chez Cave Le Galion", "degustation", 18, None, "Cave Le Galion, La Rochelle",
         0, 12, None, 1, 0),
        ("Salon gourmand de La Rochelle", "salon", 38, 40, "Espace Encan, La Rochelle",
         180, 60, 14, 0, 0),
        ("Marché de Noël de Rochefort", "marche", 45, 47, "Place Colbert, Rochefort",
         90, 50, 25, 0, 0),
    ]
    evt_ids = []
    for nom, typ, deb, fin, lieu, place, btl, limite, inscrit, pret in evenements:
        cur = conn.execute(
            """INSERT INTO evenements (nom, type, date_debut, date_fin, lieu, cout_place,
               btl_prevues, date_limite_inscription, inscrit, stock_pret)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nom, typ, d(deb), d(fin) if fin else None, lieu, place, btl,
             d(limite) if limite is not None else None, inscrit, pret),
        )
        evt_ids.append(cur.lastrowid)

    def ticket(jours, client_idx, nom, canal, paiement, lignes, evt=None, facture=False):
        date_vente = d(jours)
        sous_total = sum(q * p for _, q, p in lignes)
        client_id = client_ids[client_idx] if client_idx is not None else None
        adresse = clients[client_idx][4] if client_idx is not None else None
        cur = conn.execute(
            """INSERT INTO tickets (numero, date_vente, client_id, client_nom, canal, mode_paiement,
               evenement_id, sous_total, total, client_adresse, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (prochain_numero(conn, "tickets", "numero", "T", date_vente[:4], 4), date_vente,
             client_id, nom, canal, paiement, evt_ids[evt] if evt is not None else None,
             sous_total, sous_total, adresse, now),
        )
        tid = cur.lastrowid
        for li, q, p in lignes:
            conn.execute(
                "INSERT INTO ventes (ticket_id, date_vente, client, lot_id, quantite,"
                " prix_unitaire_ttc, canal) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tid, date_vente, nom, lot_ids[li], q, p, canal),
            )
        if facture:
            conn.execute(
                "UPDATE tickets SET facture_numero = ?, facture_date = ? WHERE id = ?",
                (prochain_numero(conn, "tickets", "facture_numero", "F", date_vente[:4], 4),
                 date_vente, tid),
            )
        return tid

    ticket(-175, None, "Clients du marché", "direct", "especes", [(0, 6, 34.0)], evt=0)
    ticket(-160, 0, "Cave Le Galion", "revendeur", "virement", [(0, 10, 22.0)], facture=True)
    ticket(-140, 2, "Sophie Martin", "direct", "carte", [(0, 2, 34.0)])
    ticket(-118, None, "Clients du marché", "direct", "especes", [(1, 5, 36.0)], evt=1)
    ticket(-110, 1, "Épicerie fine Bâbord", "revendeur", "virement", [(0, 6, 22.0)], facture=True)
    ticket(-90, 0, "Cave Le Galion", "revendeur", "virement", [(1, 6, 23.0)], facture=True)
    ticket(-70, 1, "Épicerie fine Bâbord", "revendeur", "cheque", [(2, 4, 24.0)], facture=True)
    ticket(-60, 3, "Julien Robert", "direct", "carte", [(1, 1, 36.0)])
    ticket(-40, 4, "Claire Dubois", "direct", "virement", [(2, 2, 38.0)])
    ticket(-21, 5, "Comité d'entreprise Atlantique", "direct", "virement",
           [(1, 3, 33.0), (2, 1, 35.0)], facture=True)
    ticket(-12, None, "Clients du marché", "direct", "especes", [(2, 3, 38.0)], evt=2)
    t_sophie = ticket(-3, 2, "Sophie Martin", "direct", "carte", [(1, 2, 36.0)])
    ticket(0, 4, "Claire Dubois", "direct", "carte", [(2, 1, 38.0)])

    # Consigne : Sophie a pris 2 bouteilles consignées et en a rapporté 1.
    consigne = 1.0
    conn.execute(
        "UPDATE tickets SET consigne = ?, total = total + ? WHERE id = ?",
        (2 * consigne, 2 * consigne, t_sophie),
    )
    conn.executemany(
        "INSERT INTO consignes (client_id, client_nom, date_mouvement, quantite, montant_unitaire,"
        " ticket_id) VALUES (?, ?, ?, ?, ?, ?)",
        [(client_ids[2], "Sophie Martin", d(-3), 2, consigne, t_sophie)],
    )
    conn.execute(
        "INSERT INTO consignes (client_id, client_nom, date_mouvement, quantite, montant_unitaire,"
        " notes) VALUES (?, ?, ?, ?, ?, ?)",
        (client_ids[2], "Sophie Martin", d(-1), -1, consigne, "Bouteille rapportée propre"),
    )
    conn.executemany(
        "INSERT INTO sorties (date_sortie, lot_id, quantite, motif, beneficiaire, evenement_id,"
        " notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(d(-12), lot_ids[2], 1, "degustation", None, evt_ids[2], "Bouteille ouverte au stand", now),
         (d(-30), lot_ids[1], 1, "casse", None, None, "Tombée au déchargement", now)])
    seed_matieres(conn, d)
    conn.execute("UPDATE recettes SET perte_pct = 15")
    for numero, macere, obtenu in [(1, 14, 12.1), (2, 13, 11.1), (3, 11.8, 10.2), (4, 14, None),
                                   (5, 12, None)]:
        conn.execute(
            "UPDATE lots SET volume_macere_l = ?, perte_pct = 15, volume_obtenu_l = ?"
            " WHERE numero = ?", (macere, obtenu, f"MC-{today.year}-{numero:03d}"))

    conn.executemany(
        "INSERT INTO bons (code, client_id, beneficiaire, montant, motif, date_emission,"
        " date_expiration) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (code_bon(), client_ids[2], "Sophie Martin", 10.0, "Fidélité : 5e bouteille",
             d(-20), d(20)),
            (code_bon(), client_ids[4], "Claire Dubois", 5.0, "Merci pour votre visite au marché",
             d(-10), d(170)),
        ],
    )

    # Déclaration URSSAF des mois déjà passés (sauf le dernier, pour le rappel)
    y, m = today.year, today.month
    for k in range(1, 8):
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
        if k == 1:
            continue
        conn.execute("INSERT OR IGNORE INTO declarations (periode, declare_le) VALUES (?, ?)",
                     (f"urssaf:{y}-{m:02d}", d(-30 * k + 25)))


def seed_matieres(conn, d):
    """Matières premières, achats et consommation des lots d'exemple."""
    from calculs import convertir

    matieres = [
        # nom, catégorie, unité, seuil, coût, fournisseur, allergène
        ("Rhum agricole blanc 50°", "rhum", "L", 10, 14.0, "Distillerie des Alizés", None),
        ("Rhum ambré 45°", "rhum", "L", 5, 17.0, "Distillerie des Alizés", None),
        ("Ananas Victoria", "fruit", "kg", 0, 6.5, "Primeur du marché", None),
        ("Mangue", "fruit", "kg", 0, 6.0, "Primeur du marché", None),
        ("Fruit de la passion", "fruit", "kg", 0, 12.0, "Primeur du marché", None),
        ("Gousse de vanille", "epice", "pièce", 10, 2.6, "Épices du Monde", None),
        ("Grains de café arabica", "epice", "kg", 0.3, 30.0, "Torréfaction Saint-Nicolas", None),
        ("Fèves de cacao", "epice", "kg", 0.2, 30.0, "Épices du Monde", None),
        ("Noix de coco râpée toastée", "fruit", "kg", 0.5, 12.0, "Épices du Monde", None),
        ("Citron vert (zestes)", "fruit", "pièce", 10, 0.3, "Primeur du marché", None),
        ("Sucre de canne roux", "sucre", "kg", 2, 4.0, "Épicerie en gros", None),
        ("Sirop de canne", "sucre", "L", 0.5, 8.0, "Épicerie en gros", None),
    ]
    ids = {}
    for nom, cat, unite, seuil, cout, fournisseur, allergene in matieres:
        cur = conn.execute(
            "INSERT INTO matieres_premieres (nom, categorie, unite, seuil_alerte, cout_unitaire,"
            " fournisseur, allergene) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nom, cat, unite, seuil, cout, fournisseur, allergene))
        ids[nom.lower()] = (cur.lastrowid, unite)

    now = datetime.now().isoformat(timespec="seconds")
    achats = [
        (-250, "Distillerie des Alizés", "FA-2026-118", "virement",
         [("Rhum agricole blanc 50°", 40, 560.0), ("Rhum ambré 45°", 10, 170.0)]),
        (-245, "Verrerie Atlantique", "V-88412", "carte",
         [("@Bouteille flasque 50 cl", 120, 144.0), ("@Bouchon liège tête bois", 200, 90.0)]),
        (-242, "Primeur du marché", None, "especes",
         [("Ananas Victoria", 4.2, 25.2), ("Sucre de canne roux", 5, 20.0)]),
        (-240, "Épices du Monde", "EM-5521", "carte",
         [("Gousse de vanille", 50, 130.0), ("Fèves de cacao", 0.5, 15.0),
          ("Noix de coco râpée toastée", 1, 12.0)]),
        (-201, "Primeur du marché", None, "especes",
         [("Mangue", 3.3, 19.8), ("Fruit de la passion", 1.1, 13.2), ("Sirop de canne", 1, 8.0)]),
        (-152, "Torréfaction Saint-Nicolas", "TSN-301", "carte",
         [("Grains de café arabica", 0.5, 15.0)]),
        (-120, "Imprimerie du Port", "IP-2026-044", "virement",
         [("@Étiquette avant + contre-étiquette", 100, 38.0)]),
        (-65, "Distillerie des Alizés", "FA-2026-301", "virement",
         [("Rhum agricole blanc 50°", 20, 280.0)]),
        (-63, "Primeur du marché", None, "especes", [("Ananas Victoria", 4.2, 27.3)]),
        (-47, "Primeur du marché", None, "especes",
         [("Citron vert (zestes)", 25, 7.5), ("Noix de coco râpée toastée", 0.5, 6.0)]),
    ]
    for jours, fournisseur, ref, paiement, lignes in achats:
        cur = conn.execute(
            "INSERT INTO achats (date_achat, fournisseur, reference, mode_paiement, montant_total,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (d(jours), fournisseur, ref, paiement, sum(l[2] for l in lignes), now))
        achat_id = cur.lastrowid
        for nom, qte, montant in lignes:
            if nom.startswith("@"):  # matière de conditionnement (stock déjà à jour)
                mat = conn.execute("SELECT id FROM materiaux WHERE nom = ?", (nom[1:],)).fetchone()
                conn.execute(
                    "INSERT INTO achat_lignes (achat_id, materiau_id, designation, quantite, unite,"
                    " montant) VALUES (?, ?, ?, ?, 'pièce', ?)",
                    (achat_id, mat[0] if mat else None, nom[1:], qte, montant))
                continue
            mp_id, unite = ids[nom.lower()]
            ligne = conn.execute(
                "INSERT INTO achat_lignes (achat_id, mp_id, designation, quantite, unite, montant)"
                " VALUES (?, ?, ?, ?, ?, ?)", (achat_id, mp_id, nom, qte, unite, montant))
            conn.execute(
                "INSERT INTO mouvements_mp (mp_id, date_mouvement, type, quantite, achat_ligne_id)"
                " VALUES (?, ?, 'achat', ?, ?)", (mp_id, d(jours), qte, ligne.lastrowid))

    # Les lots d'exemple consomment ces matières
    for ing in conn.execute(
            """SELECT i.*, l.date_maceration FROM lot_ingredients i
               JOIN lots l ON l.id = i.lot_id""").fetchall():
        trouve = ids.get(ing["nom"].lower())
        if not trouve:
            continue
        mp_id, unite = trouve
        qte = convertir(ing["quantite"] or 0, ing["unite"], unite)
        conn.execute("UPDATE lot_ingredients SET mp_id = ? WHERE id = ?", (mp_id, ing["id"]))
        if qte:
            conn.execute(
                "INSERT INTO mouvements_mp (mp_id, date_mouvement, type, quantite,"
                " lot_ingredient_id) VALUES (?, ?, 'utilisation', ?, ?)",
                (mp_id, ing["date_maceration"], -qte, ing["id"]))
    for ing in conn.execute("SELECT id, nom FROM recette_ingredients").fetchall():
        trouve = ids.get(ing["nom"].lower())
        if trouve:
            conn.execute("UPDATE recette_ingredients SET mp_id = ? WHERE id = ?",
                         (trouve[0], ing["id"]))
    for nom, etiquette in [
        ("Rhum agricole blanc 50°", "rhum agricole"), ("Rhum ambré 45°", "rhum ambré"),
        ("Ananas Victoria", "ananas"), ("Gousse de vanille", "vanille"),
        ("Grains de café arabica", "café"), ("Noix de coco râpée toastée", "noix de coco"),
        ("Citron vert (zestes)", "zestes de citron vert"), ("Sucre de canne roux", "sucre de canne"),
    ]:
        conn.execute("UPDATE matieres_premieres SET nom_etiquette = ? WHERE nom = ?", (etiquette, nom))
    conn.execute("UPDATE matieres_premieres SET degre = 50 WHERE nom = 'Rhum agricole blanc 50°'")
    conn.execute("UPDATE matieres_premieres SET degre = 45 WHERE nom = 'Rhum ambré 45°'")
    # Un écart d'inventaire corrigé, pour l'exemple
    conn.execute(
        "INSERT INTO mouvements_mp (mp_id, date_mouvement, type, quantite, notes)"
        " VALUES (?, ?, 'ajustement', ?, ?)",
        (ids["sucre de canne roux"][0], d(-30), -0.3, "Inventaire : sachet entamé jeté"))
