"""Point d'entrée : collecter, laisser l'agent rédiger, vérifier, mettre en page, envoyer.

Usage :
    python -m veille.main --dry-run     produit le PDF dans out/ sans l'envoyer
    python -m veille.main               envoie le journal par mail
"""
import argparse
import json
import logging
import sys
from datetime import date

from . import llm
from .agent import lancer_agent
from .collecte import charger_sources, collecter, fenetre_heures
from .config import RACINE, load_config
from .journal import date_longue, exporter_pdf, render_html, render_texte
from .mailer import envoyer
from .memoire import Memoire
from .verification import Journal

log = logging.getLogger("veille")


def setup_logging() -> None:
    (RACINE / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
        handlers=[logging.FileHandler(RACINE / "logs" / "veille.log", encoding="utf-8"),
                  logging.StreamHandler()],
    )


def run(dry_run: bool, heures: int | None) -> int:
    cfg = load_config()
    jour = date.today()
    memoire = Memoire(cfg.fichier_memoire)
    numero = memoire.numero_suivant(jour)

    sources = charger_sources(cfg.fichier_sources)
    articles, echecs = collecter(sources, heures or fenetre_heures(jour, cfg.fenetre_heures))
    if len(echecs) == len(sources):
        # Mieux vaut un échec visible dans les logs qu'un faux « rien de neuf ».
        raise RuntimeError("Aucune source joignable : vérifier la connexion réseau")

    # Mémoire 1 : on retire ce qui a déjà été publié, avant même que l'agent ne voie le catalogue.
    deja = memoire.liens_publies([a.lien for a in articles])
    articles = [a for a in articles if a.lien not in deja]
    log.info("%d articles déjà publiés écartés, %d nouveaux", len(deja), len(articles))

    if articles:
        # Mémoire 2 : l'agent reçoit les notions déjà vues et le niveau visé.
        journal, trace = lancer_agent(articles, cfg.modele, llm.appeler,
                                      max_tours=cfg.max_tours, max_lectures=cfg.max_lectures,
                                      notions_vues=memoire.notions_vues(),
                                      niveau_cible=memoire.niveau_cible())
        # La trace garde chaque décision de l'agent : utile pour comprendre et déboguer.
        (RACINE / "logs" / f"trace-{jour.isoformat()}.json").write_text(
            json.dumps(trace.etapes, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        # Rien à lire : pas d'appel au modèle, donc aucun risque d'invention.
        journal = Journal("Journée calme sur le front cyber.", None, [], None)

    sortie = RACINE / "out"
    sortie.mkdir(exist_ok=True)
    nom_fichier = f"{cfg.nom_journal.replace(' ', '-')}-{jour.isoformat()}"
    # Mémoire 4 : les rappels sont lus en base par le code, sans appel au modèle.
    rappels = memoire.rappels(jour)
    html = render_html(journal, jour, numero, cfg.nom_journal, echecs, len(sources), rappels)
    (sortie / f"{nom_fichier}.html").write_text(html, encoding="utf-8")
    pdf = exporter_pdf(html, sortie / f"{nom_fichier}.pdf",
                       f"{cfg.nom_journal} · N° {numero} · {date_longue(jour)}")
    log.info("PDF : %s", pdf)

    if dry_run:
        print(render_texte(journal, jour, cfg.nom_journal, rappels))
        log.info("Mode test : la mémoire n'est pas modifiée")
    else:
        objet = journal.accroche or date_longue(jour)
        envoyer(cfg, f"{cfg.nom_journal} · {objet}", render_texte(journal, jour, cfg.nom_journal, rappels), pdf)
        # Mémoire 3 : on n'enregistre qu'après un envoi réussi. Si l'envoi échoue, ces articles restent disponibles demain.
        memoire.enregistrer_edition(jour, numero, journal.accroche, articles_du_journal(journal),
                                    (journal.notion.titre, journal.notion.niveau, journal.notion.essentiel) if journal.notion else None)
    memoire.fermer()
    return 0


def articles_du_journal(journal: Journal) -> list[tuple[str, str]]:
    articles = (journal.une.sources if journal.une else []) + [b.source for b in journal.breves]
    if journal.notion:
        articles.append(journal.notion.source)
    return list(dict.fromkeys((a.lien, a.source) for a in articles))


def main() -> int:
    parser = argparse.ArgumentParser(description="Le Veilleur, agent de veille cyber quotidien")
    parser.add_argument("--dry-run", action="store_true", help="produit le PDF sans envoyer le mail")
    parser.add_argument("--heures", type=int, help="fenêtre de collecte, 36 h par défaut et 72 h le lundi")
    args = parser.parse_args()
    setup_logging()
    try:
        return run(args.dry_run, args.heures)
    except Exception:
        # Un échec doit laisser une trace exploitable, pas disparaître en silence.
        log.exception("Échec de l'exécution")
        return 1


if __name__ == "__main__":
    sys.exit(main())
