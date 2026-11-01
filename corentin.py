"""Corentin, l'agent de veille concurrentielle de Maison Corsaire.

Ce module fait la collecte automatique :
- il visite les pages publiques de chaque concurrent (site, pages produits, blog…) ;
- il en garde une « photo » (titre, description, titres de sections, prix repérés) ;
- il compare avec la photo précédente et enregistre chaque changement
  comme une observation dans la base de veille.

Utilisation en ligne de commande :
    python corentin.py collect      # visite les sites et enregistre les changements
    python corentin.py report       # affiche le rapport des 7 derniers jours
    python corentin.py competitors  # vérifie la liste des concurrents
"""

import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).parent
DB = BASE / "veille.db"
CONFIG = BASE / "competitors.json"
EXAMPLE_CONFIG = BASE / "competitors.example.json"

USER_AGENT = (
    "Mozilla/5.0 (compatible; CorentinVeille/1.0; "
    "veille concurrentielle Maison Corsaire)"
)
TIMEOUT = 20
PRICE_RE = re.compile(r"\d{1,5}(?:[ .  ]\d{3})*(?:[,.]\d{2})?\s?€")
MAX_ITEMS = 60


# --------------------------------------------------------------------------
# Base de données
# --------------------------------------------------------------------------

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            details TEXT,
            source_url TEXT,
            observed_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor TEXT NOT NULL,
            url TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            data TEXT NOT NULL,
            taken_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def add_observation(conn, competitor, category, title, details="", source_url=""):
    cursor = conn.execute(
        """
        INSERT INTO observations
        (competitor, category, title, details, source_url, observed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (competitor, category, title, details, source_url, now_iso()),
    )
    conn.commit()
    return cursor.lastrowid


# --------------------------------------------------------------------------
# Concurrents
# --------------------------------------------------------------------------

class ConfigMissing(Exception):
    pass


def competitors():
    if not CONFIG.exists():
        raise ConfigMissing(
            "Le fichier competitors.json est absent. Copiez "
            "competitors.example.json en competitors.json puis "
            "remplissez-le avec vos concurrents."
        )
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    for competitor in data:
        competitor.setdefault("instagram", "")
        competitor.setdefault("website", "")
        competitor.setdefault("pages", [])
    return data


def urls_for(competitor):
    urls = []
    if competitor.get("website"):
        urls.append(competitor["website"])
    for page in competitor.get("pages", []):
        if page and page not in urls:
            urls.append(page)
    return urls


# --------------------------------------------------------------------------
# Photo d'une page
# --------------------------------------------------------------------------

def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _unique(items):
    seen, result = set(), []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result[:MAX_ITEMS]


def extract(html):
    """Transforme une page HTML en photo comparable."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    headings = _unique(
        _clean(h.get_text(" ")) for h in soup.find_all(["h1", "h2", "h3"])
    )
    text = _clean(soup.get_text(" "))
    prices = _unique(_clean(p) for p in PRICE_RE.findall(text))

    return {
        "title": _clean(soup.title.get_text()) if soup.title else "",
        "description": _clean(meta.get("content", "")) if meta else "",
        "headings": headings,
        "prices": prices,
    }


def fingerprint(snapshot):
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fetch(url):
    response = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.text


# --------------------------------------------------------------------------
# Comparaison
# --------------------------------------------------------------------------

def _list(items):
    return "\n".join(f"• {item}" for item in items[:15])


def compare(old, new):
    """Retourne la liste des changements (catégorie, titre, détails)."""
    changes = []

    if old["title"] != new["title"] and new["title"]:
        changes.append((
            "site", "Titre de page modifié",
            f"Avant : {old['title']}\nAprès : {new['title']}",
        ))
    if old["description"] != new["description"] and new["description"]:
        changes.append((
            "marketing", "Message d'accroche modifié",
            f"Avant : {old['description']}\nAprès : {new['description']}",
        ))

    added = [h for h in new["headings"] if h not in old["headings"]]
    removed = [h for h in old["headings"] if h not in new["headings"]]
    if added:
        changes.append((
            "produit", f"{len(added)} nouvelle(s) rubrique(s) / nouveauté(s)",
            _list(added),
        ))
    if removed:
        changes.append((
            "produit", f"{len(removed)} rubrique(s) retirée(s)", _list(removed),
        ))

    new_prices = [p for p in new["prices"] if p not in old["prices"]]
    gone_prices = [p for p in old["prices"] if p not in new["prices"]]
    if new_prices or gone_prices:
        details = []
        if new_prices:
            details.append("Nouveaux prix affichés :\n" + _list(new_prices))
        if gone_prices:
            details.append("Prix disparus :\n" + _list(gone_prices))
        changes.append(("prix", "Changement de prix affichés", "\n".join(details)))

    return changes


# --------------------------------------------------------------------------
# Collecte
# --------------------------------------------------------------------------

def last_snapshot(conn, competitor, url):
    row = conn.execute(
        """
        SELECT data, content_hash FROM snapshots
        WHERE competitor = ? AND url = ?
        ORDER BY id DESC LIMIT 1
        """,
        (competitor, url),
    ).fetchone()
    if not row:
        return None, None
    return json.loads(row["data"]), row["content_hash"]


def collect(fetcher=fetch):
    """Visite toutes les pages suivies et enregistre les changements.

    Retourne un résumé lisible de la collecte.
    """
    conn = db()
    summary = []

    try:
        targets = competitors()
    except ConfigMissing as error:
        conn.close()
        return str(error)

    for competitor in targets:
        name = competitor["name"]
        urls = urls_for(competitor)
        if not urls:
            summary.append(f"⚠️ {name} : aucune page à surveiller (ajoutez 'website' ou 'pages').")
            continue

        for url in urls:
            try:
                snapshot = extract(fetcher(url))
            except Exception as error:  # site indisponible, blocage, etc.
                summary.append(f"⚠️ {name} — {url} : inaccessible ({error.__class__.__name__}).")
                continue

            digest = fingerprint(snapshot)
            previous, previous_digest = last_snapshot(conn, name, url)

            if previous is None:
                summary.append(f"📸 {name} — {url} : première photo enregistrée.")
            elif digest == previous_digest:
                summary.append(f"= {name} — {url} : aucun changement.")
                continue
            else:
                changes = compare(previous, snapshot)
                for category, title, details in changes:
                    add_observation(conn, name, category, title, details, url)
                summary.append(
                    f"🔔 {name} — {url} : {len(changes)} changement(s) enregistré(s)."
                )

            conn.execute(
                """
                INSERT INTO snapshots (competitor, url, content_hash, data, taken_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, url, digest, json.dumps(snapshot, ensure_ascii=False), now_iso()),
            )
            conn.commit()

    conn.close()
    return "\n".join(summary) if summary else "Aucun concurrent à surveiller."


# --------------------------------------------------------------------------
# Rapport
# --------------------------------------------------------------------------

def weekly_report(days=7):
    conn = db()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT * FROM observations
        WHERE observed_at >= ?
        ORDER BY competitor, observed_at DESC
        """,
        (since,),
    ).fetchall()
    conn.close()

    if not rows:
        return f"Aucune observation enregistrée pendant les {days} derniers jours."

    grouped = {}
    for row in rows:
        grouped.setdefault(row["competitor"], []).append(dict(row))

    report = [
        "# Veille concurrentielle Maison Corsaire",
        "",
        f"Période : {since[:10]} → {datetime.now().date()}",
        f"{len(rows)} observation(s) sur {len(grouped)} concurrent(s).",
        "",
    ]
    for competitor, observations in grouped.items():
        report.append(f"## {competitor}")
        for observation in observations:
            report.append(f"- [{observation['category']}] {observation['title']}")
            if observation["details"]:
                for line in observation["details"].splitlines():
                    report.append(f"  {line}")
            if observation["source_url"]:
                report.append(f"  Source : {observation['source_url']}")
        report.append("")
    return "\n".join(report)


# --------------------------------------------------------------------------
# Ligne de commande
# --------------------------------------------------------------------------

def main(argv):
    command = argv[1] if len(argv) > 1 else "help"
    if command == "collect":
        print(collect())
    elif command == "report":
        print(weekly_report())
    elif command == "competitors":
        try:
            for competitor in competitors():
                pages = urls_for(competitor)
                print(f"- {competitor['name']} : {len(pages)} page(s) suivie(s)")
        except ConfigMissing as error:
            print(error)
            return 1
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
