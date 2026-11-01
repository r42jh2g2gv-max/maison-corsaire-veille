"""Prévision de production : combien de bouteilles manqueront, et quand lancer les lots."""
from datetime import date, timedelta

from flask import render_template, request

from calculs import PERTE_DEFAUT
from noyau import app, get_db, lots_avec_stock, stock_lot, to_int

DELAI_EMBOUTEILLAGE = 3  # jours entre la fin de macération et les bouteilles prêtes


def prevision(conn, horizon=150):
    ajd = date.today()
    fin = ajd + timedelta(days=horizon)

    stock = sum(stock_lot(l) for l in lots_avec_stock("WHERE l.statut = 'embouteille'"))
    # Lots en cours : bouteilles disponibles à leur date de fin estimée
    en_cours = []
    for l in conn.execute(
            """SELECT l.*, r.duree_maceration_jours AS duree FROM lots l
               LEFT JOIN recettes r ON r.id = l.recette_id
               WHERE l.statut IN ('maceration', 'pret') AND COALESCE(l.essai, 0) = 0"""):
        if l["statut"] == "pret" or not l["date_maceration"]:
            prete = ajd
        else:
            prete = (date.fromisoformat(l["date_maceration"])
                     + timedelta(days=(l["duree"] or 60) + DELAI_EMBOUTEILLAGE))
        en_cours.append({"lot": l, "date": max(prete, ajd), "btl": l["nb_bouteilles"] or 0})

    # Ventes hors marchés : moyenne des 3 derniers mois
    il_y_a_3_mois = (ajd - timedelta(days=91)).isoformat()
    courantes = conn.execute(
        """SELECT COALESCE(SUM(v.quantite), 0) FROM ventes v JOIN tickets t ON t.id = v.ticket_id
           WHERE t.date_vente >= ? AND t.evenement_id IS NULL""", (il_y_a_3_mois,)).fetchone()[0]
    par_jour = courantes / 91

    # Répartition par recette : ventes des 12 derniers mois
    parts = conn.execute(
        """SELECT r.id, r.nom, r.duree_maceration_jours AS duree, r.perte_pct,
                  COALESCE((SELECT SUM(v.quantite) FROM ventes v JOIN lots l ON l.id = v.lot_id
                            WHERE l.recette_id = r.id AND v.date_vente >= ?), 0) AS vendues
           FROM recettes r ORDER BY vendues DESC, r.nom""",
        ((ajd - timedelta(days=365)).isoformat(),)).fetchall()
    total_parts = sum(p["vendues"] for p in parts)

    evenements = conn.execute(
        """SELECT * FROM evenements WHERE date_debut >= ? AND date_debut <= ? AND btl_prevues > 0
           ORDER BY date_debut""", (ajd.isoformat(), fin.isoformat())).fetchall()
    besoin_cumule = 0
    etapes = []
    for e in evenements:
        jour = date.fromisoformat(e["date_debut"])
        besoin_cumule += e["btl_prevues"]
        besoin = besoin_cumule + round(par_jour * (jour - ajd).days)
        disponible = stock + sum(x["btl"] for x in en_cours if x["date"] <= jour)
        manque = max(besoin - disponible, 0)
        conseils = []
        if manque:
            for p in parts:
                part = (p["vendues"] / total_parts) if total_parts else 1 / max(len(parts), 1)
                btl = round(manque * part)
                if btl <= 0:
                    continue
                perte = (p["perte_pct"] if p["perte_pct"] is not None else PERTE_DEFAUT) / 100
                litres = round(btl * 0.5 / max(1 - perte, 0.05), 1)
                lancer = jour - timedelta(days=(p["duree"] or 60) + DELAI_EMBOUTEILLAGE)
                conseils.append({"recette_id": p["id"], "recette": p["nom"], "btl": btl,
                                 "litres": litres, "lancer_avant": lancer.isoformat(),
                                 "trop_tard": lancer < ajd})
        etapes.append({"e": e, "besoin": besoin, "disponible": disponible, "manque": manque,
                       "conseils": conseils})
    return {"stock": stock, "en_cours": en_cours, "par_mois": round(par_jour * 30.4),
            "etapes": etapes, "horizon": horizon}


@app.route("/prevision")
def prevision_vue():
    conn = get_db()
    horizon = min(max(to_int(request.args.get("jours"), 150), 30), 365)
    return render_template("prevision.html", p=prevision(conn, horizon))


def rappels_prevision(conn):
    """Lots à lancer dans les 14 jours pour couvrir les prochains marchés."""
    ajd = date.today()
    sortie = []
    for etape in prevision(conn)["etapes"]:
        for c in etape["conseils"]:
            lancer = date.fromisoformat(c["lancer_avant"])
            if (lancer - ajd).days <= 14:
                sortie.append((etape["e"], c))
    return sortie
