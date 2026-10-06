from datetime import datetime, timezone
from pathlib import Path

from veille.sources import fetch_articles

FLUX = str(Path(__file__).parent / "fixtures" / "flux_test.xml")
MAINTENANT = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)


def test_garde_seulement_les_articles_recents():
    articles = fetch_articles(FLUX, window_hours=24, now=MAINTENANT)
    titres = [a.title for a in articles]
    assert "Ancien avis" not in titres
    assert "Vulnérabilité dans ExempleVPN Gateway" in titres


def test_rejette_les_liens_non_http():
    articles = fetch_articles(FLUX, window_hours=24, now=MAINTENANT)
    assert all(a.link.startswith("https://") for a in articles)
    assert "Lien piégé" not in [a.title for a in articles]


def test_retire_le_html_et_numerote():
    articles = fetch_articles(FLUX, window_hours=24, now=MAINTENANT)
    assert "<p>" not in articles[0].summary
    assert [a.id for a in articles] == ["A1", "A2"]
