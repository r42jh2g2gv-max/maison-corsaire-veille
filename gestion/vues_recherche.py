"""Recherche globale : un seul champ pour retrouver client, lot, facture, ingrédient, bon..."""
import unicodedata

from flask import render_template, request, url_for

from noyau import app, get_db


def normaliser(texte):
    texte = unicodedata.normalize("NFD", str(texte or "").lower())
    return "".join(ch for ch in texte if unicodedata.category(ch) != "Mn")


SOURCES = [
    ("Clients", "clients",
     "SELECT id, nom, type, email, telephone, notes FROM clients ORDER BY nom",
     ("nom", "email", "telephone", "notes"),
     lambda r: (r["nom"], " · ".join(x for x in (r["email"], r["telephone"]) if x)),
     lambda r: url_for("client_detail", client_id=r["id"])),
    ("Lots", "lots",
     "SELECT id, numero, recette_nom, statut, volume_cl, notes FROM lots ORDER BY numero DESC",
     ("numero", "recette_nom", "notes"),
     lambda r: (f"{r['numero']} — {r['recette_nom'] or ''}", f"{r['volume_cl']} cl · {r['statut']}"),
     lambda r: url_for("lot_detail", lot_id=r["id"])),
    ("Recettes", "recettes",
     "SELECT id, nom, notes_degustation FROM recettes ORDER BY nom",
     ("nom", "notes_degustation"),
     lambda r: (r["nom"], (r["notes_degustation"] or "")[:80]),
     lambda r: url_for("recette_fiche", recette_id=r["id"])),
    ("Tickets et factures", "facture",
     """SELECT id, numero, facture_numero, client_nom, date_vente, total, paye, notes FROM tickets
        ORDER BY date_vente DESC, id DESC""",
     ("numero", "facture_numero", "client_nom", "notes"),
     lambda r: (" · ".join(x for x in (r["facture_numero"], r["numero"]) if x),
                f"{r['client_nom'] or ''} · {r['date_vente']} · {r['total']:.2f} €"
                + ("" if r["paye"] else " · à régler")),
     lambda r: url_for("ticket_detail", ticket_id=r["id"])),
    ("Avoirs", "facture",
     """SELECT a.id, a.numero, a.ticket_id, a.montant, a.motif, t.client_nom FROM avoirs a
        JOIN tickets t ON t.id = a.ticket_id ORDER BY a.id DESC""",
     ("numero", "client_nom", "motif"),
     lambda r: (r["numero"], f"{r['client_nom'] or ''} · {r['montant']:.2f} €"),
     lambda r: url_for("ticket_detail", ticket_id=r["ticket_id"])),
    ("Ingrédients", "lot",
     "SELECT id, nom, categorie, fournisseur, unite, notes FROM matieres_premieres ORDER BY nom",
     ("nom", "fournisseur", "notes"),
     lambda r: (r["nom"], " · ".join(x for x in (r["categorie"], r["fournisseur"]) if x)),
     lambda r: url_for("matiere_detail", mp_id=r["id"])),
    ("Achats", "facture",
     "SELECT id, fournisseur, date_achat, reference, montant_total, notes FROM achats ORDER BY date_achat DESC",
     ("fournisseur", "reference", "notes"),
     lambda r: (r["fournisseur"] or "Achat", f"{r['date_achat']}"
                + f" · {r['montant_total']:.2f} €"),
     lambda r: url_for("achat_modifier", achat_id=r["id"])),
    ("Bons d'achat", "bon",
     "SELECT id, code, beneficiaire, montant, motif FROM bons ORDER BY id DESC",
     ("code", "beneficiaire", "motif"),
     lambda r: (r["code"], f"{r['beneficiaire'] or ''} · {r['montant']:.2f} €"),
     lambda r: url_for("bons") + f"#bon-{r['id']}"),
    ("Agenda", "agenda",
     "SELECT id, nom, lieu, date_debut FROM evenements ORDER BY date_debut DESC",
     ("nom", "lieu"),
     lambda r: (r["nom"], f"{r['date_debut']}" + (f" · {r['lieu']}" if r["lieu"] else "")),
     lambda r: url_for("evenement_modifier", evt_id=r["id"])),
]


def rechercher(conn, q, limite=8):
    mots = normaliser(q).split()
    if not mots:
        return []
    groupes = []
    for titre, icone, sql, champs, libelle, lien in SOURCES:
        try:
            lignes = conn.execute(sql).fetchall()
        except Exception:  # colonne absente d'une ancienne base : on ignore la source
            continue
        trouves = []
        for r in lignes:
            texte = normaliser(" ".join(str(r[c] or "") for c in champs))
            if all(m in texte for m in mots):
                principal, detail = libelle(r)
                trouves.append({"titre": principal, "detail": detail, "lien": lien(r)})
        if trouves:
            groupes.append({"titre": titre, "icone": icone, "total": len(trouves),
                            "resultats": trouves[:limite]})
    return groupes


@app.route("/recherche")
def recherche():
    q = request.args.get("q", "").strip()[:80]
    tout = bool(request.args.get("tout"))
    groupes = rechercher(get_db(), q, limite=200 if tout else 8) if q else []
    return render_template("recherche.html", q=q, groupes=groupes, tout=tout)
