"""Plafonds de la micro-entreprise (vente de marchandises) et de la franchise de TVA.
Valeurs 2026 vérifiées sur service-public.gouv.fr ; modifiables dans Paramètres."""
from datetime import date

from calculs import taux_tva, to_float

DEFAUTS = {"plafond_micro": "203100", "seuil_tva": "85000", "seuil_tva_majore": "93500"}


def etat_plafonds(conn, conf, jour=None):
    from rappels import ca_periode
    jour = jour or date.today()
    debut = date(jour.year, 1, 1)
    ca_ttc = ca_periode(conn, debut, jour)
    tva = taux_tva(conf)
    ca = ca_ttc / (1 + tva) if tva else ca_ttc  # les plafonds s'apprécient hors taxes
    jours = (jour - debut).days + 1
    annee = 366 if jour.year % 4 == 0 else 365
    # Première année : plafond micro au prorata du temps d'activité
    plafond = to_float(conf.get("plafond_micro"), 203100)
    activite = conf.get("debut_activite") or ""
    prorata = None
    if activite[:4] == str(jour.year):
        try:
            depuis = date.fromisoformat(activite)
            jours_activite = (date(jour.year, 12, 31) - depuis).days + 1
            prorata = round(plafond * jours_activite / annee)
            jours = max((jour - depuis).days + 1, 1)
            annee = jours_activite
        except ValueError:
            pass
    projection = ca / jours * annee if jours else 0
    jauges = [{"cle": "micro", "titre": "Plafond micro-entreprise",
               "plafond": prorata or plafond, "ca": ca, "projection": projection,
               "prorata": prorata is not None,
               "aide": "Un dépassement isolé ne fait pas perdre le régime : il faut le dépasser "
                       "deux années de suite."}]
    if conf.get("tva_applicable") != "1":
        jauges.append({"cle": "tva", "titre": "Franchise de TVA",
                       "plafond": to_float(conf.get("seuil_tva"), 85000),
                       "majore": to_float(conf.get("seuil_tva_majore"), 93500),
                       "ca": ca, "projection": projection, "prorata": False,
                       "aide": "Au-delà du seuil majoré, la TVA est due dès le jour du dépassement."})
    for j in jauges:
        j["pct"] = min(round(j["ca"] / j["plafond"] * 100, 1), 999) if j["plafond"] else 0
        j["pct_projection"] = round(j["projection"] / j["plafond"] * 100) if j["plafond"] else 0
        if j.get("majore") and j["ca"] > j["majore"]:
            j["niveau"] = "retard"
        elif j["pct"] >= 95:
            j["niveau"] = "urgent"
        elif j["pct"] >= 80 or j["pct_projection"] >= 100:
            j["niveau"] = "info"
        else:
            j["niveau"] = "ok"
    return {"annee": jour.year, "jauges": jauges}
