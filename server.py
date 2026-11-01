"""Serveur MCP de Corentin, l'agent de veille de Maison Corsaire."""

import json
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP

import corentin
from corentin import ConfigMissing

mcp = FastMCP("Corentin - Veille Maison Corsaire")


def _competitors_or_error():
    try:
        return corentin.competitors(), None
    except ConfigMissing as error:
        return None, str(error)


@mcp.tool()
def list_competitors() -> str:
    """Liste les concurrents Maison Corsaire suivis par Corentin."""
    data, error = _competitors_or_error()
    if error:
        return error
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def get_competitor(name: str) -> str:
    """Retourne les informations d'un concurrent (par nom ou compte Instagram)."""
    data, error = _competitors_or_error()
    if error:
        return error

    wanted = name.strip().lower().lstrip("@")
    for competitor in data:
        handle = competitor.get("instagram", "").rstrip("/").split("/")[-1].lower()
        if competitor["name"].lower() == wanted or (handle and handle == wanted):
            return json.dumps(competitor, ensure_ascii=False, indent=2)
    return f"Concurrent introuvable : {name}"


@mcp.tool()
def collect_now() -> str:
    """Visite les sites des concurrents et enregistre automatiquement les changements."""
    return corentin.collect()


@mcp.tool()
def add_observation(
    competitor: str,
    category: str,
    title: str,
    details: str = "",
    source_url: str = "",
) -> str:
    """Enregistre une observation de veille (catégories conseillées :
    prix, produit, marketing, réseaux sociaux, recrutement, site)."""
    conn = corentin.db()
    observation_id = corentin.add_observation(
        conn, competitor, category, title, details, source_url
    )
    conn.close()
    return f"Observation enregistrée : #{observation_id}"


@mcp.tool()
def search_observations(query: str = "", competitor: str = "", days: int = 30) -> str:
    """Recherche les observations récentes."""
    conn = corentin.db()
    since = (datetime.now() - timedelta(days=max(1, days))).isoformat()

    sql = "SELECT * FROM observations WHERE observed_at >= ?"
    params = [since]
    if competitor:
        sql += " AND competitor LIKE ?"
        params.append(f"%{competitor}%")
    if query:
        sql += " AND (title LIKE ? OR details LIKE ? OR category LIKE ?)"
        params.extend([f"%{query}%"] * 3)
    sql += " ORDER BY observed_at DESC LIMIT 200"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2)


@mcp.tool()
def weekly_report() -> str:
    """Génère le rapport hebdomadaire de veille Maison Corsaire."""
    return corentin.weekly_report()


if __name__ == "__main__":
    corentin.db().close()
    mcp.run()
