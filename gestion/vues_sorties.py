"""Sorties hors vente : cadeau, concours, dégustation, échantillon, casse."""
from datetime import date, datetime

from flask import flash, redirect, render_template, request, url_for

from noyau import (app, couts_par_lot, get_db, get_or_404, lots_avec_stock,
                   maj_statut_epuise, parse_date, redirection_sure, settings, stock_lot,
                   to_int, today)

MOTIFS = {
    "concours": "Concours / jeu",
    "cadeau": "Cadeau offert",
    "degustation": "Dégustation",
    "echantillon": "Échantillon (revendeur, presse)",
    "casse": "Casse / perte",
    "consommation": "Consommation personnelle",
    "autre": "Autre",
}
app.jinja_env.globals["MOTIFS_SORTIE"] = MOTIFS


@app.route("/sorties", methods=["GET", "POST"])
def sorties():
    conn = get_db()
    if request.method == "POST":
        lot_id = to_int(request.form.get("lot_id"))
        quantite = to_int(request.form.get("quantite"))
        motif = request.form.get("motif") if request.form.get("motif") in MOTIFS else "autre"
        lot = lots_avec_stock("WHERE l.id = ?", (lot_id,))
        if not lot or lot[0]["statut"] not in ("embouteille", "epuise"):
            flash("Choisissez un lot embouteillé.", "erreur")
        elif quantite <= 0:
            flash("Indiquez un nombre de bouteilles.", "erreur")
        elif quantite > stock_lot(lot[0]):
            flash(f"Stock insuffisant : il reste {stock_lot(lot[0])} bouteille(s) du lot "
                  f"{lot[0]['numero']}.", "erreur")
        else:
            conn.execute(
                "INSERT INTO sorties (date_sortie, lot_id, quantite, motif, beneficiaire,"
                " evenement_id, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (parse_date(request.form.get("date_sortie")) or today(), lot_id, quantite, motif,
                 request.form.get("beneficiaire", "").strip() or None,
                 to_int(request.form.get("evenement_id")) or None,
                 request.form.get("notes", "").strip() or None,
                 datetime.now().isoformat(timespec="seconds")))
            maj_statut_epuise(conn, lot_id)
            conn.commit()
            flash(f"{quantite} bouteille(s) de {lot[0]['recette_nom']} sortie(s) du stock "
                  f"({MOTIFS[motif].lower()}).", "succes")
            return redirection_sure(request.form.get("retour"), url_for("sorties"))

    annee = request.args.get("annee") or today()[:4]
    rows = conn.execute(
        """SELECT s.*, l.numero, l.recette_nom, l.volume_cl, e.nom AS evenement
           FROM sorties s JOIN lots l ON l.id = s.lot_id
           LEFT JOIN evenements e ON e.id = s.evenement_id
           WHERE s.date_sortie LIKE ? ORDER BY s.date_sortie DESC, s.id DESC""",
        (annee + "%",)).fetchall()
    couts = couts_par_lot(conn, settings())
    par_motif = {}
    for s in rows:
        m = par_motif.setdefault(s["motif"], {"btl": 0, "cout": 0.0})
        m["btl"] += s["quantite"]
        m["cout"] += s["quantite"] * couts.get(s["lot_id"], 0)
    annees = [r[0] for r in conn.execute(
        "SELECT DISTINCT substr(date_sortie, 1, 4) FROM sorties ORDER BY 1 DESC")] or [annee]
    lots = [l for l in lots_avec_stock("WHERE l.statut = 'embouteille' ORDER BY l.recette_nom")
            if stock_lot(l) > 0]
    evenements = conn.execute(
        "SELECT id, nom, date_debut FROM evenements WHERE date_debut >= ? ORDER BY date_debut",
        ((date.today().replace(day=1)).isoformat(),)).fetchall()
    return render_template(
        "sorties.html", sorties=rows, couts=couts, par_motif=par_motif, annee=annee,
        annees=annees, lots=lots, evenements=evenements, stock_lot=stock_lot,
        total_btl=sum(m["btl"] for m in par_motif.values()),
        total_cout=sum(m["cout"] for m in par_motif.values()),
        lot_preselect=to_int(request.args.get("lot_id")),
        motif_preselect=request.args.get("motif", ""),
    )


@app.route("/sorties/<int:sortie_id>/supprimer", methods=["POST"])
def sortie_supprimer(sortie_id):
    conn = get_db()
    sortie = get_or_404("sorties", sortie_id)
    conn.execute("DELETE FROM sorties WHERE id = ?", (sortie_id,))
    maj_statut_epuise(conn, sortie["lot_id"], reouvrir=True)
    conn.commit()
    flash(f"Sortie annulée : {sortie['quantite']} bouteille(s) remise(s) en stock.", "succes")
    return redirection_sure(request.form.get("retour"), url_for("sorties"))


def sorties_du_lot(conn, lot_id):
    return conn.execute(
        "SELECT * FROM sorties WHERE lot_id = ? ORDER BY date_sortie DESC, id DESC",
        (lot_id,)).fetchall()


app.jinja_env.globals["get_lot_sorties"] = lambda lot_id: sorties_du_lot(get_db(), lot_id)
