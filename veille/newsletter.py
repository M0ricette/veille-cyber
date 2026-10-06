"""Mise en forme du récap : une version HTML et une version texte brut."""
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .redaction import Digest

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]

# autoescape : si le LLM ou un flux renvoie du HTML, il s'affiche comme du texte
# au lieu d'être interprété dans le mail.
_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)


def date_fr(d: date) -> str:
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


def render_html(digest: Digest, day: date, source_name: str) -> str:
    return _env.get_template("newsletter.html").render(
        digest=digest, date_fr=date_fr(day), source_name=source_name)


def render_text(digest: Digest, day: date) -> str:
    """Version texte : lue par les clients qui bloquent le HTML, et utile dans les logs."""
    lignes = [f"Veille cyber du {date_fr(day)}", "", digest.intro, ""]
    for i, p in enumerate(digest.points, 1):
        lignes += [f"{i}. {p.titre}", p.resume, f"Source : {p.source.link}", ""]
    if not digest.points:
        lignes += ["Rien de notable aujourd'hui.", ""]
    if digest.notion:
        n = digest.notion
        lignes += [f"Notion du jour : {n.titre}", n.explication, f"Liée à : {n.source.link}"]
    return "\n".join(lignes)
