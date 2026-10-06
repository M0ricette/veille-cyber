"""Unique point de contact avec le modèle de langage.

L'agent appelle appeler() et ne connaît pas le SDK. Changer de fournisseur
demande d'adapter ce fichier, notamment le format des appels d'outils.
"""
import logging

import anthropic

log = logging.getLogger(__name__)
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # Le SDK relance seul les erreurs réseau, 429 et 5xx avec un délai croissant.
        _client = anthropic.Anthropic(max_retries=3, timeout=120)  # lit ANTHROPIC_API_KEY
    return _client


def appeler(system: str, messages: list, outils: list, modele: str,
            outil_force: str | None = None, max_tokens: int = 8000):
    """Un tour de conversation. Renvoie la réponse brute : texte et demandes d'outils."""
    choix = {"type": "tool", "name": outil_force} if outil_force else {"type": "auto"}
    reponse = _get_client().messages.create(
        model=modele, max_tokens=max_tokens, system=system,
        messages=messages, tools=outils, tool_choice=choix,
    )
    log.info("LLM : %d tokens en entrée, %d en sortie, arrêt %s",
             reponse.usage.input_tokens, reponse.usage.output_tokens, reponse.stop_reason)
    return reponse
