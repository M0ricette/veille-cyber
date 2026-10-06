"""Collecte : lire tous les flux RSS et construire le catalogue du jour.

Cette partie n'est pas un agent, et c'est voulu. Lire des flux fixes ne demande
aucun jugement : du code simple le fait plus vite, moins cher et sans erreur.
"""
import calendar
import html
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import feedparser
import yaml

from .reseau import telecharger

log = logging.getLogger(__name__)

MAX_PAR_SOURCE = 12      # une source bavarde ne doit pas noyer les autres
MAX_RESUME = 400         # le catalogue reste court, le texte complet se lit à la demande


@dataclass(frozen=True)
class Source:
    nom: str
    url: str
    rubrique: str
    langue: str


@dataclass(frozen=True)
class Article:
    id: str          # identifiant court donné à l'agent, par exemple "S12"
    source: str
    rubrique: str
    titre: str
    lien: str        # vient du flux, jamais de l'agent
    publie: datetime
    resume: str


def charger_sources(chemin: Path) -> list[Source]:
    data = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    return [Source(**s) for s in data["sources"]]


def fenetre_heures(jour: date, base: int = 36) -> int:
    """Le lundi, on couvre le week-end. La mémoire écarte ce qui a déjà été publié."""
    return max(72, base) if jour.weekday() == 0 else base


def _nettoyer(texte: str | None, limite: int) -> str:
    texte = re.sub(r"<[^>]+>", " ", texte or "")
    texte = html.unescape(texte)
    texte = re.sub(r"\s+", " ", texte).strip()
    return texte if len(texte) <= limite else texte[:limite].rsplit(" ", 1)[0] + "…"


def _lire_flux(source: Source, brut: bytes, depuis: datetime) -> list[dict]:
    flux = feedparser.parse(brut)
    if flux.bozo and not flux.entries:
        raise ValueError(f"flux illisible : {flux.bozo_exception}")
    entrees = []
    for e in flux.entries:
        date_brute = e.get("published_parsed") or e.get("updated_parsed")
        lien = e.get("link", "")
        if not date_brute or not lien.startswith(("https://", "http://")):
            continue
        publie = datetime.fromtimestamp(calendar.timegm(date_brute), tz=timezone.utc)
        if publie >= depuis:
            entrees.append({"source": source.nom, "rubrique": source.rubrique,
                            "titre": _nettoyer(e.get("title"), 200), "lien": lien,
                            "publie": publie, "resume": _nettoyer(e.get("summary"), MAX_RESUME)})
    entrees.sort(key=lambda x: x["publie"], reverse=True)
    return entrees[:MAX_PAR_SOURCE]


def collecter(sources: list[Source], heures: int, maintenant: datetime | None = None,
              telecharger_fn: Callable[[str], bytes] = telecharger) -> tuple[list[Article], list[str]]:
    """Renvoie le catalogue et la liste des sources en échec."""
    maintenant = maintenant or datetime.now(timezone.utc)
    depuis = maintenant - timedelta(hours=heures)
    entrees, echecs, vus = [], [], set()

    for source in sources:
        try:
            nouvelles = _lire_flux(source, telecharger_fn(source.url), depuis)
        except Exception as exc:
            # Une source en panne ne doit jamais bloquer le journal.
            log.warning("Source ignorée, %s : %s", source.nom, exc)
            echecs.append(source.nom)
            continue
        for n in nouvelles:
            if n["lien"] not in vus:
                vus.add(n["lien"])
                entrees.append(n)
        log.info("%s : %d articles récents", source.nom, len(nouvelles))

    entrees.sort(key=lambda x: x["publie"], reverse=True)
    articles = [Article(id=f"S{i}", **e) for i, e in enumerate(entrees, 1)]
    log.info("Catalogue : %d articles, %d sources en échec", len(articles), len(echecs))
    return articles, echecs
