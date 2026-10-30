"""Calculs de coût de revient, de prix et de marge."""

STATUTS = {
    "maceration": "En macération",
    "pret": "Prêt à embouteiller",
    "embouteille": "Embouteillé",
    "epuise": "Épuisé",
}
STATUTS_EMBOUTEILLES = ("embouteille", "epuise")

CATEGORIES_INGREDIENTS = {
    "rhum": "Rhum",
    "fruit": "Fruits",
    "epice": "Épices",
    "sucre": "Sucre",
    "autre": "Autre",
}

TYPES_MATERIAUX = {
    "bouteille": "Bouteille vide",
    "bouchon": "Bouchon",
    "etiquette": "Étiquette",
    "emballage": "Emballage",
    "autre": "Autre",
}


def to_float(value, default=0.0):
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return default


def taux_tva(settings):
    """Taux de TVA appliqué (0 en franchise en base, art. 293 B du CGI)."""
    if settings.get("tva_applicable") == "1":
        return to_float(settings.get("tva_taux"), 20.0) / 100
    return 0.0


def droits_par_bouteille(volume_cl, degre, settings):
    """Droits d'accise + cotisation sécurité sociale, en € par bouteille."""
    hl_alcool_pur = (volume_cl or 0) / 10000 * (degre or 0) / 100
    tarif = to_float(settings.get("accise_hlap")) + to_float(settings.get("secu_hlap"))
    return hl_alcool_pur * tarif


def cout_revient(conn, lot, settings):
    """Détail du coût de revient d'une bouteille pour un lot."""
    ingredients = conn.execute(
        "SELECT COALESCE(SUM(cout), 0) FROM lot_ingredients WHERE lot_id = ?",
        (lot["id"],),
    ).fetchone()[0]
    nb = lot["nb_bouteilles"] or 0
    materiaux = conn.execute(
        "SELECT nom, type, cout_unitaire FROM materiaux WHERE par_bouteille = 1 ORDER BY type, nom"
    ).fetchall()
    ing_btl = ingredients / nb if nb else 0.0
    mat_btl = sum(m["cout_unitaire"] for m in materiaux)
    droits = droits_par_bouteille(lot["volume_cl"], lot["degre"], settings)
    return {
        "ingredients_total": ingredients,
        "ingredients_bouteille": ing_btl,
        "materiaux": [dict(m) for m in materiaux],
        "materiaux_bouteille": mat_btl,
        "droits_bouteille": droits,
        "total": ing_btl + mat_btl + droits,
        "calculable": nb > 0,
    }


def prix_depuis_marge(cout, marge_pct):
    """Prix HT pour obtenir une marge (en % du prix de vente HT)."""
    marge = min(max(marge_pct, 0), 95) / 100
    return cout / (1 - marge) if cout else 0.0


def marge_pct(prix_ht, cout):
    return (prix_ht - cout) / prix_ht * 100 if prix_ht else 0.0


# Conversions d'unités : (famille, facteur vers l'unité de base)
UNITES = {
    "kg": ("masse", 1000), "g": ("masse", 1),
    "l": ("volume", 1000), "cl": ("volume", 10), "ml": ("volume", 1),
    "pièce": ("piece", 1), "piece": ("piece", 1), "pièces": ("piece", 1), "pc": ("piece", 1),
}


def convertir(quantite, de, vers):
    """Convertit une quantité (g → kg, cl → L...). None si les unités sont incompatibles."""
    if quantite is None:
        return None
    de, vers = (de or "").strip().lower(), (vers or "").strip().lower()
    if de == vers:
        return quantite
    a, b = UNITES.get(de), UNITES.get(vers)
    if not a or not b or a[0] != b[0]:
        return None
    return quantite * a[1] / b[1]
