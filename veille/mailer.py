"""Envoi du mail par SMTP.

SMTP est un standard : marche avec Gmail, Outlook ou n'importe quel serveur,
sans dépendre d'un service tiers d'emailing.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from .config import Config

log = logging.getLogger(__name__)


def send_newsletter(cfg: Config, subject: str, text: str, html: str) -> None:
    if not (cfg.smtp_user and cfg.smtp_password and cfg.mail_to):
        raise RuntimeError("SMTP_USER, SMTP_PASSWORD et MAIL_TO doivent être définis dans .env")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.smtp_user
    msg["To"] = cfg.mail_to
    msg.set_content(text)                       # version texte, en secours
    msg.add_alternative(html, subtype="html")   # version affichée par défaut

    # SMTP_SSL : connexion chiffrée dès le départ, le mot de passe ne circule jamais en clair.
    with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=ssl.create_default_context()) as smtp:
        smtp.login(cfg.smtp_user, cfg.smtp_password)
        smtp.send_message(msg)
    log.info("Newsletter envoyée à %s", cfg.mail_to)
