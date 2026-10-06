"""Mémoire longue de l'agent : ce qui doit survivre d'un matin à l'autre.

Le modèle ne retient rien entre deux exécutions. Cette base garde trois choses :
- les articles déjà publiés, pour ne jamais les ressortir ;
- les notions déjà expliquées et leur niveau, pour ne pas se répéter et progresser ;
- les éditions, pour numéroter le journal.

Règle de sécurité : on ne mémorise que des données validées par le code,
jamais le texte brut des articles. Sinon, une injection cachée dans une page
reviendrait dans le prompt tous les jours suivants.

Usage : python -m veille.memoire   affiche le contenu de la mémoire
"""
import difflib
import re
import sqlite3
import unicodedata
from datetime import date
from pathlib import Path

NIVEAU_MAX = 4
NOTIONS_PAR_NIVEAU = 10   # une notion par jour : on monte d'un niveau toutes les dix éditions
SEUIL_SIMILARITE = 0.85
MAX_TITRE_NOTION = 80

SCHEMA = """
CREATE TABLE IF NOT EXISTS editions (
    jour     TEXT PRIMARY KEY,
    numero   INTEGER NOT NULL,
    accroche TEXT
);
CREATE TABLE IF NOT EXISTS articles_publies (
    lien   TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    jour   TEXT NOT NULL REFERENCES editions(jour)
);
CREATE TABLE IF NOT EXISTS notions (
    id         INTEGER PRIMARY KEY,
    titre      TEXT NOT NULL,
    normalise  TEXT NOT NULL UNIQUE,
    niveau     INTEGER NOT NULL,
    jour       TEXT NOT NULL REFERENCES editions(jour)
);
"""

MOTS_VIDES = {"le", "la", "les", "l", "un", "une", "des", "du", "de", "d", "the", "a", "an"}


def normaliser(titre: str) -> str:
    """« L'Attaque par la chaîne d'outils » devient « attaque par chaine outils »."""
    sans_accents = unicodedata.normalize("NFKD", titre).encode("ascii", "ignore").decode()
    mots = re.findall(r"[a-z0-9]+", sans_accents.lower())
    return " ".join(m for m in mots if m not in MOTS_VIDES)


def nettoyer_titre(titre: str) -> str:
    """Un titre de notion est réinjecté dans le prompt : une ligne, longueur bornée."""
    return re.sub(r"\s+", " ", str(titre)).strip()[:MAX_TITRE_NOTION]


def notion_deja_vue(titre: str, vues: list[str]) -> str | None:
    """Renvoie la notion déjà vue qui ressemble trop à ce titre, sinon None.

    Attrape les variantes d'écriture. Ne voit pas les synonymes comme
    phishing et hameçonnage : il faudra des embeddings pour ça.
    """
    cible = normaliser(titre)
    for vue in vues:
        n = normaliser(vue)
        if n == cible or difflib.SequenceMatcher(None, n, cible).ratio() >= SEUIL_SIMILARITE:
            return vue
    return None


class Memoire:
    def __init__(self, chemin: Path | str):
        if chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(chemin))
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)

    # Lecture

    def liens_publies(self, liens: list[str]) -> set[str]:
        if not liens:
            return set()
        trous = ",".join("?" * len(liens))
        lignes = self.db.execute(f"SELECT lien FROM articles_publies WHERE lien IN ({trous})", liens)
        return {l for (l,) in lignes}

    def notions_vues(self) -> list[tuple[str, int]]:
        return list(self.db.execute("SELECT titre, niveau FROM notions ORDER BY id"))

    def niveau_cible(self) -> int:
        (nb,) = self.db.execute("SELECT COUNT(*) FROM notions").fetchone()
        return min(NIVEAU_MAX, 1 + nb // NOTIONS_PAR_NIVEAU)

    def numero_suivant(self, jour: date) -> int:
        deja = self.db.execute("SELECT numero FROM editions WHERE jour = ?", (jour.isoformat(),)).fetchone()
        if deja:  # relance le même jour : même numéro
            return deja[0]
        (nb,) = self.db.execute("SELECT COUNT(*) FROM editions").fetchone()
        return nb + 1

    # Écriture

    def enregistrer_edition(self, jour: date, numero: int, accroche: str,
                            articles: list[tuple[str, str]], notion: tuple[str, int] | None) -> None:
        """Tout ou rien : une transaction, pour ne jamais garder une édition à moitié écrite."""
        j = jour.isoformat()
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO editions VALUES (?, ?, ?)", (j, numero, accroche))
            self.db.executemany("INSERT OR IGNORE INTO articles_publies VALUES (?, ?, ?)",
                                [(lien, source, j) for lien, source in articles])
            if notion:
                titre = nettoyer_titre(notion[0])
                self.db.execute("INSERT OR IGNORE INTO notions (titre, normalise, niveau, jour) VALUES (?, ?, ?, ?)",
                                (titre, normaliser(titre), notion[1], j))

    def fermer(self) -> None:
        self.db.close()


def _afficher(chemin: Path) -> None:
    m = Memoire(chemin)
    (nb_ed,) = m.db.execute("SELECT COUNT(*) FROM editions").fetchone()
    (nb_art,) = m.db.execute("SELECT COUNT(*) FROM articles_publies").fetchone()
    vues = m.notions_vues()
    print(f"{nb_ed} éditions, {nb_art} articles publiés, {len(vues)} notions vues")
    print(f"Niveau visé pour la prochaine notion : {m.niveau_cible()} sur {NIVEAU_MAX}")
    for titre, niveau in vues:
        print(f"  niveau {niveau} · {titre}")
    m.fermer()


if __name__ == "__main__":
    from .config import load_config
    _afficher(load_config().fichier_memoire)
