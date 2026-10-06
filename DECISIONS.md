# Journal des décisions

Chaque choix tient en trois lignes : ce qui a été choisi, l'alternative écartée, pourquoi.

## Un agent seulement là où il faut du jugement

**Choix.** Collecte et vérification en code fixe, rédaction confiée à un agent.
**Alternative.** Un agent qui fait tout, y compris chercher ses sources sur le web.
**Pourquoi.** Lire dix flux RSS ne demande aucun jugement : du code le fait plus vite, moins cher et sans erreur. Choisir la une, décider quoi lire et rédiger, si. Moins l'agent a de liberté, plus il est prévisible et facile à sécuriser.

## Boucle d'agent écrite à la main

**Choix.** Une boucle d'une cinquantaine de lignes dans `agent.py`, sur l'API de tool use.
**Alternative.** LangGraph ou LangChain.
**Pourquoi.** Le graphe est simple : lire, publier, corriger. L'écrire soi-même montre ce que font les frameworks sous le capot. LangGraph deviendra utile avec la mémoire persistante, la reprise après erreur ou plusieurs agents.

## La publication est un outil

**Choix.** L'agent rend le journal en appelant `publier_journal`, avec un schéma JSON imposé.
**Alternative.** Lui demander du JSON en texte libre et le parser.
**Pourquoi.** Le schéma de l'outil structure la sortie. Surtout, le résultat de l'outil sert de canal de retour : si la vérification échoue, l'agent reçoit la liste des problèmes et peut corriger.

## La vérification est faite par du code, pas par le LLM

**Choix.** Contrôles déterministes sur les identifiants, la lecture de la une, les CVE et les grands nombres.
**Alternative.** Demander au modèle de se relire.
**Pourquoi.** Un modèle qui se relit peut halluciner pendant sa relecture. Un contrôle en code donne le même résultat à chaque fois et se teste.

**Limite connue.** Le contrôle attrape les sources, CVE et chiffres inventés, pas une phrase fausse sur un fait réel. La notion du jour s'appuie encore sur les connaissances générales du modèle. Le RAG sur les guides de l'ANSSI la sourcera.

## L'agent choisit un identifiant, jamais une URL

**Choix.** `lire_article` prend un identifiant du catalogue, le code retrouve le lien.
**Alternative.** Un outil qui lit n'importe quelle URL.
**Pourquoi.** Une page piégée pourrait pousser l'agent à visiter une adresse interne ou à exfiltrer des données dans une URL. Ici, la liste des pages visitables est fixée par le code avant que l'agent démarre.

## Limites strictes sur l'agent

**Choix.** Six lectures, dix tours, deux corrections, publication forcée au dernier tour.
**Alternative.** Laisser l'agent tourner jusqu'à ce qu'il s'arrête.
**Pourquoi.** Un agent sans limite peut boucler et coûter cher. Les limites bornent le coût et garantissent qu'un journal sort chaque matin.

## RSS plutôt que scraping, pas de LinkedIn

**Choix.** Flux RSS officiels pour la collecte. LinkedIn exclu.
**Alternative.** Scraper les sites et le fil LinkedIn.
**Pourquoi.** Le RSS est fait pour les machines et ne casse pas quand un site change de design. LinkedIn n'offre pas d'accès public au fil, et le scraper viole ses conditions d'utilisation. Ce qui y circule relaie le plus souvent des articles de presse déjà couverts.

## trafilatura pour le texte complet

**Choix.** `trafilatura` pour extraire le corps d'un article.
**Alternative.** BeautifulSoup avec des sélecteurs par site.
**Pourquoi.** trafilatura fonctionne sur n'importe quel site sans réglage et retire menus, publicités et commentaires. Moins de bruit envoyé au modèle, donc moins de coût et moins de surface d'injection.

## Un seul fichier pour parler au modèle

**Choix.** Tout l'accès au fournisseur passe par `llm.py`.
**Alternative.** Appeler le SDK depuis l'agent.
**Pourquoi.** L'agent ne dépend pas du SDK. Passer à un autre fournisseur ou à un modèle local via Ollama demande d'adapter ce seul fichier, y compris le format des appels d'outils.

## Modèle léger par défaut

**Choix.** Un petit modèle rapide, configurable dans `.env`.
**Alternative.** Le plus gros modèle disponible.
**Pourquoi.** Le coût reste de quelques centimes par jour. La fiabilité vient des contrôles, pas de la taille du modèle. Un modèle plus grand améliore surtout le style de la une.

## PDF via Playwright, polices embarquées

**Choix.** Maquette en HTML et CSS, PDF produit par Chromium via Playwright, polices libres intégrées au HTML.
**Alternative.** WeasyPrint ou ReportLab.
**Pourquoi.** Chromium gère bien les colonnes et la typographie, et s'installe en une commande sur Windows, macOS et Linux, là où WeasyPrint demande des bibliothèques système. Les polices embarquées donnent le même rendu partout, même hors ligne.

## SQLite pour la mémoire

**Choix.** Une base SQLite locale, trois tables.
**Alternative.** Une base vectorielle comme Chroma, ou un simple fichier JSON.
**Pourquoi.** On fait des recherches exactes : ce lien a-t-il été publié, combien de notions vues. SQLite le fait sans serveur, avec des transactions. Le JSON se corrompt si le script plante pendant l'écriture. Une base vectorielle n'apporterait rien tant qu'on ne cherche pas par le sens.

## La mémoire est appliquée par le code

**Choix.** Le code retire les articles déjà publiés avant que l'agent ne voie le catalogue, et la vérification refuse une notion déjà vue.
**Alternative.** Donner à l'agent un outil pour consulter sa mémoire et le laisser juger.
**Pourquoi.** Ne pas republier un article est une règle, pas un jugement. Une règle s'applique en code : c'est gratuit, certain et testable. L'agent ne reçoit que ce qui demande du discernement, le choix d'une notion nouvelle au bon niveau.

## Ne mémoriser que du validé

**Choix.** On stocke des liens, des titres de notions nettoyés et des numéros, jamais le texte des articles.
**Alternative.** Stocker les résumés complets pour donner plus de contexte à l'agent.
**Pourquoi.** Tout ce qui est en mémoire revient dans le prompt les jours suivants. Une injection cachée dans un article deviendrait persistante. Les titres de notions sont bornés à une ligne de 80 caractères avant stockage.

## Enregistrer seulement après l'envoi

**Choix.** L'édition est mémorisée dans une transaction, après l'envoi réussi du mail.
**Alternative.** Mémoriser dès que l'agent a publié.
**Pourquoi.** Si l'envoi échoue, les articles doivent rester disponibles pour le lendemain. La transaction garantit qu'on n'enregistre jamais une édition à moitié.

## Doublons de notions : comparaison de texte, pas encore d'embeddings

**Choix.** Titres normalisés puis comparés avec `difflib`, seuil de similarité à 85 %.
**Alternative.** Comparer des embeddings dans une base vectorielle.
**Pourquoi.** La comparaison de texte attrape « Le phishing » et « le Phishing ! », sans dépendance. Elle rate les synonymes comme phishing et hameçonnage. Quand la liste de notions grandira, ce sera le bon moment pour introduire des embeddings.

## Progression de niveau par compteur

**Choix.** Le niveau visé monte d'un cran toutes les dix notions, de 1 à 4.
**Alternative.** Laisser l'agent juger mon niveau.
**Pourquoi.** Une règle simple, prévisible et lisible dans la base. La boucle de retour remplacera ce compteur par mes vraies notes sur chaque notion.

## SMTP plutôt qu'un service d'emailing

**Choix.** `smtplib` en SSL avec un compte Gmail, le journal en pièce jointe.
**Alternative.** Une API comme SendGrid.
**Pourquoi.** Un seul destinataire, aucune dépendance ni compte tiers. SMTP marche avec n'importe quel fournisseur.
