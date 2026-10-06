from datetime import datetime, timezone
from pathlib import Path

import pytest

from veille.collecte import Source, collecter

FIXTURES = Path(__file__).parent / "fixtures"
MAINTENANT = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)

SOURCES = [
    Source("Source A", "https://a.example/feed", "Fuites et attaques", "fr"),
    Source("Source B", "https://b.example/feed", "Géopolitique et régulation", "fr"),
    Source("Source en panne", "https://panne.example/feed", "Écosystème", "fr"),
]


def faux_telechargement(url: str) -> bytes:
    pages = {
        "https://a.example/feed": "flux_a.xml",
        "https://b.example/feed": "flux_b.xml",
        "https://a.example/fuite": "article.html",
    }
    if url not in pages:
        raise ConnectionError(f"injoignable : {url}")
    return (FIXTURES / pages[url]).read_bytes()


@pytest.fixture
def catalogue():
    articles, _ = collecter(SOURCES, 24, MAINTENANT, faux_telechargement)
    return articles
