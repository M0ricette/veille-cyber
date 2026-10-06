"""Configuration lue depuis les variables d'environnement ou un fichier .env.

Aucun secret dans le code : la clé API et le mot de passe SMTP restent dans .env,
qui n'est jamais commité.
"""
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent
load_dotenv(RACINE / ".env")


@dataclass(frozen=True)
class Config:
    fichier_sources: Path
    fenetre_heures: int
    modele: str
    max_tours: int
    max_lectures: int
    nom_journal: str
    premier_numero: date
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    mail_to: str


def load_config() -> Config:
    return Config(
        fichier_sources=Path(os.getenv("SOURCES", RACINE / "sources.yaml")),
        fenetre_heures=int(os.getenv("WINDOW_HOURS", "24")),
        modele=os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001"),
        max_tours=int(os.getenv("AGENT_MAX_TOURS", "10")),
        max_lectures=int(os.getenv("AGENT_MAX_LECTURES", "6")),
        nom_journal=os.getenv("NOM_JOURNAL", "Le Veilleur"),
        premier_numero=date.fromisoformat(os.getenv("PREMIER_NUMERO", "2026-10-07")),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        mail_to=os.getenv("MAIL_TO", ""),
    )
