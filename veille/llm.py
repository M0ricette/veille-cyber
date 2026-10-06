"""Unique point de contact avec le modèle de langage.

Tout le reste du code appelle complete() et ignore quel fournisseur est derrière.
Passer à un autre fournisseur ou à un modèle local via Ollama ne touche que ce fichier.
"""
import logging

import anthropic

log = logging.getLogger(__name__)


def complete(system: str, user: str, model: str, max_tokens: int = 2000) -> str:
    # Le SDK relance seul les erreurs réseau, 429 et 5xx avec un délai croissant.
    client = anthropic.Anthropic(max_retries=3, timeout=60)  # lit ANTHROPIC_API_KEY
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    log.info("LLM : %d tokens en entrée, %d en sortie",
             response.usage.input_tokens, response.usage.output_tokens)
    return "".join(block.text for block in response.content if block.type == "text")
