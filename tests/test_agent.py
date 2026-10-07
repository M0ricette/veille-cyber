"""Tests de la boucle d'agent avec un faux modèle qui joue un scénario écrit à l'avance."""
from types import SimpleNamespace

from veille.agent import lancer_agent

from .conftest import faux_telechargement
from veille.lecture import lire_texte_complet

JOURNAL_OK = {
    "accroche": "Fuite chez un opérateur",
    "une": {"titre": "ExempleTelecom piraté", "chapo": "Des millions de fiches en circulation.",
            "paragraphes": ["Un pirate revendique 3 000 000 fiches [S1].", "La faille CVE-2026-11111 serait en cause [S1]."],
            "sources": ["S1"]},
    "breves": [{"rubrique": "Géopolitique et régulation", "titre": "Sanctions", "texte": "L'UE vise six individus.", "source": "S3"}],
    "notion": {"titre": "Le smishing", "explication": "Une arnaque par SMS.", "source": "S1", "niveau": 1,
               "essentiel": "Le smishing est un hameçonnage par SMS."},
}


def appel(nom, entree, n):
    return SimpleNamespace(type="tool_use", id=f"t{n}", name=nom, input=entree)


class FauxModele:
    """Rejoue une liste de réponses et garde ce qu'il a reçu."""
    def __init__(self, reponses):
        self.reponses, self.recus = list(reponses), []

    def __call__(self, system, messages, outils, modele, outil_force=None):
        self.recus.append({"messages": list(messages), "force": outil_force})
        return SimpleNamespace(content=self.reponses.pop(0), stop_reason="tool_use")


def lire(url):
    return lire_texte_complet(url, faux_telechargement)


def test_scenario_complet_avec_correction(catalogue):
    une_non_lue = {**JOURNAL_OK, "une": {**JOURNAL_OK["une"], "sources": ["S3"],
                   "paragraphes": ["L'UE vise six individus [S3]."]}}
    modele = FauxModele([
        [appel("publier_journal", une_non_lue, 1)],     # publie trop vite, sans avoir lu
        [appel("lire_article", {"id": "S1"}, 2)],        # se corrige : va lire
        [appel("publier_journal", JOURNAL_OK, 3)],       # republie, tout est sourcé
    ])
    journal, trace = lancer_agent(catalogue, "test", modele, lire)
    assert journal.une.titre == "ExempleTelecom piraté"
    assert [e.get("outil") for e in trace.etapes] == ["publier_journal", "lire_article", "publier_journal"]
    # Le refus est renvoyé au modèle comme une erreur d'outil, avec la raison.
    retour = modele.recus[1]["messages"][-1]["content"][0]
    assert retour["is_error"] and "lu en entier" in retour["content"]


def test_le_contenu_lu_est_balise_comme_non_fiable(catalogue):
    modele = FauxModele([[appel("lire_article", {"id": "S1"}, 1)], [appel("publier_journal", JOURNAL_OK, 2)]])
    lancer_agent(catalogue, "test", modele, lire)
    contenu = modele.recus[1]["messages"][-1]["content"][0]["content"]
    assert contenu.startswith('<contenu_non_fiable id="S1"')


def test_identifiant_inconnu_refuse_sans_requete_reseau(catalogue):
    urls = []
    modele = FauxModele([
        [appel("lire_article", {"id": "S99"}, 1)],
        [appel("lire_article", {"id": "S1"}, 2)],
        [appel("publier_journal", JOURNAL_OK, 3)],
    ])
    lancer_agent(catalogue, "test", modele, lambda u: urls.append(u) or lire(u))
    # Seul l'article du catalogue a été visité : l'agent ne peut pas inventer une URL.
    assert urls == ["https://a.example/fuite"]


def test_limite_de_lectures(catalogue):
    modele = FauxModele([
        [appel("lire_article", {"id": "S1"}, 1)],
        [appel("lire_article", {"id": "S2"}, 2)],
        [appel("publier_journal", JOURNAL_OK, 3)],
    ])
    _, trace = lancer_agent(catalogue, "test", modele, lambda u: "texte", max_lectures=1)
    assert trace.etapes[1]["resultat"] == "limite atteinte"


def test_le_dernier_tour_force_la_publication(catalogue):
    modele = FauxModele([[appel("lire_article", {"id": "S1"}, 1)], [appel("publier_journal", JOURNAL_OK, 2)]])
    lancer_agent(catalogue, "test", modele, lire, max_tours=2)
    assert [r["force"] for r in modele.recus] == [None, "publier_journal"]


def test_apres_deux_corrections_on_garde_ce_qui_est_valide(catalogue):
    mauvais = {**JOURNAL_OK, "une": {**JOURNAL_OK["une"], "paragraphes": ["Sans source."]}}
    modele = FauxModele([[appel("lire_article", {"id": "S1"}, 0)]] +
                        [[appel("publier_journal", mauvais, i)] for i in range(1, 4)])
    journal, _ = lancer_agent(catalogue, "test", modele, lire)
    assert journal.une is None
    assert len(journal.breves) == 1


def test_notion_deja_vue_refusee_puis_corrigee(catalogue):
    nouvelle = {**JOURNAL_OK, "notion": {**JOURNAL_OK["notion"], "titre": "La fuite de données", "niveau": 2}}
    modele = FauxModele([
        [appel("lire_article", {"id": "S1"}, 1)],
        [appel("publier_journal", JOURNAL_OK, 2)],      # le smishing a déjà été expliqué
        [appel("publier_journal", nouvelle, 3)],
    ])
    journal, _ = lancer_agent(catalogue, "test", modele, lire,
                              notions_vues=[("Le Smishing", 1)], niveau_cible=2)
    assert journal.notion.titre == "La fuite de données" and journal.notion.niveau == 2
    # La mémoire est bien donnée à l'agent dès le premier message.
    premier = modele.recus[0]["messages"][0]["content"]
    assert "<memoire>" in premier and "Le Smishing" in premier and "2 sur 4" in premier


def test_republication_partielle_garde_les_breves_et_la_notion(catalogue):
    """Bug du 7 octobre : après une correction, l'agent ne renvoyait que la une et perdait le reste."""
    une_sans_source = {**JOURNAL_OK, "une": {**JOURNAL_OK["une"], "paragraphes": ["Sans source."]}}
    seulement_la_une = {"accroche": JOURNAL_OK["accroche"], "une": JOURNAL_OK["une"]}
    modele = FauxModele([
        [appel("lire_article", {"id": "S1"}, 1)],
        [appel("publier_journal", une_sans_source, 2)],
        [appel("publier_journal", seulement_la_une, 3)],
    ])
    journal, _ = lancer_agent(catalogue, "test", modele, lire)
    assert journal.une is not None
    assert len(journal.breves) == 1
    assert journal.notion is not None
