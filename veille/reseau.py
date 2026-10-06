"""Téléchargement HTTP avec des limites strictes.

Toutes les requêtes du projet passent par ici : même délai maximal,
même taille maximale, même identification auprès des sites.
"""
import requests

USER_AGENT = "veille-cyber/0.2 (projet personnel de veille, lecture RSS)"
TIMEOUT_S = 15
MAX_OCTETS = 3_000_000  # au-delà, ce n'est plus un article : on refuse


def telecharger(url: str) -> bytes:
    if not url.startswith(("https://", "http://")):
        raise ValueError(f"Schéma refusé : {url}")
    with requests.get(url, headers={"User-Agent": USER_AGENT},
                      timeout=TIMEOUT_S, stream=True) as r:
        r.raise_for_status()
        contenu = b""
        for bloc in r.iter_content(64_000):
            contenu += bloc
            if len(contenu) > MAX_OCTETS:
                raise ValueError(f"Réponse trop volumineuse : {url}")
        return contenu
