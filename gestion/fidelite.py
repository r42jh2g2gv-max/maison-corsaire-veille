"""Carte de fidélité : 1 tampon par bouteille achetée, un bon d'achat automatique au seuil."""
from datetime import date, timedelta

from calculs import to_float
from db import code_bon


def regles(conf):
    return {
        "active": conf.get("fidelite_active", "1") == "1",
        "seuil": max(int(to_float(conf.get("fidelite_seuil"), 10)), 1),
        "montant": max(to_float(conf.get("fidelite_montant"), 5), 0),
        "validite": max(int(to_float(conf.get("fidelite_validite"), 365)), 1),
        "bonus_consigne": conf.get("fidelite_bonus_consigne", "1") == "1",
    }


def carte(conn, client_id, conf):
    """État de la carte : tampons gagnés, bons déjà générés, tampons en cours."""
    r = regles(conf)
    achetees = conn.execute(
        """SELECT COALESCE(SUM(v.quantite), 0) FROM ventes v JOIN tickets t ON t.id = v.ticket_id
           WHERE t.client_id = ? AND t.canal = 'direct'""", (client_id,)).fetchone()[0]
    rapportees = conn.execute(
        "SELECT COALESCE(SUM(-quantite), 0) FROM consignes WHERE client_id = ? AND quantite < 0",
        (client_id,)).fetchone()[0] if r["bonus_consigne"] else 0
    bons = conn.execute("SELECT COUNT(*) FROM bons WHERE client_id = ? AND origine = 'fidelite'",
                        (client_id,)).fetchone()[0]
    total = achetees + rapportees
    en_cours = max(total - bons * r["seuil"], 0)
    return {"total": total, "achetees": achetees, "rapportees": rapportees, "bons": bons,
            "tampons": min(en_cours, r["seuil"]), "a_generer": en_cours // r["seuil"],
            "seuil": r["seuil"], "montant": r["montant"], "active": r["active"]}


def attribuer_bons(conn, client_id, conf, jour=None):
    """Crée les bons gagnés (appelé après chaque vente). Retourne la liste des codes créés."""
    if not client_id:
        return []
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    r = regles(conf)
    if not client or not r["active"] or client["type"] == "revendeur" or not r["montant"]:
        return []
    etat = carte(conn, client_id, conf)
    crees = []
    debut = date.fromisoformat(jour) if jour else date.today()
    for _ in range(etat["a_generer"]):
        code = code_bon()
        while conn.execute("SELECT 1 FROM bons WHERE code = ?", (code,)).fetchone():
            code = code_bon()
        conn.execute(
            "INSERT INTO bons (code, client_id, beneficiaire, montant, motif, date_emission,"
            " date_expiration, origine) VALUES (?, ?, ?, ?, ?, ?, ?, 'fidelite')",
            (code, client_id, client["nom"], r["montant"],
             f"Carte de fidélité : {r['seuil']} tampons", debut.isoformat(),
             (debut + timedelta(days=r["validite"])).isoformat()))
        crees.append(code)
    return crees


def bons_actifs(conn, client_id):
    return conn.execute(
        """SELECT code, montant, date_expiration FROM bons WHERE client_id = ? AND ticket_id IS NULL
           AND (date_expiration IS NULL OR date_expiration >= date('now', 'localtime'))
           ORDER BY date_expiration""", (client_id,)).fetchall()
