#!/usr/bin/env bash
# Prépare une session vierge (cloud) pour un cycle du Manager : branche, dépendances, données Dukascopy.
# Idempotent : peut être relancé à chaque cycle.
set -u
cd "$(dirname "$0")/.."
BRANCH="multi-agent-research"
git fetch -q origin || true
if [ "$(git rev-parse --abbrev-ref HEAD)" != "$BRANCH" ]; then
  git checkout -q "$BRANCH" 2>/dev/null || git checkout -q -b "$BRANCH" "origin/$BRANCH"
fi
git pull -q --ff-only origin "$BRANCH" || echo "pull impossible (modifications locales ?) : on continue"
python3 -c "import pandas, numpy, yaml" 2>/dev/null || pip install -q -r requirements.txt --break-system-packages || pip install -q -r requirements.txt
# Données : branche data-<tag> du dépôt PRIVÉ soso366/forex-data → dossier local (CSV gzip).
# (Le dépôt forex-agent est public : les données Dukascopy n'y sont plus.) Rien n'est lu ici, on prépare seulement.
# Dans GitHub Actions, le secret DATA_REPO_TOKEN (jeton en lecture sur forex-data) donne l'accès.
DATA_REMOTE="https://github.com/soso366/forex-data"
[ -n "${DATA_REPO_TOKEN:-}" ] && DATA_REMOTE="https://x-access-token:${DATA_REPO_TOKEN}@github.com/soso366/forex-data"
fetch() {  # $1 = tag, $2 = dossier
  [ -f "data/$2/EURUSD.csv" ] && return 0
  git ls-remote --exit-code --heads "$DATA_REMOTE" "data-$1" >/dev/null 2>&1 || { echo "données $1 : indisponibles (pas publiées ou pas d'accès à forex-data)"; return 0; }
  tmp=$(mktemp -d)
  git clone -q --depth 1 -b "data-$1" "$DATA_REMOTE" "$tmp/d" && mkdir -p "data/$2" && \
    for f in "$tmp"/d/*.csv.gz; do gunzip -c "$f" > "data/$2/$(basename "$f" .gz)"; done && \
    cp "$tmp"/d/quality_report.json "data/$2/" 2>/dev/null
  rm -rf "$tmp"
  echo "données $1 → data/$2"
}
fetch 2025sep-2026feb m1_2025
fetch 2026mar-aug m1
fetch 2025mar-aug m1_locked
fetch 2024sep-2025feb m1_locked_2024
# OOS vierge sept. 2023 → août 2024 : JAMAIS préparé automatiquement. Il n'est cloné qu'au moment de l'OOS final
# d'une expérience ayant survécu Train ET Validation (python -m orchestrator oos-gate E### doit répondre OUVERT).
python3 -m orchestrator status
