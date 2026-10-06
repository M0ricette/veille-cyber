"""Mise en page du journal : HTML façon quotidien, puis export PDF.

Le PDF est produit par Chromium via Playwright : on maquette en HTML et CSS,
le navigateur s'occupe des colonnes, de la typo et de la pagination.
"""
import base64
import re
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from .collecte import Article
from .verification import RUBRIQUES, Journal

ICI = Path(__file__).parent
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
POLICES = {
    "Masthead": [("unifrakturmaguntia-latin-400-normal", 400, "normal")],
    "Titrage": [("playfair-display-latin-700-normal", 700, "normal"),
                ("playfair-display-latin-900-normal", 900, "normal"),
                ("playfair-display-latin-400-italic", 400, "italic")],
    "Texte": [("source-serif-4-latin-400-normal", 400, "normal"),
              ("source-serif-4-latin-600-normal", 600, "normal"),
              ("source-serif-4-latin-400-italic", 400, "italic")],
    "Labels": [("libre-franklin-latin-600-normal", 600, "normal"),
               ("libre-franklin-latin-800-normal", 800, "normal")],
}

# autoescape : un titre piégé dans un flux s'affiche comme du texte, il n'est jamais interprété.
_env = Environment(loader=FileSystemLoader(ICI / "templates"), autoescape=select_autoescape(["html"]))
_env.filters["lien_court"] = lambda url: (lambda c: c if len(c) <= 70 else c[:67] + "…")(re.sub(r"^https?://(www\.)?", "", url))


def typo(texte: str) -> str:
    """Espaces insécables à la française : ni « 3 000 » ni « Attention : » ne se coupent en fin de ligne."""
    texte = re.sub(r"(\d) (?=\d{3}\b)", "\\1\u00a0", str(texte))
    return re.sub(r" ([:;!?»])", "\u00a0\\1", texte)


_env.filters["typo"] = typo


def date_longue(d: date) -> str:
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}"


def _polices_css() -> str:
    """Polices embarquées dans le HTML : le PDF a le même rendu sur toutes les machines, même hors ligne."""
    regles = []
    for famille, fichiers in POLICES.items():
        for nom, poids, style in fichiers:
            data = base64.b64encode((ICI / "fonts" / f"{nom}.woff2").read_bytes()).decode()
            regles.append(f"@font-face{{font-family:'{famille}';font-weight:{poids};font-style:{style};"
                          f"src:url(data:font/woff2;base64,{data}) format('woff2');}}")
    return "\n".join(regles)


def _numeroter_sources(journal: Journal) -> list[Article]:
    """Ordre d'apparition dans le journal : la une, puis les brèves, puis la notion."""
    ordre: list[Article] = []
    if journal.une:
        ordre += journal.une.sources
    ordre += [b.source for b in journal.breves]
    if journal.notion:
        ordre.append(journal.notion.source)
    return list(dict.fromkeys(ordre))


def render_html(journal: Journal, jour: date, numero: int, nom: str, sources_en_echec: list[str],
                nb_sources: int, rappels: list[dict] = ()) -> str:
    sources = _numeroter_sources(journal)
    num = {a.id: i for i, a in enumerate(sources, 1)}

    def avec_appels(texte: str) -> Markup:
        """Transforme [S3] en appel de note numéroté, après échappement du texte."""
        sur = str(escape(typo(texte)))
        sur = re.sub(r"\s*\[(S\d+)\]", lambda m: f"<sup>{num.get(m.group(1), '?')}</sup>", sur)
        sur = re.sub(r"</sup><sup>", ",", sur)
        return Markup(sur)

    rubriques = [(r, [b for b in journal.breves if b.rubrique == r]) for r in RUBRIQUES]
    return _env.get_template("journal.html").render(
        j=journal, nom=nom, numero=numero, date_longue=date_longue(jour),
        rubriques=[(r, bs) for r, bs in rubriques if bs], sources=sources, num=num,
        avec_appels=avec_appels, polices=Markup(_polices_css()),
        sources_en_echec=sources_en_echec, nb_sources=nb_sources, rappels=list(rappels),
    )


def render_texte(journal: Journal, jour: date, nom: str, rappels: list[dict] = ()) -> str:
    """Corps du mail : un sommaire court, le journal complet est en pièce jointe."""
    lignes = [f"{nom} du {date_longue(jour)}", ""]
    if journal.accroche:
        lignes += [journal.accroche, ""]
    if journal.une:
        lignes += ["À la une", journal.une.titre, journal.une.chapo, ""]
    if journal.breves:
        lignes += ["En bref"] + [f"· {b.titre}" for b in journal.breves] + [""]
    if journal.notion:
        lignes += [f"La notion du jour : {journal.notion.titre}", ""]
    if rappels:
        lignes += ["Rappel"] + [f"· {r['titre']} : {r['essentiel']}" for r in rappels] + [""]
    lignes.append("Le journal complet est en pièce jointe.")
    return "\n".join(lignes)


def exporter_pdf(html: str, chemin: Path, pied: str) -> Path:
    from playwright.sync_api import sync_playwright

    pied_html = ('<div style="width:100%;font-family:Georgia,serif;font-size:7.5pt;color:#555;'
                 'padding:0 12mm;display:flex;justify-content:space-between;">'
                 f'<span>{escape(pied)}</span>'
                 '<span>page <span class="pageNumber"></span> sur <span class="totalPages"></span></span></div>')
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        page = navigateur.new_page()
        # Le HTML est autonome : pas de réseau nécessaire pour le rendu.
        page.set_content(html, wait_until="load")
        page.pdf(path=str(chemin), format="A4", print_background=True,
                 margin={"top": "11mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
                 display_header_footer=True, header_template="<span></span>", footer_template=pied_html)
        navigateur.close()
    return chemin
