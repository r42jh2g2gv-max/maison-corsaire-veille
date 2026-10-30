"""Application installable et fonctionnement hors ligne (service worker, manifeste)."""
import hashlib
import json

from flask import Response, render_template, url_for

from noyau import BASE, app


def version_statique():
    """Change dès qu'un fichier statique change : force la mise à jour du cache hors ligne."""
    h = hashlib.sha1()
    for chemin in sorted((BASE / "static").rglob("*")):
        if chemin.is_file():
            h.update(chemin.name.encode())
            h.update(str(chemin.stat().st_mtime_ns).encode())
    return h.hexdigest()[:10]


@app.route("/sw.js")
def service_worker():
    pages = [url_for("caisse"), url_for("tableau_de_bord"), url_for("hors_ligne")]
    statiques = [url_for("static", filename=f) for f in (
        "style.css", "ancre.svg", "js/hors-ligne.js", "icones/icone-192.png")]
    js = render_template("sw.js", version=version_statique(), pages=json.dumps(pages),
                         statiques=json.dumps(statiques))
    return Response(js, mimetype="application/javascript",
                    headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@app.route("/manifest.webmanifest")
def manifeste():
    donnees = {
        "name": "Maison Corsaire",
        "short_name": "Corsaire",
        "description": "Gestion de la production et des ventes de rhum arrangé",
        "lang": "fr",
        "start_url": url_for("tableau_de_bord"),
        "scope": "/",
        "display": "standalone",
        "background_color": "#0a1322",
        "theme_color": "#0a1322",
        "icons": [
            {"src": url_for("static", filename="icones/icone-192.png"), "sizes": "192x192",
             "type": "image/png"},
            {"src": url_for("static", filename="icones/icone-512.png"), "sizes": "512x512",
             "type": "image/png"},
            {"src": url_for("static", filename="icones/icone-maskable-512.png"),
             "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [{"name": "Caisse", "url": url_for("caisse")}],
    }
    return Response(json.dumps(donnees, ensure_ascii=False),
                    mimetype="application/manifest+json")


@app.route("/hors-ligne")
def hors_ligne():
    return render_template("hors_ligne.html")
