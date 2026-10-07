"""Le workflow se déclenche plusieurs fois par matin : seul le premier passage doit publier."""
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from veille.config import load_config
from veille.mailer import envoyer
from veille.memoire import Memoire

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
from edition_faite import edition_faite  # noqa: E402


def test_pas_de_base_donc_il_faut_publier(tmp_path):
    assert edition_faite(tmp_path / "absente.db", date(2026, 10, 7)) is False


def test_edition_du_jour_detectee(tmp_path):
    chemin = tmp_path / "m.db"
    m = Memoire(chemin)
    m.enregistrer_edition(date(2026, 10, 6), 1, "", [], None)
    m.fermer()
    assert edition_faite(chemin, date(2026, 10, 6)) is True
    assert edition_faite(chemin, date(2026, 10, 7)) is False


def test_base_vide_ne_bloque_pas(tmp_path):
    chemin = tmp_path / "vide.db"
    chemin.touch()
    assert edition_faite(chemin, date(2026, 10, 7)) is False


def test_le_script_repond_oui_ou_non(tmp_path):
    sortie = subprocess.run([sys.executable, str(RACINE / "scripts" / "edition_faite.py"), str(tmp_path / "x.db")],
                            capture_output=True, text=True, check=True).stdout.strip()
    assert sortie == "non"


def test_le_message_nomme_le_secret_manquant_sans_valeur(tmp_path):
    cfg = load_config()
    cfg = cfg.__class__(**{**cfg.__dict__, "smtp_user": "moi@exemple.fr", "smtp_password": "secret-a-ne-pas-afficher",
                           "mail_to": " "})
    with pytest.raises(RuntimeError) as erreur:
        envoyer(cfg, "objet", "texte", tmp_path / "x.pdf")
    assert "MAIL_TO" in str(erreur.value)
    assert "SMTP_USER" not in str(erreur.value) and "secret-a-ne-pas-afficher" not in str(erreur.value)
