from datetime import date

from veille.journal import render_html, typo
from veille.verification import Breve, Journal, Une


def test_rendu_echappe_le_html_et_numerote_les_sources(catalogue):
    s1, s3 = catalogue[0], catalogue[2]
    j = Journal("Accroche", Une("<script>alert(1)</script>", "Chapô", ["Fait [S1].", "Autre fait [S1][S3]."], [s1, s3]),
                [Breve("Écosystème", "Brève", "Texte", s3)], None)
    html = render_html(j, date(2026, 10, 7), 1, "Le Veilleur", [], 3)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "Fait<sup>1</sup>" in html and "<sup>1,2</sup>" in html


def test_typographie_francaise():
    assert typo("3 000 000 clients : attention !") == "3 000 000 clients : attention !"
