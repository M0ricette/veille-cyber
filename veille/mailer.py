"""Envoi du journal par SMTP, en pièce jointe PDF.

SMTP est un standard : marche avec Gmail, Outlook ou n'importe quel serveur,
sans dépendre d'un service tiers d'emailing.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from .config import Config

log = logging.getLogger(__name__)


def envoyer(cfg: Config, objet: str, texte: str, pdf: Path) -> None:
    if not (cfg.smtp_user and cfg.smtp_password and cfg.mail_to):
        raise RuntimeError("SMTP_USER, SMTP_PASSWORD et MAIL_TO doivent être définis dans .env")

    msg = EmailMessage()
    msg["Subject"] = objet
    msg["From"] = cfg.smtp_user
    msg["To"] = cfg.mail_to
    msg.set_content(texte)
    msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)

    # SMTP_SSL : connexion chiffrée dès le départ, le mot de passe ne circule jamais en clair.
    with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=ssl.create_default_context()) as smtp:
        smtp.login(cfg.smtp_user, cfg.smtp_password)
        smtp.send_message(msg)
    log.info("Journal envoyé")  # pas d'adresse dans les logs : ils peuvent être publics sur GitHub
