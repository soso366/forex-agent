# État du projet (mis à jour par le Manager à chaque cycle)

Dernière mise à jour : 2026-10-02 (cycle 1)
Dernier cycle : cycle 1 (2026-10-02, session interactive de test — agents réellement invoqués, voir reports/CYCLE_001.md)
Contrôle : voir `orchestrator/control.yaml` (RUNNING / PAUSED)
Moteur d'autonomie : tâche planifiée Claude « Forex — cycle Manager » (id trig_01FQqW1RLoX1zX21rHAYZCHe), toutes les 6 h (02:41, 08:41, 14:41, 20:41 heure de Paris), cloud, approbation automatique.

## Où en est-on
- **Baseline officielle = V2** (branche `main`) : 6 stratégies, Router par régime, Risk Manager. Pas d'avantage démontré.
- **Meta-skills** ajoutées sur `main` (informatives, rejeu identique 148 trades / −1,97 €).
- **Recherche V4** (branche `research-v4`) : 5 hypothèses testées, une seule candidate (H3, fix de Londres).
- **H3 / E000 : TERMINÉE — FAIL OOS, REJECT / ARCHIVED** (sept. 2024 → août 2025 : 577 trades, −0,108 R/trade, PF 0,74,
  3 paires négatives, 1 trimestre positif / 4, IC 95 % journalier entièrement négatif, placebos 13:00/14:00 > 16:00).
  Ne JAMAIS la resélectionner, la retester, l'optimiser ni la recycler.
- **Aucune stratégie validée pour le paper trading.**
- **Cycle 1** : E001 (divergence EURUSD-GBPUSD) REJECT au Train ; E002 (choc de spread) pré-critiquée GO, protocole au cycle 2.
- **OOS vierge en préparation** : sept. 2023 → août 2024 (voir memory/DATA_REQUESTS.md). Les 24 mois sept. 2024 → août 2026
  sont CONTAMINÉS : utilisables en Train / Validation, jamais comme OOS.

## Contraintes permanentes
5–30 min · scan 5 min · EURUSD/GBPUSD/USDJPY · 50 € · paper · max 2 positions · risque 1 %/trade, 2 % total,
perte jour 3 %, drawdown 20 % = kill switch, 3 pertes = pause 60 min, pas de martingale, stop obligatoire jamais élargi,
min R:R 1,5 (baseline), pas deux positions avec la même devise dans le même sens.

## Données disponibles (Dukascopy M1 bid/ask)
| Période | Dossier local | Branche GitHub | Rôle |
|---|---|---|---|
| sept. 2025 → fév. 2026 | `data/m1_2025` | `data-2025sep-2026feb` | Train V4 |
| mars → août 2026 | `data/m1` | `data-2026mar-aug` | Validation V4 |
| mars → août 2025 | `data/m1_locked` | `data-2025mar-aug` | OOS H3 consommé → validation seulement |
| sept. 2024 → fév. 2025 | `data/m1_locked_2024` | `data-2024sep-2025feb` | OOS H3 consommé → validation seulement |
| sept. 2023 → fév. 2024 | `data/m1_oos2324_a` | `data-2023sep-2024feb` | **OOS vierge** (en téléchargement) |
| mars → août 2024 | `data/m1_oos2324_b` | `data-2024mar-aug` | **OOS vierge** (en téléchargement) |
Les CSV ne sont pas dans git (trop gros) : les cloner depuis la branche `data-*` et `gunzip`.
Ne jamais ouvrir l'OOS vierge 2023-2024 avant qu'un protocole soit verrouillé (commit) pour l'expérience concernée.

## Chiffres de référence
- V2, 12 mois (305 trades) : −0,033 R/trade, PF 0,90. Sens du signal sans information (test du miroir).
- Coût moyen : spread ≈ 0,3–0,6 pip ; entrées aléatoires stop 1 ATR M5 ≈ −0,07 R/trade.
- Amplitude typique en 30 min ≈ 2,3 ATR M5 (07–20 UTC).
