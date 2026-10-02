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
# Données : branche GitHub data-<tag> → dossier local (CSV gzip). Rien n'est lu ici, on prépare seulement.
fetch() {  # $1 = tag, $2 = dossier
  [ -f "data/$2/EURUSD.csv" ] && return 0
  git ls-remote --exit-code --heads origin "data-$1" >/dev/null 2>&1 || { echo "données $1 : pas encore publiées"; return 0; }
  tmp=$(mktemp -d)
  git clone -q --depth 1 -b "data-$1" "$(git remote get-url origin)" "$tmp/d" && mkdir -p "data/$2" && \
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
