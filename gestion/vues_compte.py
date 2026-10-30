"""Connexion, paramètres et gestion des données."""
import os
import subprocess
import time
from pathlib import Path

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import db as database
from calculs import to_float
from emails import envoyer, smtp_configure
from noyau import BASE, app, get_db, redirection_sure, set_setting, settings

CHAMPS_TEXTE = ("producteur_nom", "producteur_adresse", "producteur_email",
                "producteur_telephone", "siret", "iban", "conditions_paiement",
                "smtp_host", "smtp_user", "smtp_expediteur")
CHAMPS_NOMBRE = ("tva_taux", "accise_hlap", "secu_hlap", "consigne_montant",
                 "urssaf_taux", "cfp_taux", "smtp_port")


# Protection contre les essais de mot de passe en série (application en ligne)
ECHECS = {}
MAX_ECHECS, FENETRE = 5, 15 * 60


def _bloque(ip):
    maintenant = time.time()
    ECHECS[ip] = [t for t in ECHECS.get(ip, []) if maintenant - t < FENETRE]
    return len(ECHECS[ip]) >= MAX_ECHECS


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    ip = request.headers.get("X-Real-IP") or request.remote_addr or "?"
    if request.method == "POST" and _bloque(ip):
        flash("Trop d'essais. Réessayez dans 15 minutes.", "erreur")
    elif request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            csrf = session.get("csrf")
            session.clear()
            session["csrf"] = csrf
            session.permanent = True
            session["user_id"] = user["id"]
            ECHECS.pop(ip, None)
            return redirection_sure(request.args.get("next"), url_for("tableau_de_bord"))
        ECHECS.setdefault(ip, []).append(time.time())
        flash("Email ou mot de passe incorrect.", "erreur")
    # Les identifiants de démonstration ne s'affichent jamais sur une application en ligne.
    demo = os.environ.get("HTTPS") != "1" and check_password_hash(
        get_db().execute("SELECT password_hash FROM users LIMIT 1").fetchone()[0],
        "corsaire2026",
    )
    return render_template("connexion.html", demo=demo)


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect(url_for("connexion"))


@app.route("/parametres", methods=["GET", "POST"])
def parametres():
    conn = get_db()
    if request.method == "POST":
        for key in CHAMPS_TEXTE:
            set_setting(key, request.form.get(key, "").strip())
        for key in CHAMPS_NOMBRE:
            set_setting(key, str(max(to_float(request.form.get(key)), 0)))
        set_setting("tva_applicable", "1" if request.form.get("tva_applicable") else "0")
        periodicite = request.form.get("urssaf_periodicite")
        set_setting("urssaf_periodicite",
                    "trimestrielle" if periodicite == "trimestrielle" else "mensuelle")
        # Le mot de passe SMTP n'est remplacé que s'il est ressaisi.
        if request.form.get("smtp_password"):
            set_setting("smtp_password", request.form["smtp_password"])
        if request.form.get("smtp_effacer"):
            set_setting("smtp_password", "")
        conn.commit()
        flash("Paramètres enregistrés.", "succes")
        return redirect(url_for("parametres") + "#" + request.form.get("ancre", ""))
    user = conn.execute("SELECT email FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    return render_template("parametres.html", conf=settings(), email=user["email"],
                           smtp_ok=smtp_configure(settings()))


@app.route("/parametres/test-email", methods=["POST"])
def parametres_test_email():
    conf = settings()
    dest = conf.get("producteur_email") or conf.get("smtp_expediteur")
    try:
        envoyer(conf, dest, "Test d'envoi – Maison Corsaire",
                "Bonjour,\n\nL'envoi d'emails depuis votre application fonctionne.\n")
        flash(f"Email de test envoyé à {dest}.", "succes")
    except Exception as exc:  # noqa: BLE001 — on affiche l'erreur à l'utilisateur
        flash(f"Échec de l'envoi : {exc}", "erreur")
    return redirect(url_for("parametres") + "#emails")


@app.route("/parametres/compte", methods=["POST"])
def parametres_compte():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    retour = redirect(url_for("parametres") + "#compte")
    if not check_password_hash(user["password_hash"], request.form.get("actuel", "")):
        flash("Mot de passe actuel incorrect : rien n'a été modifié.", "erreur")
        return retour
    email = request.form.get("email", "").strip().lower()
    nouveau = request.form.get("nouveau", "")
    confirmation = request.form.get("confirmation", "")
    if "@" not in email:
        flash("Adresse email invalide : rien n'a été modifié.", "erreur")
        return retour
    if nouveau and len(nouveau) < 8:
        flash("Le nouveau mot de passe doit contenir au moins 8 caractères : rien n'a été modifié.",
              "erreur")
        return retour
    if nouveau and nouveau != confirmation:
        flash("Les deux nouveaux mots de passe ne sont pas identiques : rien n'a été modifié.",
              "erreur")
        return retour
    messages = []
    if email != user["email"]:
        conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user["id"]))
        messages.append(f"email de connexion : {email}")
    if nouveau:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                     (generate_password_hash(nouveau), user["id"]))
        messages.append("mot de passe changé, utilisez-le à votre prochaine connexion")
    conn.commit()
    flash(("Enregistré : " + " ; ".join(messages) + ".") if messages
          else "Aucun changement : remplissez « Nouveau mot de passe » pour le changer.",
          "succes" if messages else "info")
    return retour


def version_appli():
    """Version installée (dernier commit), pour vérifier qu'une mise à jour a bien pris effet."""
    try:
        res = subprocess.run(["git", "-C", str(BASE), "log", "-1", "--format=%h · %cd",
                              "--date=format:%d/%m/%Y %H:%M"], capture_output=True, text=True,
                             timeout=5)
        return res.stdout.strip() or "inconnue"
    except (OSError, subprocess.TimeoutExpired):
        return "inconnue"


app.jinja_env.globals["version_appli"] = version_appli


def chemin_installeur():
    """Script d'installation présent seulement sur une installation PythonAnywhere."""
    chemin = BASE / "installer_pythonanywhere.sh"
    config = Path(os.environ.get("DATA_DIR", "")) / "config.json"
    return chemin if os.environ.get("HTTPS") == "1" and config.exists() else None


app.jinja_env.globals["mise_a_jour_possible"] = lambda: chemin_installeur() is not None


@app.route("/parametres/mise-a-jour", methods=["POST"])
def parametres_mise_a_jour():
    """Récupère la dernière version, installe les dépendances et relance l'application."""
    script = chemin_installeur()
    if not script:
        flash("Mise à jour automatique disponible uniquement sur PythonAnywhere.", "erreur")
        return redirect(url_for("parametres") + "#mise-a-jour")
    try:
        res = subprocess.run(["bash", str(script)], capture_output=True, text=True,
                             timeout=280, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        flash("La mise à jour prend du temps : patientez 2 minutes puis rechargez la page.",
              "info")
        return redirect(url_for("parametres") + "#mise-a-jour")
    if res.returncode == 0:
        flash("Mise à jour installée. Si rien ne change, touchez Reload dans l'onglet Web "
              "de PythonAnywhere.", "succes")
    else:
        flash("Échec de la mise à jour : " + (res.stderr or res.stdout)[-400:], "erreur")
    return redirect(url_for("parametres") + "#mise-a-jour")


@app.route("/parametres/donnees", methods=["POST"])
def parametres_donnees():
    conn = get_db()
    action = request.form.get("action")
    if request.form.get("confirmation", "").strip().upper() != "CONFIRMER":
        flash("Tapez CONFIRMER pour valider cette action.", "erreur")
        return redirect(url_for("parametres") + "#donnees")
    database.clear_data(conn)
    if action == "exemple":
        database.seed_demo(conn)
        flash("Données d'exemple rechargées.", "succes")
    else:
        flash("Toutes les données ont été effacées. Vous pouvez démarrer votre vrai registre.",
              "succes")
    conn.commit()
    return redirect(url_for("tableau_de_bord"))
