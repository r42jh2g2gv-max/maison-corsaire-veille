"""Rappels « À faire » : agenda, lots, stock, déclarations, bons, clients."""
from calendar import monthrange
from datetime import date, timedelta

from flask import url_for

from calculs import to_float
from noyau import MOIS_LONGS, euro


def _fin_de_mois(y, m):
    return date(y, m, monthrange(y, m)[1])


def periodes_urssaf(periodicite, nombre=12, reference=None):
    """Périodes terminées les plus récentes : [(clé, libellé, début, fin, échéance)]."""
    ref = reference or date.today()
    resultat = []
    if periodicite == "trimestrielle":
        t = (ref.month - 1) // 3  # trimestre en cours (0..3)
        y = ref.year
        for _ in range(nombre):
            t -= 1
            if t < 0:
                t, y = 3, y - 1
            debut = date(y, 3 * t + 1, 1)
            fin = _fin_de_mois(y, 3 * t + 3)
            em = 3 * t + 4
            ey = y + (1 if em > 12 else 0)
            em = em - 12 if em > 12 else em
            resultat.append((f"{y}-T{t + 1}", f"{t + 1}{'er' if t == 0 else 'e'} trimestre {y}",
                             debut, fin, _fin_de_mois(ey, em)))
    else:
        y, m = ref.year, ref.month
        for _ in range(nombre):
            y, m = (y, m - 1) if m > 1 else (y - 1, 12)
            ey, em = (y, m + 1) if m < 12 else (y + 1, 1)
            resultat.append((f"{y}-{m:02d}", f"{MOIS_LONGS[m - 1]} {y}", date(y, m, 1),
                             _fin_de_mois(y, m), _fin_de_mois(ey, em)))
    return resultat


def ca_periode(conn, debut, fin):
    return conn.execute(
        "SELECT COALESCE(SUM(sous_total - remise), 0) FROM tickets"
        " WHERE date_vente BETWEEN ? AND ?", (debut.isoformat(), fin.isoformat())
    ).fetchone()[0]


def calculer_rappels(conn, conf):
    ajd = date.today()
    rappels = []

    def ajouter(niveau, icone, titre, detail, echeance, lien):
        rappels.append({"niveau": niveau, "icone": icone, "titre": titre, "detail": detail,
                        "echeance": echeance.isoformat() if echeance else None, "lien": lien})

    # Agenda
    stock_total = conn.execute(
        """SELECT COALESCE(SUM(l.nb_bouteilles - COALESCE((SELECT SUM(quantite) FROM ventes v
             WHERE v.lot_id = l.id), 0)), 0) FROM lots l WHERE l.statut = 'embouteille'"""
    ).fetchone()[0]
    for e in conn.execute("SELECT * FROM evenements WHERE date_debut >= ? ORDER BY date_debut",
                          (ajd.isoformat(),)):
        jour = date.fromisoformat(e["date_debut"])
        delai = (jour - ajd).days
        lien = url_for("agenda") + f"#evt-{e['id']}"
        if not e["inscrit"]:
            if e["date_limite_inscription"]:
                limite = date.fromisoformat(e["date_limite_inscription"])
                if (limite - ajd).days <= 21:
                    niveau = "retard" if limite < ajd else ("urgent" if (limite - ajd).days <= 7
                                                            else "info")
                    ajouter(niveau, "calendrier", f"S'inscrire : {e['nom']}",
                            f"Le {jour:%d/%m/%Y} · {e['lieu'] or ''}".rstrip(" ·"), limite, lien)
            elif delai <= 30:
                ajouter("info", "calendrier", f"Confirmer l'inscription : {e['nom']}",
                        f"Le {jour:%d/%m/%Y}", jour, lien)
        if not e["stock_pret"] and delai <= 14 and e["btl_prevues"]:
            manque = e["btl_prevues"] > stock_total
            ajouter("urgent" if delai <= 3 or manque else "info", "caisse",
                    f"Préparer le stock : {e['nom']}",
                    f"{e['btl_prevues']} bouteille(s) prévue(s) · {stock_total} en stock"
                    + (" — stock insuffisant" if manque else ""),
                    jour - timedelta(days=1), lien)

    # Lots
    for l in conn.execute(
            """SELECT l.*, r.duree_maceration_jours AS duree FROM lots l
               LEFT JOIN recettes r ON r.id = l.recette_id
               WHERE l.statut IN ('maceration', 'pret')"""):
        lien = url_for("lot_detail", lot_id=l["id"])
        if l["statut"] == "pret":
            ajouter("urgent", "lot", f"Embouteiller le lot {l['numero']}",
                    f"{l['recette_nom']} · {l['nb_bouteilles']} bouteilles", None, lien)
        elif l["date_maceration"]:
            pret = date.fromisoformat(l["date_maceration"]) + timedelta(days=l["duree"] or 60)
            if (pret - ajd).days <= 7:
                ajouter("info", "lot", f"Goûter le lot {l['numero']}",
                        f"{l['recette_nom']} · macération prévue jusqu'au {pret:%d/%m}", pret, lien)

    # Stock de matières
    for m in conn.execute("SELECT * FROM materiaux WHERE stock <= seuil_alerte"):
        ajouter("urgent" if m["stock"] <= 0 else "info", "stock", f"Commander : {m['nom']}",
                f"Reste {m['stock']} · seuil {m['seuil_alerte']}", None,
                url_for("stock") + "#materiaux")

    # DLC / DDM proches pour des bouteilles encore en stock
    for l in conn.execute(
            """SELECT l.*, l.nb_bouteilles - COALESCE((SELECT SUM(quantite) FROM ventes v
                 WHERE v.lot_id = l.id), 0) AS reste FROM lots l
               WHERE l.statut = 'embouteille' AND l.dlc IS NOT NULL AND l.dlc <= ?""",
            ((ajd + timedelta(days=60)).isoformat(),)):
        if l["reste"] > 0:
            dlc = date.fromisoformat(l["dlc"])
            ajouter("retard" if dlc < ajd else "urgent", "lot", f"DLC proche : lot {l['numero']}",
                    f"{l['reste']} bouteille(s) de {l['recette_nom']}", dlc,
                    url_for("lot_detail", lot_id=l["id"]))

    # Déclaration URSSAF de la dernière période terminée
    periodicite = conf.get("urssaf_periodicite", "mensuelle")
    for cle, libelle, debut, fin, echeance in periodes_urssaf(periodicite, 3):
        if conn.execute("SELECT 1 FROM declarations WHERE periode = ?",
                        (f"urssaf:{cle}",)).fetchone():
            continue
        ca = ca_periode(conn, debut, fin)
        if ca <= 0 and echeance < ajd:
            continue
        taux = (to_float(conf.get("urssaf_taux")) + to_float(conf.get("cfp_taux"))) / 100
        ajouter("retard" if echeance < ajd else ("urgent" if (echeance - ajd).days <= 10
                                                 else "info"),
                "declaration", f"Déclarer le CA URSSAF : {libelle}",
                f"{euro(ca)} à déclarer · env. {euro(ca * taux)} de cotisations", echeance,
                url_for("chiffres", periode=cle))

    # Bons d'achat qui expirent bientôt
    for b in conn.execute(
            """SELECT * FROM bons WHERE ticket_id IS NULL AND date_expiration BETWEEN ? AND ?""",
            (ajd.isoformat(), (ajd + timedelta(days=30)).isoformat())):
        ajouter("info", "bon", "Bon d'achat bientôt expiré",
                f"{euro(b['montant'])} · {b['beneficiaire'] or b['code']} — pensez à le rappeler",
                date.fromisoformat(b["date_expiration"]),
                url_for("client_detail", client_id=b["client_id"]) if b["client_id"]
                else url_for("bons"))

    # Revendeurs sans commande depuis 45 jours
    for c in conn.execute(
            """SELECT c.*, (SELECT MAX(date_vente) FROM tickets t WHERE t.client_id = c.id) AS dernier
               FROM clients c WHERE c.type = 'revendeur'"""):
        if c["dernier"] and (ajd - date.fromisoformat(c["dernier"])).days >= 45:
            ajouter("info", "client", f"Relancer {c['nom']}",
                    f"Dernière commande il y a {(ajd - date.fromisoformat(c['dernier'])).days} jours",
                    None, url_for("client_detail", client_id=c["id"]))

    ordre = {"retard": 0, "urgent": 1, "info": 2}
    rappels.sort(key=lambda r: (ordre[r["niveau"]], r["echeance"] or "9999"))
    return rappels
