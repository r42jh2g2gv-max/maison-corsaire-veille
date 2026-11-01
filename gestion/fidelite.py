"""Fidélité : un achat de 3 bouteilles (ou d'un coffret) donne un bon pour le prochain passage.
Le bon est soit un montant (5 €), soit une remise en pourcentage (10 %)."""
from datetime import date, timedelta

from calculs import to_float
from db import code_bon
from noyau import app, euro


def regles(conf):
    return {
        "active": conf.get("fidelite_active", "1") == "1",
        "seuil": max(int(to_float(conf.get("fidelite_seuil"), 3)), 1),
        "coffret": conf.get("fidelite_coffret", "1") == "1",
        "type": "pourcentage" if conf.get("fidelite_type") == "pourcentage" else "montant",
        "montant": max(to_float(conf.get("fidelite_montant"), 5), 0),
        "pourcentage": min(max(to_float(conf.get("fidelite_pourcentage"), 10), 0), 100),
        "validite": max(int(to_float(conf.get("fidelite_validite"), 365)), 1),
    }


def texte_avantage(r):
    if r["type"] == "pourcentage":
        return f"{to_float(r['pourcentage']):g} % de remise"
    return f"un bon de {euro(r['montant'])}"


def texte_condition(r):
    return f"{r['seuil']} bouteilles" + (" ou un coffret" if r["coffret"] else "") + " achetés"


def valeur_bon(bon):
    """« 5,00 € » ou « 10 % » selon le bon."""
    if bon["pourcentage"]:
        return f"{to_float(bon['pourcentage']):g} %"
    return euro(bon["montant"])


def remise_bon(bon, sous_total):
    if bon["pourcentage"]:
        return round(sous_total * bon["pourcentage"] / 100, 2)
    return round(min(bon["montant"], sous_total), 2)


app.jinja_env.globals["valeur_bon"] = valeur_bon


def fidelite_caisse(conf):
    r = regles(conf)
    return {"active": r["active"], "seuil": r["seuil"], "coffret": r["coffret"],
            "avantage": texte_avantage(r)}


def carte(conn, client_id, conf):
    """Ce que le client sait de son avantage fidélité."""
    r = regles(conf)
    gagnes = conn.execute("SELECT COUNT(*) FROM bons WHERE client_id = ? AND origine = 'fidelite'",
                          (client_id,)).fetchone()[0]
    return {"active": r["active"], "seuil": r["seuil"], "coffret": r["coffret"],
            "avantage": texte_avantage(r), "condition": texte_condition(r), "bons": gagnes,
            "actifs": bons_actifs(conn, client_id) if client_id else []}


def merite_bon(conf, bouteilles, avec_coffret, canal="direct"):
    r = regles(conf)
    if not r["active"] or canal != "direct":
        return False
    if r["type"] == "montant" and not r["montant"]:
        return False
    if r["type"] == "pourcentage" and not r["pourcentage"]:
        return False
    return bouteilles >= r["seuil"] or (r["coffret"] and avec_coffret)


def creer_bon_fidelite(conn, conf, ticket_id, client, jour=None):
    """Crée le bon gagné par ce ticket (nominatif si le client a une fiche, sinon au porteur)."""
    r = regles(conf)
    debut = date.fromisoformat(jour) if jour else date.today()
    code = code_bon()
    while conn.execute("SELECT 1 FROM bons WHERE code = ?", (code,)).fetchone():
        code = code_bon()
    conn.execute(
        "INSERT INTO bons (code, client_id, beneficiaire, montant, pourcentage, motif,"
        " date_emission, date_expiration, origine, ticket_origine)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'fidelite', ?)",
        (code, client["id"] if client else None, client["nom"] if client else None,
         r["montant"] if r["type"] == "montant" else 0,
         r["pourcentage"] if r["type"] == "pourcentage" else None,
         "Fidélité : " + texte_condition(r), debut.isoformat(),
         (debut + timedelta(days=r["validite"])).isoformat(), ticket_id))
    return code


def bon_gagne(conn, ticket_id):
    return conn.execute("SELECT * FROM bons WHERE ticket_origine = ? AND origine = 'fidelite'",
                        (ticket_id,)).fetchone()


def bons_actifs(conn, client_id):
    return conn.execute(
        """SELECT code, montant, pourcentage, date_expiration FROM bons
           WHERE client_id = ? AND ticket_id IS NULL
           AND (date_expiration IS NULL OR date_expiration >= date('now', 'localtime'))
           ORDER BY date_expiration""", (client_id,)).fetchall()
