#!/usr/bin/env bash
# Persiste la mémoire SQLite entre deux exécutions GitHub Actions.
#
# Chaque exécution démarre sur une machine vierge. On récupère donc la base
# depuis la branche « memoire » du dépôt au début, et on l'y repousse à la fin.
# Une branche à part garde l'historique du code propre.
#
# Usage : scripts/memoire_git.sh recuperer | sauvegarder
set -euo pipefail

BRANCHE="${BRANCHE:-memoire}"
FICHIER="${FICHIER:-data/veilleur.db}"
DEPOT="${DEPOT:-https://x-access-token:${GITHUB_TOKEN:-}@github.com/${GITHUB_REPOSITORY:-}.git}"

# 0 si la branche existe, 1 si elle n'existe pas encore. Toute autre erreur arrête tout :
# un dépôt injoignable ne doit surtout pas être pris pour un premier lancement.
branche_existe() {
  set +e
  git ls-remote --exit-code --heads "$DEPOT" "$BRANCHE" >/dev/null 2>&1
  local code=$?
  set -e
  case $code in
    0) return 0 ;;
    2) return 1 ;;
    *) echo "Dépôt injoignable, arrêt" >&2; exit 1 ;;
  esac
}

recuperer() {
  mkdir -p "$(dirname "$FICHIER")"
  if branche_existe; then
    local tmp; tmp=$(mktemp -d)
    git -C "$tmp" init -q
    git -C "$tmp" fetch -q --depth=1 "$DEPOT" "$BRANCHE"
    git -C "$tmp" show FETCH_HEAD:veilleur.db > "$FICHIER"
    rm -rf "$tmp"
    echo "Mémoire récupérée"
  else
    echo "Pas encore de mémoire : premier lancement"
  fi
}

sauvegarder() {
  if [ ! -f "$FICHIER" ]; then
    echo "Aucune mémoire à sauvegarder"
    return 0
  fi
  local source tmp
  source=$(realpath "$FICHIER")
  tmp=$(mktemp -d)
  git -C "$tmp" init -q
  if branche_existe; then
    git -C "$tmp" fetch -q --depth=1 "$DEPOT" "$BRANCHE"
    git -C "$tmp" checkout -q -B "$BRANCHE" FETCH_HEAD
  else
    git -C "$tmp" checkout -q --orphan "$BRANCHE"
    printf '# Mémoire du Veilleur\n\nBranche technique : la base SQLite que l%sagent relit chaque matin.\n' "'" > "$tmp/README.md"
    git -C "$tmp" add README.md
  fi
  cp "$source" "$tmp/veilleur.db"
  git -C "$tmp" add veilleur.db
  if git -C "$tmp" diff --cached --quiet; then
    echo "Mémoire inchangée"
  else
    git -C "$tmp" -c user.name="Le Veilleur" \
      -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
      commit -q -m "Mémoire : édition du $(date +%Y-%m-%d)"
    git -C "$tmp" -c push.negotiate=false push -q "$DEPOT" "$BRANCHE"
    echo "Mémoire sauvegardée"
  fi
  rm -rf "$tmp"
}

case "${1:-}" in
  recuperer) recuperer ;;
  sauvegarder) sauvegarder ;;
  *) echo "Usage : $0 recuperer | sauvegarder" >&2; exit 2 ;;
esac
