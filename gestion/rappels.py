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
    """Chiffre d'affaires encaissé sur la période (micro-entreprise : à la date du paiement),
    moins les avoirs remboursés."""
    d, f = debut.isoformat(), fin.isoformat()
    encaisse = conn.execute(
        "SELECT COALESCE(SUM(sous_total - remise), 0) FROM tickets"
        " WHERE paye = 1 AND COALESCE(date_paiement, date_vente) BETWEEN ? AND ?", (d, f)
    ).fetchone()[0]
    avoirs = conn.execute(
        "SELECT COALESCE(SUM(montant), 0) FROM avoirs WHERE date_avoir BETWEEN ? AND ?", (d, f)
    ).fetchone()[0]
    return encaisse - avoirs


def calculer_rappels(conn, conf):
    ajd = date.today()
    rappels = []

    def ajouter(niveau, icone, titre, detail, echeance, lien):
        rappels.append({"niveau": niveau, "icone": icone, "titre": titre, "detail": detail,
                        "echeance": echeance.isoformat() if echeance else None, "lien": lien})

    # Agenda
    stock_total = conn.execute(
        """SELECT COALESCE(SUM(l.nb_bouteilles - COALESCE((SELECT SUM(quantite) FROM ventes v
             WHERE v.lot_id = l.id), 0) - COALESCE((SELECT SUM(quantite) FROM sorties s
             WHERE s.lot_id = l.id), 0) - COALESCE((SELECT SUM(CASE type WHEN 'depot' THEN quantite
             ELSE -quantite END) FROM depots dp WHERE dp.lot_id = l.id), 0)), 0)
             FROM lots l WHERE l.statut = 'embouteille'"""
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

    # Prévision de production : lots à lancer pour couvrir les prochains marchés
    from vues_prevision import rappels_prevision
    for evt, conseil in rappels_prevision(conn):
        lancer = date.fromisoformat(conseil["lancer_avant"])
        ajouter("retard" if conseil["trop_tard"] else "urgent", "lot",
                f"Lancer {conseil['litres']:g} L de {conseil['recette']}",
                f"≈ {conseil['btl']} bouteilles pour {evt['nom']} ({date.fromisoformat(evt['date_debut']):%d/%m})",
                lancer, url_for("prevision_vue"))

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

    # Matières premières sous le seuil (rhum, épices, sucre...)
    for m in conn.execute(
            """SELECT m.*, COALESCE((SELECT SUM(quantite) FROM mouvements_mp v
                 WHERE v.mp_id = m.id), 0) AS stock FROM matieres_premieres m
               WHERE m.seuil_alerte > 0"""):
        if m["stock"] <= m["seuil_alerte"]:
            ajouter("urgent" if m["stock"] <= 0 else "info", "stock", f"Racheter : {m['nom']}",
                    f"Reste {m['stock']:g} {m['unite']} · seuil {m['seuil_alerte']:g}"
                    + (f" · {m['fournisseur']}" if m["fournisseur"] else ""), None,
                    url_for("matiere_detail", mp_id=m["id"]))

    # Hausse de prix d'un ingrédient (dernier achat ≥ 10 % plus cher)
    from vues_matieres import hausses_prix
    for h in hausses_prix(conn):
        ajouter("info", "stock", f"Hausse du prix : {h['mp']['nom']} {h['variation']:+.0f} %",
                f"{euro(h['avant'])} → {euro(h['apres'])} / {h['mp']['unite']}"
                + (f" · vérifiez le prix de : {', '.join(h['recettes'])}" if h["recettes"] else ""),
                None, url_for("matiere_detail", mp_id=h["mp"]["id"]) + "#prix")

    # DLC / DDM proches pour des bouteilles encore en stock
    for l in conn.execute(
            """SELECT l.*, l.nb_bouteilles - COALESCE((SELECT SUM(quantite) FROM ventes v
                 WHERE v.lot_id = l.id), 0) - COALESCE((SELECT SUM(quantite) FROM sorties s
                 WHERE s.lot_id = l.id), 0) AS reste FROM lots l
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

    # Factures en attente de paiement
    for t in conn.execute(
            "SELECT * FROM tickets WHERE paye = 0 AND echeance IS NOT NULL ORDER BY echeance"):
        ech = date.fromisoformat(t["echeance"])
        if (ech - ajd).days <= 7:
            ajouter("retard" if ech < ajd else "urgent", "declaration",
                    f"Paiement attendu : {t['client_nom']}",
                    f"{euro(t['total'])} · {t['facture_numero'] or t['numero']}", ech,
                    url_for("ticket_detail", ticket_id=t["id"]))

    # Dépôt-vente : faire le point tous les 2 mois
    for dp in conn.execute(
            """SELECT c.id, c.nom, MAX(d.date_mouvement) AS dernier,
                      SUM(CASE d.type WHEN 'depot' THEN d.quantite ELSE -d.quantite END) AS reste
               FROM depots d JOIN clients c ON c.id = d.client_id GROUP BY c.id"""):
        if dp["reste"] > 0 and (ajd - date.fromisoformat(dp["dernier"])).days >= 45:
            ajouter("info", "client", f"Faire le point du dépôt chez {dp['nom']}",
                    f"{dp['reste']} bouteille(s) en dépôt · dernier relevé il y a "
                    f"{(ajd - date.fromisoformat(dp['dernier'])).days} jours", None,
                    url_for("depot_client", client_id=dp["id"]))

    # Revendeurs sans commande depuis 45 jours
    for c in conn.execute(
            """SELECT c.*, (SELECT MAX(date_vente) FROM tickets t WHERE t.client_id = c.id) AS dernier
               FROM clients c WHERE c.type = 'revendeur'"""):
        if c["dernier"] and (ajd - date.fromisoformat(c["dernier"])).days >= 45:
            ajouter("info", "client", f"Relancer {c['nom']}",
                    f"Dernière commande il y a {(ajd - date.fromisoformat(c['dernier'])).days} jours",
                    None, url_for("client_detail", client_id=c["id"]))

    # Plafonds micro-entreprise et franchise de TVA
    from plafonds import etat_plafonds
    for j in etat_plafonds(conn, conf)["jauges"]:
        if j["niveau"] == "ok":
            continue
        if j["niveau"] == "retard":
            titre = "Seuil majoré de TVA dépassé"
            detail = "La TVA est due dès le jour du dépassement : contactez votre comptable ou le SIE"
        elif j["pct"] >= 80:
            titre = f"{j['titre']} : {j['pct']:.0f} % atteint"
            detail = f"{j['ca']:,.0f} € sur {j['plafond']:,.0f} €".replace(",", " ")
        else:
            titre = f"{j['titre']} : dépassement possible"
            detail = (f"À ce rythme, environ {j['projection']:,.0f} € sur l'année "
                      f"(plafond {j['plafond']:,.0f} €)").replace(",", " ")
        ajouter(j["niveau"], "chiffres", titre, detail, None, url_for("chiffres") + "#plafonds")

    # Plan d'hygiène : tâches à faire
    from vues_hygiene import rappels_hygiene
    for x in rappels_hygiene(conn):
        ajouter(x["etat"], "check", f"Hygiène : {x['t']['nom']}",
                f"Tous les {x['t']['frequence_jours']} jours"
                + (f" · dernier le {date.fromisoformat(x['dernier']):%d/%m}" if x["dernier"]
                   else " · jamais noté"),
                date.fromisoformat(x["prochaine"]), url_for("hygiene"))

    # Nouveaux avis clients
    nb_avis = conn.execute("SELECT COUNT(*) FROM avis WHERE lu = 0").fetchone()[0]
    if nb_avis:
        ajouter("info", "message", f"{nb_avis} nouvel avis client" if nb_avis == 1
                else f"{nb_avis} nouveaux avis clients", "Notes, commentaires et conseils à lire",
                None, url_for("avis_clients", filtre="nouveaux"))

    ordre = {"retard": 0, "urgent": 1, "info": 2}
    rappels.sort(key=lambda r: (ordre[r["niveau"]], r["echeance"] or "9999"))
    return rappels
