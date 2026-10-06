import json
from datetime import datetime, timezone

import pytest

from veille.redaction import build_user_prompt, parse_and_verify
from veille.sources import Article

ARTICLES = [
    Article("A1", "Vulnérabilité dans ExempleVPN", "https://exemple.fr/a1",
            datetime(2026, 10, 6, tzinfo=timezone.utc),
            "Contournement d'authentification CVE-2026-11111, activement exploitée."),
    Article("A2", "Vulnérabilités dans ExempleCMS", "https://exemple.fr/a2",
            datetime(2026, 10, 6, tzinfo=timezone.utc), "Injection XSS à distance."),
]


def reponse(points, notion=None):
    return json.dumps({"intro": "Bonjour", "points": points, "notion": notion})


def test_point_valide_conserve_avec_le_lien_du_flux():
    d = parse_and_verify(reponse([{"titre": "VPN", "resume": "CVE-2026-11111 exploitée.", "source": "A1"}]), ARTICLES)
    assert len(d.points) == 1
    assert d.points[0].source.link == "https://exemple.fr/a1"


def test_source_inconnue_rejetee():
    d = parse_and_verify(reponse([{"titre": "Inventé", "resume": "...", "source": "A9"}]), ARTICLES)
    assert d.points == [] and len(d.rejets) == 1


def test_cve_inventee_rejetee():
    d = parse_and_verify(reponse([{"titre": "CMS", "resume": "Corrigez CVE-2026-99999.", "source": "A2"}]), ARTICLES)
    assert d.points == []
    assert "CVE-2026-99999" in d.rejets[0]


def test_cve_d_un_autre_article_rejetee():
    # La CVE existe, mais pas dans l'article cité : le point est mal sourcé.
    d = parse_and_verify(reponse([{"titre": "CMS", "resume": "Lié à CVE-2026-11111.", "source": "A2"}]), ARTICLES)
    assert d.points == []


def test_notion_sourcee_conservee():
    notion = {"titre": "Le XSS", "explication": "Injection de script.", "source": "A2"}
    d = parse_and_verify(reponse([], notion), ARTICLES)
    assert d.notion is not None and d.notion.source.id == "A2"


def test_json_entoure_de_balises_markdown():
    raw = "```json\n" + reponse([{"titre": "VPN", "resume": "ok", "source": "A1"}]) + "\n```"
    assert len(parse_and_verify(raw, ARTICLES).points) == 1


def test_reponse_sans_json_leve_une_erreur():
    with pytest.raises(ValueError):
        parse_and_verify("Désolé, je ne peux pas.", ARTICLES)


def test_articles_balises_dans_le_prompt():
    prompt = build_user_prompt(ARTICLES)
    assert '<article id="A1">' in prompt and "</article>" in prompt
