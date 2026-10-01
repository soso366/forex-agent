# État du projet (mis à jour par le Manager à chaque cycle)

Dernière mise à jour : 2026-10-01 (création de la mémoire, avant le premier cycle autonome)
Dernier cycle autonome : aucun (cycle 0 = mise en place)
Contrôle : voir `orchestrator/control.yaml` (RUNNING / PAUSED)
Moteur d'autonomie : tâche planifiée Claude « Forex — cycle Manager » (id trig_01FQqW1RLoX1zX21rHAYZCHe), toutes les 6 h (02:41, 08:41, 14:41, 20:41 heure de Paris), cloud, approbation automatique.

## Où en est-on
- **Baseline officielle = V2** (branche `main`) : 6 stratégies, Router par régime, Risk Manager. Pas d'avantage démontré.
- **Meta-skills** ajoutées sur `main` (informatives, rejeu identique 148 trades / −1,97 €).
- **Recherche V4** (branche `research-v4`) : 5 hypothèses testées, une seule candidate (H3, fix de Londres).
- **H3 : test OOS final en cours**, critères verrouillés (commit `2e4ae39`), données sept. 2024 → août 2025 en
  téléchargement (GitHub Actions « Export données M1 », branches `data-2025mar-aug` et `data-2024sep-2025feb`).
  Commande prévue : `python -m research.v4.oos_check` (une seule lecture). Verdict : PASS / FAIL / INCONCLUSIVE.
- Le Manager NE TOUCHE PAS à H3 : il attend le verdict et l'enregistre.

## Contraintes permanentes
5–30 min · scan 5 min · EURUSD/GBPUSD/USDJPY · 50 € · paper · max 2 positions · risque 1 %/trade, 2 % total,
perte jour 3 %, drawdown 20 % = kill switch, 3 pertes = pause 60 min, pas de martingale, stop obligatoire jamais élargi,
min R:R 1,5 (baseline), pas deux positions avec la même devise dans le même sens.

## Données disponibles (Dukascopy M1 bid/ask)
| Période | Dossier local | Branche GitHub | Rôle |
|---|---|---|---|
| sept. 2025 → fév. 2026 | `data/m1_2025` | `data-2025sep-2026feb` | Train V4 |
| mars → août 2026 | `data/m1` | `data-2026mar-aug` | Validation V4 |
| mars → août 2025 | `data/m1_locked` | `data-2025mar-aug` | OOS H3 (lu une fois) |
| sept. 2024 → fév. 2025 | `data/m1_locked_2024` | `data-2024sep-2025feb` | OOS H3 (lu une fois) |
Les CSV ne sont pas dans git (trop gros) : les cloner depuis la branche `data-*` et `gunzip`.
Nouvel OOS pour les hypothèses suivantes : à télécharger (ex. 2023-2024) via `deploy/trigger/export.txt`.

## Chiffres de référence
- V2, 12 mois (305 trades) : −0,033 R/trade, PF 0,90. Sens du signal sans information (test du miroir).
- Coût moyen : spread ≈ 0,3–0,6 pip ; entrées aléatoires stop 1 ATR M5 ≈ −0,07 R/trade.
- Amplitude typique en 30 min ≈ 2,3 ATR M5 (07–20 UTC).
