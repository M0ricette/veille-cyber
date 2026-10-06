"""Deux matins de suite, de bout en bout, sans réseau ni clé API ni envoi réel."""
from datetime import date

import veille.main as main
from veille.config import load_config

from .conftest import MAINTENANT, SOURCES, faux_telechargement
from .test_agent import JOURNAL_OK, FauxModele, appel, lire
from veille.agent import lancer_agent as VRAI_AGENT
from veille.collecte import collecter


def preparer(monkeypatch, tmp_path, jour, modele, envois):
    cfg = load_config()
    monkeypatch.setattr(main, "load_config", lambda: cfg.__class__(**{**cfg.__dict__, "fichier_memoire": tmp_path / "m.db"}))
    monkeypatch.setattr(main, "RACINE", tmp_path)
    (tmp_path / "logs").mkdir(exist_ok=True)
    monkeypatch.setattr(main, "charger_sources", lambda _: SOURCES)
    monkeypatch.setattr(main, "collecter", lambda s, h: collecter(s, 24, MAINTENANT, faux_telechargement))
    monkeypatch.setattr(main, "lancer_agent", lambda *a, **k: VRAI_AGENT(*a, lire=lire, **k))
    monkeypatch.setattr(main.llm, "appeler", modele)
    monkeypatch.setattr(main, "exporter_pdf", lambda html, chemin, pied: chemin)
    monkeypatch.setattr(main, "envoyer", lambda cfg, objet, texte, pdf: envois.append(objet))
    monkeypatch.setattr(main, "date", type("D", (date,), {"today": classmethod(lambda c: jour)}))


def test_deux_matins_de_suite(monkeypatch, tmp_path):
    envois: list[str] = []

    # Jour 1 : le journal est publié et mémorisé.
    jour1 = FauxModele([[appel("lire_article", {"id": "S1"}, 1)], [appel("publier_journal", JOURNAL_OK, 2)]])
    preparer(monkeypatch, tmp_path, date(2026, 10, 7), jour1, envois)
    assert main.run(dry_run=False, heures=None) == 0

    # Jour 2 : mêmes flux. Les articles déjà publiés disparaissent du catalogue,
    # et l'agent sait que le smishing a déjà été expliqué.
    jour2 = FauxModele([[appel("publier_journal", {"accroche": "Calme", "breves": []}, 1)]])
    preparer(monkeypatch, tmp_path, date(2026, 10, 8), jour2, envois)
    assert main.run(dry_run=False, heures=None) == 0

    premier_message = jour2.recus[0]["messages"][0]["content"]
    assert "Le smishing · niveau 1" in premier_message
    # Il ne reste que l'article jamais publié.
    assert "Doublon présent" in premier_message
    assert "ExempleTelecom" not in premier_message and "sanctions" not in premier_message
    assert len(envois) == 2

    m = main.Memoire(tmp_path / "m.db")
    assert m.numero_suivant(date(2026, 10, 9)) == 3
    assert [t for t, _ in m.notions_vues()] == ["Le smishing"]
    # Le lendemain du jour 1, le smishing revient en rappel.
    assert m.rappels(date(2026, 10, 8))[0]["titre"] == "Le smishing"
