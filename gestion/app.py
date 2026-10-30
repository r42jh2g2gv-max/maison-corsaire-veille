"""Maison Corsaire — gestion de la production et des ventes de rhum arrangé.

Point d'entrée : `python app.py`. Chaque module enregistre ses pages sur l'application.
"""
import os

from noyau import app  # noqa: F401  (crée l'application et la base)
import vues_accueil  # noqa: F401,E402
import vues_agenda  # noqa: F401,E402
import vues_clients  # noqa: F401,E402
import vues_compte  # noqa: F401,E402
import vues_lots  # noqa: F401,E402
import vues_recettes  # noqa: F401,E402
import vues_ventes  # noqa: F401,E402

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
