"""Pages publiques (sans connexion) : fiche produit du QR code et calendrier abonné."""
import secrets
from datetime import date, datetime, timedelta

from flask import Response, abort, flash, redirect, render_template, request, url_for

from noyau import TYPES_EVENEMENTS, app, get_db, get_or_404, set_setting, settings
from rappels import calculer_rappels
from vues_etiquettes import donnees_etiquette

@app.route("/p/<int:recette_id>")
def produit_public(recette_id):
    """Fiche produit lue en scannant le QR code de la contre-étiquette.
    N'affiche que ce qui figure déjà sur l'étiquette (jamais la recette ni les prix d'achat)."""
    conn = get_db()
    recette = get_or_404("recettes", recette_id)
    lot = None
    if request.args.get("lot"):
        lot = conn.execute("SELECT * FROM lots WHERE numero = ? AND recette_id = ?",
                           (request.args["lot"], recette_id)).fetchone()
    e = donnees_etiquette(conn, recette=recette, lot=lot)
    marches = conn.execute(
        "SELECT * FROM evenements WHERE COALESCE(date_fin, date_debut) >= ? AND type != 'autre'"
        " ORDER BY date_debut LIMIT 4", (date.today().isoformat(),)).fetchall()
    from vues_avis import avis_publies, resume_avis
    return render_template("produit_public.html", r=recette, e=e, lot=lot, marches=marches,
                           note=resume_avis(conn, recette_id, publies=True),
                           avis=avis_publies(conn, recette_id),
                           conf=settings(), TYPES_EVENEMENTS=TYPES_EVENEMENTS)


# --- Calendrier abonné (.ics) : agenda + rappels dans le calendrier du téléphone

def jeton_calendrier(nouveau=False):
    jeton = settings().get("calendrier_jeton")
    if nouveau or not jeton:
        jeton = secrets.token_urlsafe(24)
        set_setting("calendrier_jeton", jeton)
        get_db().commit()
    return jeton


def _txt(s):
    return (str(s or "").replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,")
            .replace("\r", "").replace("\n", "\\n"))


def _plier(ligne):
    """Lignes de 75 octets maximum (norme iCalendar)."""
    b = ligne.encode("utf-8")
    morceaux = []
    while len(b) > 74:
        coupe = 74
        while (b[coupe] & 0xC0) == 0x80:  # ne pas couper un caractère accentué
            coupe -= 1
        morceaux.append(b[:coupe].decode())
        b = b[coupe:]
    morceaux.append(b.decode())
    return "\r\n ".join(morceaux)


def _evenement(uid, jour, titre, description="", fin=None, lieu="", alarme_jours=1, url=""):
    d = date.fromisoformat(jour)
    f = date.fromisoformat(fin) if fin else d
    lignes = ["BEGIN:VEVENT", f"UID:{uid}@maison-corsaire",
              f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
              f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
              f"DTEND;VALUE=DATE:{(f + timedelta(days=1)).strftime('%Y%m%d')}",
              f"SUMMARY:{_txt(titre)}"]
    if description:
        lignes.append(f"DESCRIPTION:{_txt(description)}")
    if lieu:
        lignes.append(f"LOCATION:{_txt(lieu)}")
    if url:
        lignes.append(f"URL:{url}")
    if alarme_jours is not None:
        # rappel à 9 h le jour J - alarme_jours (début d'un événement « journée » = minuit)
        avance = alarme_jours * 24 - 9
        lignes += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_txt(titre)}",
                   f"TRIGGER:-PT{avance}H" if avance > 0 else f"TRIGGER:PT{-avance}H",
                   "END:VALARM"]
    lignes.append("END:VEVENT")
    return lignes


@app.route("/calendrier/<jeton>.ics")
def calendrier_ics(jeton):
    if not secrets.compare_digest(jeton, settings().get("calendrier_jeton") or "-"):
        abort(404)
    conn = get_db()
    racine = request.url_root.rstrip("/")
    lignes = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Maison Corsaire//Gestion//FR",
              "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Maison Corsaire",
              "X-WR-TIMEZONE:Europe/Paris", "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
              "X-PUBLISHED-TTL:PT6H"]
    depuis = (date.today() - timedelta(days=60)).isoformat()
    for e in conn.execute("SELECT * FROM evenements WHERE COALESCE(date_fin, date_debut) >= ?",
                          (depuis,)):
        detail = [TYPES_EVENEMENTS.get(e["type"], "")]
        if e["btl_prevues"]:
            detail.append(f"{e['btl_prevues']} bouteilles prévues")
        if e["notes"]:
            detail.append(e["notes"])
        lignes += _evenement(f"evt-{e['id']}", e["date_debut"], e["nom"], "\n".join(detail),
                             e["date_fin"], e["lieu"], 1, racine + url_for("agenda"))
        if e["date_limite_inscription"] and not e["inscrit"]:
            lignes += _evenement(f"insc-{e['id']}", e["date_limite_inscription"],
                                 f"Inscription : {e['nom']}", "Date limite d'inscription",
                                 alarme_jours=3, url=racine + url_for("agenda"))
    vus = set()
    for r in calculer_rappels(conn, settings()):
        if not r["echeance"] or r["icone"] == "calendrier":
            continue  # les événements de l'agenda sont déjà présents
        uid = "rappel-" + "".join(ch for ch in f"{r['titre']}-{r['echeance']}" if ch.isalnum())[:60]
        if uid in vus:
            continue
        vus.add(uid)
        jour = max(r["echeance"], date.today().isoformat())
        lignes += _evenement(uid, jour, r["titre"], r["detail"], alarme_jours=0,
                             url=racine + (r["lien"] or "/"))
    lignes.append("END:VCALENDAR")
    corps = "\r\n".join(_plier(l) for l in lignes) + "\r\n"
    return Response(corps, mimetype="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": 'inline; filename="maison-corsaire.ics"'})


@app.route("/parametres/calendrier", methods=["POST"])
def calendrier_regenerer():
    jeton_calendrier(nouveau=True)
    flash("Nouvelle adresse de calendrier créée : l'ancienne ne fonctionne plus.", "succes")
    return redirect(url_for("parametres") + "#calendrier")


app.jinja_env.globals["jeton_calendrier"] = jeton_calendrier
