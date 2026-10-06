"""Récupération des articles depuis un flux RSS.

Le RSS est structuré et prévu pour être consommé par des machines :
pas de scraping HTML fragile, pas de dépendance à la mise en page du site.
"""
import calendar
import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import feedparser

log = logging.getLogger(__name__)

# On tronque chaque article : borne le coût LLM et la surface d'injection.
MAX_CHARS = 2000


@dataclass(frozen=True)
class Article:
    id: str          # identifiant court donné au LLM, par exemple "A3"
    title: str
    link: str        # vient du flux, jamais du LLM
    published: datetime
    summary: str


def _clean(text: str | None) -> str:
    """Retire le HTML et normalise les espaces : le LLM ne reçoit que du texte."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()[:MAX_CHARS]


def _is_safe_link(link: str) -> bool:
    """Un flux compromis pourrait glisser un lien javascript: dans le mail."""
    return link.startswith("https://") or link.startswith("http://")


def fetch_articles(source: str, window_hours: int, now: datetime | None = None) -> list[Article]:
    """Lit un flux RSS, URL ou fichier local, et garde les articles récents."""
    feed = feedparser.parse(source, agent="veille-cyber/0.1")
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"Flux illisible : {feed.bozo_exception}")

    now = now or datetime.now(timezone.utc)
    limit = now - timedelta(hours=window_hours)
    articles: list[Article] = []

    for entry in feed.entries:
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if not parsed:
            continue
        published = datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
        if published < limit:
            continue
        link = entry.get("link", "")
        if not _is_safe_link(link):
            log.warning("Lien rejeté pour l'article %r", entry.get("title"))
            continue
        articles.append(Article(
            id=f"A{len(articles) + 1}",
            title=_clean(entry.get("title")),
            link=link,
            published=published,
            summary=_clean(entry.get("summary")),
        ))

    log.info("%d articles récents sur %d dans le flux", len(articles), len(feed.entries))
    return articles
