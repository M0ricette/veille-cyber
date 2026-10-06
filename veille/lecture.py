"""Lecture du texte complet d'un article, à la demande de l'agent.

trafilatura extrait le corps de l'article et jette menus, pubs et commentaires.
"""
import trafilatura

from .reseau import telecharger

MAX_TEXTE = 6000  # assez pour comprendre un sujet, borné pour le coût et l'injection


def lire_texte_complet(url: str, telecharger_fn=telecharger) -> str:
    page = telecharger_fn(url).decode("utf-8", errors="replace")
    texte = trafilatura.extract(page, include_comments=False, include_tables=False) or ""
    if not texte.strip():
        raise ValueError("aucun texte exploitable sur la page")
    return texte[:MAX_TEXTE]
