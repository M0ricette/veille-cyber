"""Configuration lue depuis les variables d'environnement ou un fichier .env.

Aucun secret dans le code : la clé API et le mot de passe SMTP restent dans .env,
qui n'est jamais commité.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    feed_url: str
    window_hours: int
    llm_model: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    mail_to: str


def load_config() -> Config:
    return Config(
        feed_url=os.getenv("FEED_URL", "https://www.cert.ssi.gouv.fr/feed/"),
        window_hours=int(os.getenv("WINDOW_HOURS", "24")),
        llm_model=os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001"),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        mail_to=os.getenv("MAIL_TO", ""),
    )
