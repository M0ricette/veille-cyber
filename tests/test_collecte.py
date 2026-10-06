from datetime import date

from veille.collecte import collecter, fenetre_heures
from veille.lecture import lire_texte_complet

from .conftest import MAINTENANT, SOURCES, faux_telechargement


def test_une_source_en_panne_ne_bloque_pas_les_autres():
    articles, echecs = collecter(SOURCES, 24, MAINTENANT, faux_telechargement)
    assert echecs == ["Source en panne"]
    assert {a.source for a in articles} == {"Source A", "Source B"}


def test_doublons_liens_piegés_et_vieux_articles_ecartes(catalogue):
    liens = [a.lien for a in catalogue]
    assert liens.count("https://commun.example/doublon") == 1
    assert all(l.startswith("https://") for l in liens)
    assert "https://a.example/vieux" not in liens
    assert len(catalogue) == 3


def test_catalogue_trie_et_numerote(catalogue):
    assert [a.id for a in catalogue] == ["S1", "S2", "S3"]
    assert catalogue[0].publie >= catalogue[-1].publie
    assert "<p>" not in catalogue[0].resume


def test_le_lundi_couvre_le_week_end():
    assert fenetre_heures(date(2026, 10, 5)) == 72
    assert fenetre_heures(date(2026, 10, 6)) == 24


def test_lecture_garde_l_article_et_jette_le_menu():
    texte = lire_texte_complet("https://a.example/fuite", faux_telechargement)
    assert "3 000 000" in texte
    assert "Mentions légales" not in texte
