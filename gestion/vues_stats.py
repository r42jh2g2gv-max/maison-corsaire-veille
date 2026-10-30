"""Statistiques par recette : production, ventes, marge, saisonnalité."""
from datetime import date, timedelta

from flask import render_template, request

from calculs import STATUTS_EMBOUTEILLES, marge_pct, taux_tva
from noyau import MOIS, app, couts_par_lot, get_db, lots_avec_stock, settings, stock_lot

PERIODES = {"12m": "12 derniers mois", "annee": "Cette année", "tout": "Depuis le début"}


@app.route("/statistiques")
def statistiques():
    conn = get_db()
    conf = settings()
    tva = taux_tva(conf)
    periode = request.args.get("periode") if request.args.get("periode") in PERIODES else "12m"
    ajd = date.today()
    debut = {"12m": (ajd - timedelta(days=365)).isoformat(), "annee": f"{ajd.year}-01-01",
             "tout": "2000-01-01"}[periode]
    couts = couts_par_lot(conn, conf)

    # 12 derniers mois pour les mini-graphiques
    mois = []
    y, m = ajd.year, ajd.month
    for _ in range(12):
        mois.append(f"{y}-{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    mois.reverse()

    recettes = {}

    def fiche(cle, nom):
        return recettes.setdefault(cle, {
            "nom": nom, "recette_id": cle if isinstance(cle, int) else None, "lots": 0,
            "produites": 0, "stock": 0, "en_cours": 0, "vendues": 0, "ca": 0.0, "cout": 0.0,
            "direct": 0, "revendeur": 0, "par_mois": {k: 0 for k in mois}, "clients": {},
            "cout_production": 0.0})

    for l in lots_avec_stock():
        f = fiche(l["recette_id"] or l["recette_nom"], l["recette_nom"])
        f["lots"] += 1
        if l["statut"] in STATUTS_EMBOUTEILLES:
            f["produites"] += l["nb_bouteilles"]
            f["stock"] += stock_lot(l)
            f["cout_production"] += l["nb_bouteilles"] * couts.get(l["id"], 0)
        else:
            f["en_cours"] += l["nb_bouteilles"]

    for v in conn.execute(
            """SELECT v.*, l.recette_id, l.recette_nom FROM ventes v JOIN lots l ON l.id = v.lot_id
               WHERE v.date_vente >= ?""", (debut,)):
        f = fiche(v["recette_id"] or v["recette_nom"], v["recette_nom"])
        montant = v["quantite"] * v["prix_unitaire_ttc"]
        f["vendues"] += v["quantite"]
        f["ca"] += montant
        f["cout"] += v["quantite"] * couts.get(v["lot_id"], 0)
        f[v["canal"] if v["canal"] in ("direct", "revendeur") else "direct"] += v["quantite"]
        if v["date_vente"][:7] in f["par_mois"]:
            f["par_mois"][v["date_vente"][:7]] += v["quantite"]
        f["clients"][v["client"]] = f["clients"].get(v["client"], 0) + v["quantite"]

    ca_total = sum(f["ca"] for f in recettes.values()) or 1
    lignes = []
    for f in recettes.values():
        ht = f["ca"] / (1 + tva)
        f["marge_euros"] = ht - f["cout"]
        f["marge"] = marge_pct(ht, f["cout"]) if ht else None
        f["prix_moyen"] = f["ca"] / f["vendues"] if f["vendues"] else None
        f["cout_moyen"] = f["cout_production"] / f["produites"] if f["produites"] else None
        f["part"] = f["ca"] / ca_total * 100
        f["taux_ecoulement"] = (f["produites"] - f["stock"]) / f["produites"] * 100 \
            if f["produites"] else None
        f["serie"] = [f["par_mois"][k] for k in mois]
        f["top_clients"] = sorted(f["clients"].items(), key=lambda x: -x[1])[:3]
        # Rythme de vente des 6 derniers mois, pour estimer l'autonomie du stock
        f["rythme"] = sum(f["serie"][-6:]) / 6
        f["autonomie"] = f["stock"] / f["rythme"] if f["rythme"] else None
        lignes.append(f)
    lignes.sort(key=lambda f: (-f["ca"], f["nom"]))
    max_serie = max((max(f["serie"]) for f in lignes if f["serie"]), default=0) or 1
    return render_template(
        "statistiques.html", lignes=lignes, periode=periode, periodes=PERIODES,
        mois=[MOIS[int(k[5:]) - 1] for k in mois], max_serie=max_serie,
        ca_total=sum(f["ca"] for f in lignes),
        marge_totale=sum(f["marge_euros"] for f in lignes),
        vendues=sum(f["vendues"] for f in lignes),
    )
