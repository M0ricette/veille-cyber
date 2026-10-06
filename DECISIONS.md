# Journal des décisions

Chaque choix tient en trois lignes : ce qui a été choisi, l'alternative écartée, pourquoi.

## RSS plutôt que scraping

**Choix.** Lire les flux RSS officiels avec `feedparser`.
**Alternative.** Parser le HTML des pages avec BeautifulSoup.
**Pourquoi.** Le RSS est fait pour les machines et ne casse pas quand le site change de design. Le scraping reste possible plus tard pour une source sans flux.

## Pas de framework d'orchestration à l'étape 1

**Choix.** Un script Python linéaire.
**Alternative.** LangGraph ou LangChain dès le départ.
**Pourquoi.** Le pipeline n'a ni branche ni boucle. Un framework ajouterait de la complexité sans rien apporter. LangGraph arrivera quand il y aura un vrai graphe : plusieurs sources, tri, rédaction, vérification et relance.

## La vérification est faite par du code, pas par le LLM

**Choix.** Le modèle cite un identifiant d'article, le code vérifie l'identifiant et les CVE, puis insère le lien.
**Alternative.** Demander au modèle de se relire, ou lui demander d'écrire les liens.
**Pourquoi.** Un modèle qui se relit peut halluciner pendant sa relecture. Un contrôle déterministe donne le même résultat à chaque fois et se teste.

**Limite connue.** Le contrôle détecte les identifiants inventés et les CVE inventées, pas une phrase fausse sur un fait réel. L'explication de la notion du jour s'appuie encore sur les connaissances générales du modèle. L'étape 3 la sourcera par RAG.

## Un seul fichier pour parler au modèle

**Choix.** Toute la relation au fournisseur passe par `llm.py` et une fonction `complete()`.
**Alternative.** Appeler le SDK partout où on en a besoin.
**Pourquoi.** Changer de fournisseur ou passer à un modèle local via Ollama ne touche qu'un fichier. C'est aussi un argument de souveraineté : on peut garder les données en interne sans réécrire l'agent.

## Modèle léger

**Choix.** Un petit modèle rapide, configurable dans `.env`.
**Alternative.** Le plus gros modèle disponible.
**Pourquoi.** Résumer quelques articles ne demande pas un modèle de pointe et le coût reste négligeable au quotidien. La fiabilité vient du prompt strict et de la vérification, pas de la taille du modèle.

## Relance confiée au SDK

**Choix.** `max_retries=3` sur le client Anthropic.
**Alternative.** Écrire sa propre boucle de relance.
**Pourquoi.** Le SDK relance déjà les erreurs réseau, les 429 et les 5xx avec un délai croissant. Réécrire ce code n'apporterait que des bugs.

## SMTP plutôt qu'un service d'emailing

**Choix.** `smtplib` en SSL avec un compte Gmail.
**Alternative.** Une API comme SendGrid ou Mailgun.
**Pourquoi.** Un seul destinataire, aucune dépendance supplémentaire, aucun compte tiers. SMTP est un standard qui marche avec n'importe quel fournisseur.

## HTML en tables et styles en ligne

**Choix.** Un template Jinja2 en tables avec styles en ligne, plus une version texte.
**Alternative.** Un HTML moderne avec une feuille de style.
**Pourquoi.** Gmail et Outlook ignorent une grande partie du CSS moderne. La version texte sert de secours et rend les logs lisibles.
