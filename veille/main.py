"""Point d'entrée : récupérer, rédiger, vérifier, envoyer.

Usage :
    python -m veille.main --dry-run     écrit la newsletter dans out/ sans l'envoyer
    python -m veille.main               envoie la newsletter par mail
"""
import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from .config import load_config
from .llm import complete
from .mailer import send_newsletter
from .newsletter import date_fr, render_html, render_text
from .redaction import SYSTEM_PROMPT, Digest, build_user_prompt, parse_and_verify
from .sources import fetch_articles

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("veille")


def setup_logging() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
        handlers=[logging.FileHandler(ROOT / "logs" / "veille.log", encoding="utf-8"),
                  logging.StreamHandler()],
    )


def run(dry_run: bool, feed: str | None, window: int | None) -> int:
    cfg = load_config()
    today = date.today()
    articles = fetch_articles(feed or cfg.feed_url, cfg.window_hours if window is None else window)

    if articles:
        raw = complete(SYSTEM_PROMPT, build_user_prompt(articles), cfg.llm_model)
        digest = parse_and_verify(raw, articles)
    else:
        # Pas d'article : pas d'appel LLM, donc aucun risque d'invention.
        digest = Digest("Journée calme côté CERT-FR.", [], None)

    html = render_html(digest, today, "le flux RSS du CERT-FR")
    text = render_text(digest, today)
    subject = f"Veille cyber · {date_fr(today)} · {len(digest.points)} points"

    if dry_run:
        out = ROOT / "out"
        out.mkdir(exist_ok=True)
        path = out / f"newsletter-{today.isoformat()}.html"
        path.write_text(html, encoding="utf-8")
        log.info("Mode test : newsletter écrite dans %s", path)
        print(text)
    else:
        send_newsletter(cfg, subject, text, html)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent de veille cyber quotidien")
    parser.add_argument("--dry-run", action="store_true", help="écrit le HTML au lieu d'envoyer le mail")
    parser.add_argument("--feed", help="URL ou fichier RSS à utiliser à la place de FEED_URL")
    parser.add_argument("--window", type=int, help="fenêtre en heures, 24 par défaut")
    args = parser.parse_args()
    setup_logging()
    try:
        return run(args.dry_run, args.feed, args.window)
    except Exception:
        # Un échec doit laisser une trace exploitable, pas disparaître en silence.
        log.exception("Échec de l'exécution")
        return 1


if __name__ == "__main__":
    sys.exit(main())
