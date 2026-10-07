"""Dit si l'édition du jour est déjà partie, d'après la mémoire.

GitHub peut retarder ou sauter un déclenchement planifié. Le workflow se déclenche
donc plusieurs fois chaque matin, et ce script rend les passages suivants inoffensifs :
le premier qui réussit envoie le journal, les autres s'arrêtent tout de suite.

Volontairement sans dépendance : il tourne avant l'installation des paquets,
pour qu'un passage inutile ne coûte que quelques secondes.

Usage : python scripts/edition_faite.py data/veilleur.db
Écrit « oui » ou « non » sur la sortie standard.
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path


def edition_faite(chemin: Path, jour: date) -> bool:
    if not chemin.exists():
        return False
    db = sqlite3.connect(chemin)
    try:
        ligne = db.execute("SELECT 1 FROM editions WHERE jour = ?", (jour.isoformat(),)).fetchone()
    except sqlite3.OperationalError:  # base vide ou incomplète : on considère qu'il faut publier
        ligne = None
    finally:
        db.close()
    return ligne is not None


if __name__ == "__main__":
    # date.today() suit la variable TZ du workflow, réglée sur Europe/Paris.
    print("oui" if edition_faite(Path(sys.argv[1]), date.today()) else "non")
