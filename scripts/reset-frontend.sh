#!/usr/bin/env bash
# Vyčistenie Next.js cache lokálne a/alebo obnovenie FE kontajnera bez starej Docker vrstvy.
# Po nasadení: tvrdý refresh prehliadača (Ctrl+Shift+R / Cmd+Shift+R), aby nebolo HTML z cache CDN.
#
# Použitie:
#   ./scripts/reset-frontend.sh local      # zmaze .frontend/.next (+ node_modules/.cache)
#   ./scripts/reset-frontend.sh docker     # docker compose rebuild --no-cache + recreate frontend

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

clean_local_frontend() {
  local fe="$ROOT/frontend"
  if [[ ! -d "$fe" ]]; then
    echo "Chyba: neexistuje $fe"
    exit 1
  fi
  rm -rf "$fe/.next" "$fe/node_modules/.cache"
  echo "OK: lokálny Next cache zmazaný ($fe/.next, node_modules/.cache)."
}

recreate_frontend_container() {
  cd "$ROOT"
  if [[ ! -f docker-compose.yml ]]; then
    echo "Chyba: docker-compose.yml v $ROOT."
    exit 1
  fi
  docker compose build --no-cache frontend
  docker compose up -d --force-recreate frontend
  echo "OK: služba „frontend“ prebuildovaná (--no-cache) a spustená nanovo."
  echo "    Ak stále vidíš starý vzhľad, urob tvrdý refresh v prehliadači alebo vyprázdni cache pre doménu."
}

case "${1:-docker}" in
  local | l)
    clean_local_frontend
    ;;
  docker | d | *)
    recreate_frontend_container
    ;;
esac
