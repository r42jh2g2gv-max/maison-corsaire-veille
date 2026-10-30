"""Envoi d'emails par SMTP (Gmail, Orange, OVH, etc.), configuré dans Paramètres."""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid


def smtp_configure(conf):
    return bool(conf.get("smtp_host") and conf.get("smtp_user") and conf.get("smtp_password"))


def envoyer(conf, destinataire, sujet, texte, pieces=()):
    """Envoie un email texte. pieces : liste de (nom_fichier, contenu_bytes, type_mime)."""
    if not smtp_configure(conf):
        raise RuntimeError("l'envoi d'emails n'est pas configuré (Paramètres → Emails).")
    if not destinataire or "@" not in destinataire:
        raise RuntimeError("adresse email du destinataire manquante.")
    expediteur = conf.get("smtp_expediteur") or conf["smtp_user"]
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = formataddr((conf.get("producteur_nom") or "Maison Corsaire", expediteur))
    msg["To"] = destinataire
    msg["Message-ID"] = make_msgid(domain=expediteur.split("@")[-1])
    msg.set_content(texte)
    for nom, contenu, mime in pieces:
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(contenu, maintype=maintype, subtype=subtype, filename=nom)

    port = int(float(conf.get("smtp_port") or 587))
    contexte = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(conf["smtp_host"], port, context=contexte, timeout=20) as s:
            s.login(conf["smtp_user"], conf["smtp_password"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(conf["smtp_host"], port, timeout=20) as s:
            s.starttls(context=contexte)
            s.login(conf["smtp_user"], conf["smtp_password"])
            s.send_message(msg)
