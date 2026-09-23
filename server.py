import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from mcp.server.fastmcp import FastMCP

BASE = Path(__file__).parent
DB = BASE / "veille.db"
CONFIG = BASE / "competitors.json"

mcp = FastMCP("Maison Corsaire - Veille")


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

    conn.commit()
    return conn


def competitors():
    return json.loads(
        CONFIG.read_text(encoding="utf-8")
    )


@mcp.tool()
def list_competitors() -> str:
    """Liste les concurrents Maison Corsaire."""
    return json.dumps(
        competitors(),
        ensure_ascii=False,
        indent=2
    )


@mcp.tool()
def get_competitor(name: str) -> str:
    """Retourne les informations d'un concurrent."""
    wanted = name.strip().lower().lstrip("@")

    for competitor in competitors():
        instagram = competitor["instagram"].rstrip("/")
        handle = instagram.split("/")[-1].lower()

        if (
            competitor["name"].lower() == wanted
            or handle == wanted
        ):
            return json.dumps(
                competitor,
                ensure_ascii=False,
                indent=2
            )

    return f"Concurrent introuvable : {name}"


@mcp.tool()
def add_observation(
    competitor: str,
    category: str,
    title: str,
    details: str = "",
    source_url: str = ""
) -> str:
    """Enregistre une observation de veille."""
    conn = db()

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor = conn.execute(
        """
        INSERT INTO observations
        (competitor, category, title, details,
         source_url, observed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            competitor,
            category,
            title,
            details,
            source_url,
            now
        )
    )

    conn.commit()
    conn.close()

    return f"Observation enregistrée : #{cursor.lastrowid}"


@mcp.tool()
def search_observations(
    query: str = "",
    competitor: str = "",
    days: int = 30
) -> str:
    """Recherche les observations récentes."""

    conn = db()

    since = (
        datetime.now()
        - timedelta(days=max(1, days))
    ).isoformat()

    sql = """
        SELECT *
        FROM observations
        WHERE observed_at >= ?
    """

    params = [since]

    if competitor:
        sql += " AND competitor LIKE ?"
        params.append(f"%{competitor}%")

    if query:
        sql += """
        AND (
            title LIKE ?
            OR details LIKE ?
            OR category LIKE ?
        )
        """

        search = f"%{query}%"

        params.extend([
            search,
            search,
            search
        ])

    sql += """
        ORDER BY observed_at DESC
        LIMIT 200
    """

    rows = conn.execute(
        sql,
        params
    ).fetchall()

    conn.close()

    return json.dumps(
        [dict(row) for row in rows],
        ensure_ascii=False,
        indent=2
    )


@mcp.tool()
def weekly_report() -> str:
    """Génère le rapport hebdomadaire Maison Corsaire."""

    conn = db()

    since = (
        datetime.now()
        - timedelta(days=7)
    ).isoformat()

    rows = conn.execute(
        """
        SELECT *
        FROM observations
        WHERE observed_at >= ?
        ORDER BY competitor, observed_at DESC
        """,
        (since,)
    ).fetchall()

    conn.close()

    if not rows:
        return (
            "Aucune observation enregistrée "
            "pendant les 7 derniers jours."
        )

    grouped = {}

    for row in rows:
        grouped.setdefault(
            row["competitor"],
            []
        ).append(dict(row))

    report = [
        "# Veille concurrentielle Maison Corsaire",
        "",
        f"Période : {since[:10]} "
        f"→ {datetime.now().date()}",
        ""
    ]

    for competitor, observations in grouped.items():

        report.append(
            f"## {competitor}"
        )

        for observation in observations:

            report.append(
                f"- [{observation['category']}] "
                f"{observation['title']}"
            )

            if observation["details"]:
                report.append(
                    f"  {observation['details']}"
                )

            if observation["source_url"]:
                report.append(
                    f"  Source : "
                    f"{observation['source_url']}"
                )

        report.append("")

    return "\n".join(report)


if __name__ == "__main__":
    db().close()
    mcp.run()
