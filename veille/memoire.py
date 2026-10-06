"""Mémoire longue de l'agent : ce qui doit survivre d'un matin à l'autre.

Le modèle ne retient rien entre deux exécutions. Cette base garde trois choses :
- les articles déjà publiés, pour ne jamais les ressortir ;
- les notions déjà expliquées, leur niveau et leur idée clé, pour ne pas se répéter,
  progresser et faire des rappels ;
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
MAX_ESSENTIEL = 220
# Répétition espacée : on revoit la notion de la dernière édition, puis celles d'il y a 3 et 7 éditions.
RAPPELS = (1, 3, 7)

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
    jour       TEXT NOT NULL REFERENCES editions(jour),
    essentiel  TEXT NOT NULL DEFAULT ''
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


def nettoyer_essentiel(texte: str) -> str:
    """L'essentiel revient dans les journaux suivants : une ligne, longueur bornée."""
    texte = re.sub(r"\s+", " ", str(texte)).strip()
    return texte if len(texte) <= MAX_ESSENTIEL else texte[:MAX_ESSENTIEL].rsplit(" ", 1)[0] + "…"


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
        self._migrer()

    def _migrer(self) -> None:
        """Une base créée par une version précédente reçoit les colonnes ajoutées depuis."""
        colonnes = {c[1] for c in self.db.execute("PRAGMA table_info(notions)")}
        if "essentiel" not in colonnes:
            self.db.execute("ALTER TABLE notions ADD COLUMN essentiel TEXT NOT NULL DEFAULT ''")

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

    def rappels(self, jour: date) -> list[dict]:
        """Notions des éditions précédentes à revoir aujourd'hui, selon les intervalles RAPPELS."""
        precedentes = [j for (j,) in self.db.execute(
            "SELECT jour FROM editions WHERE jour < ? ORDER BY jour DESC", (jour.isoformat(),))]
        resultat = []
        for rang in RAPPELS:
            if rang > len(precedentes):
                break
            ligne = self.db.execute("SELECT titre, essentiel, niveau FROM notions WHERE jour = ?",
                                    (precedentes[rang - 1],)).fetchone()
            if ligne and ligne[1]:
                ecart = (jour - date.fromisoformat(precedentes[rang - 1])).days
                resultat.append({"titre": ligne[0], "essentiel": ligne[1], "niveau": ligne[2],
                                 "quand": "Hier" if ecart == 1 else f"Il y a {ecart} jours"})
        return resultat

    def numero_suivant(self, jour: date) -> int:
        deja = self.db.execute("SELECT numero FROM editions WHERE jour = ?", (jour.isoformat(),)).fetchone()
        if deja:  # relance le même jour : même numéro
            return deja[0]
        (nb,) = self.db.execute("SELECT COUNT(*) FROM editions").fetchone()
        return nb + 1

    # Écriture

    def enregistrer_edition(self, jour: date, numero: int, accroche: str,
                            articles: list[tuple[str, str]], notion: tuple[str, int, str] | None) -> None:
        """Tout ou rien : une transaction, pour ne jamais garder une édition à moitié écrite."""
        j = jour.isoformat()
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO editions VALUES (?, ?, ?)", (j, numero, accroche))
            self.db.executemany("INSERT OR IGNORE INTO articles_publies VALUES (?, ?, ?)",
                                [(lien, source, j) for lien, source in articles])
            if notion:
                titre, niveau, essentiel = nettoyer_titre(notion[0]), notion[1], nettoyer_essentiel(notion[2])
                self.db.execute("INSERT OR IGNORE INTO notions (titre, normalise, niveau, jour, essentiel) "
                                "VALUES (?, ?, ?, ?, ?)", (titre, normaliser(titre), niveau, j, essentiel))

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
