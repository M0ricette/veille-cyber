"""Vérification déterministe du journal proposé par l'agent.

L'agent rédige, ce module contrôle. Les contrôles sont du code simple :
ils donnent toujours le même résultat et se testent.

Ce qui est vérifié :
- chaque source citée existe dans le catalogue du jour ;
- la une s'appuie sur au moins un article lu en entier ;
- chaque paragraphe de la une cite au moins une source ;
- chaque CVE et chaque grand nombre figure dans les sources citées ;
- la notion du jour n'a pas déjà été expliquée.
"""
import re
from dataclasses import dataclass, field

from .collecte import Article
from .memoire import NIVEAU_MAX, nettoyer_essentiel, nettoyer_titre, notion_deja_vue

RUBRIQUES = ["Menaces et failles", "Fuites et attaques", "Géopolitique et régulation", "Écosystème"]

CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
REF_RE = re.compile(r"\[(S\d+)\]")
NOMBRE_RE = re.compile(r"\d{1,3}(?:[   .,]\d{3})+|\d{4,}")


@dataclass
class Une:
    titre: str
    chapo: str
    paragraphes: list[str]
    sources: list[Article]


@dataclass
class Breve:
    rubrique: str
    titre: str
    texte: str
    source: Article


@dataclass
class Notion:
    titre: str
    explication: str
    source: Article
    niveau: int
    essentiel: str = ""


@dataclass
class Journal:
    accroche: str
    une: Une | None
    breves: list[Breve]
    notion: Notion | None
    ecartes: list[str] = field(default_factory=list)


def _cves(texte: str) -> set[str]:
    return {c.upper() for c in CVE_RE.findall(texte)}


def _grands_nombres(texte: str) -> set[int]:
    """Nombres d'au moins 1000, séparateurs ignorés. Les années sont exclues."""
    nombres = set()
    for brut in NOMBRE_RE.findall(texte):
        chiffres = re.sub(r"\D", "", brut)
        n = int(chiffres)
        if n >= 1000 and not (len(chiffres) == 4 and 1900 <= n <= 2100):
            nombres.add(n)
    return nombres


def _non_sources(texte: str, reference: str) -> list[str]:
    """Ce que le texte affirme et que la référence ne contient pas."""
    manques = sorted(_cves(texte) - _cves(reference))
    manques += [f"{n:,}".replace(",", " ") for n in sorted(_grands_nombres(texte) - _grands_nombres(reference))]
    return manques


def _texte_source(article: Article, lus: dict[str, str]) -> str:
    return " ".join([article.titre, article.resume, lus.get(article.id, "")])


def verifier(data: dict, catalogue: dict[str, Article], lus: dict[str, str],
             notions_vues: list[str] = (), niveau_cible: int = 1) -> tuple[Journal, list[str]]:
    """Renvoie le journal nettoyé et la liste des problèmes trouvés."""
    problemes: list[str] = []

    # La une
    une = None
    u = data.get("une") or {}
    if u:
        paragraphes = [str(p).strip() for p in u.get("paragraphes", []) if str(p).strip()]
        ids = list(dict.fromkeys([str(i) for i in u.get("sources", [])] +
                                 [r for p in paragraphes for r in REF_RE.findall(p)]))
        p_une = [f"une : source inconnue {i}" for i in ids if i not in catalogue]
        connus = [catalogue[i] for i in ids if i in catalogue]
        if not any(a.id in lus for a in connus):
            p_une.append("une : elle doit s'appuyer sur au moins un article lu en entier avec lire_article")
        for n, p in enumerate(paragraphes, 1):
            if not REF_RE.search(p):
                p_une.append(f"une : le paragraphe {n} ne cite aucune source")
        reference = " ".join(_texte_source(a, lus) for a in connus)
        texte_une = " ".join([str(u.get("titre", "")), str(u.get("chapo", ""))] + paragraphes)
        manques = _non_sources(texte_une, reference)
        if manques:
            p_une.append(f"une : éléments absents des sources citées {manques}")
        if not paragraphes:
            p_une.append("une : aucun paragraphe")
        if p_une:
            problemes += p_une
        else:
            une = Une(str(u.get("titre", "")), str(u.get("chapo", "")), paragraphes, connus)

    # Les brèves
    breves: list[Breve] = []
    for b in data.get("breves", []):
        titre, texte = str(b.get("titre", "")), REF_RE.sub("", str(b.get("texte", ""))).strip()
        article = catalogue.get(str(b.get("source", "")))
        if article is None:
            problemes.append(f"brève {titre!r} : source inconnue {b.get('source')}")
            continue
        manques = _non_sources(titre + " " + texte, _texte_source(article, lus))
        if manques:
            problemes.append(f"brève {titre!r} : éléments absents de {article.id} {manques}")
            continue
        rubrique = b.get("rubrique") if b.get("rubrique") in RUBRIQUES else article.rubrique
        breves.append(Breve(rubrique, titre, texte, article))

    # La notion du jour : le concept peut venir des connaissances du modèle,
    # mais aucun fait d'actualité non sourcé.
    notion = None
    n = data.get("notion") or {}
    if n:
        article = catalogue.get(str(n.get("source", "")))
        tout = " ".join(_texte_source(a, lus) for a in catalogue.values())
        texte = " ".join(str(n.get(k, "")) for k in ("titre", "explication", "essentiel"))
        if article is None:
            problemes.append(f"notion : source inconnue {n.get('source')}")
        elif manques := _non_sources(texte, tout):
            problemes.append(f"notion : éléments absents des sources {manques}")
        elif not str(n.get("essentiel", "")).strip():
            problemes.append("notion : il manque l'essentiel en une phrase, utilisé pour les rappels")
        elif deja := notion_deja_vue(str(n.get("titre", "")), list(notions_vues)):
            problemes.append(f"notion : déjà expliquée lors d'une édition précédente, sous le titre {deja!r}. Choisis-en une autre")
        else:
            niveau = n.get("niveau") if n.get("niveau") in range(1, NIVEAU_MAX + 1) else niveau_cible
            notion = Notion(nettoyer_titre(n.get("titre", "")),
                            REF_RE.sub("", str(n.get("explication", ""))).strip(), article, niveau,
                            nettoyer_essentiel(REF_RE.sub("", str(n["essentiel"]))))

    accroche = str(data.get("accroche", "")).strip()
    if _non_sources(accroche, " ".join(_texte_source(a, lus) for a in catalogue.values())):
        problemes.append("accroche : éléments non sourcés")
        accroche = ""

    return Journal(accroche, une, breves, notion, problemes), problemes
